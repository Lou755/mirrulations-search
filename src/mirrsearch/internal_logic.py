"""Internal logic module for search operations with pagination"""
import atexit
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import List, Tuple

from mirrsearch.db import cfr_part_filter_patterns, _cfr_exact_title_part_pairs, get_db

# Reused across searches: creating a ThreadPoolExecutor per request costs more than the
# overlap win when phase 1 is only tens of milliseconds. Single-element list avoids
# ``global`` while keeping a module-level mutable slot (name is pylint-friendly).
_PHASE1_EXECUTOR_REF = [None]


def _get_phase1_executor() -> ThreadPoolExecutor:
    if _PHASE1_EXECUTOR_REF[0] is None:
        _PHASE1_EXECUTOR_REF[0] = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="mirrsearch_phase1",
        )
    return _PHASE1_EXECUTOR_REF[0]


def _shutdown_phase1_executor() -> None:
    ex = _PHASE1_EXECUTOR_REF[0]
    if ex is not None:
        ex.shutdown(wait=True)
        _PHASE1_EXECUTOR_REF[0] = None


atexit.register(_shutdown_phase1_executor)


def _parallel_search_phase1_enabled() -> bool:
    """When true (env ``MIRRSEARCH_PHASE1_PARALLEL=1``), phase 1 runs Postgres and
    OpenSearch concurrently."""
    v = (os.getenv("MIRRSEARCH_PHASE1_PARALLEL") or "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def _phase1_run_sql(db_layer, query, filters):
    dtp, ag, cfp, sd, ed = filters
    return db_layer.search(
        query, dtp, ag, cfp, start_date=sd, end_date=ed,
    )


def _phase1_run_os(db_layer, term):
    return db_layer.text_match_terms([term])


def _phase1_future_result_or_error(future):
    """Read completed future outcome without a broad ``except`` (uses ``Future.exception()``)."""
    exc = future.exception()
    if exc is not None:
        return None, exc
    return future.result(), None


def _run_phase1_parallel_tasks(run_sql, run_os):
    executor = _get_phase1_executor()
    sql_future = executor.submit(run_sql)
    os_future = executor.submit(run_os)
    sql_pair = _phase1_future_result_or_error(sql_future)
    os_pair = _phase1_future_result_or_error(os_future)
    if sql_pair[1] is not None:
        raise sql_pair[1]
    if os_pair[1] is not None:
        raise os_pair[1]
    return sql_pair[0], os_pair[0]


def _correlation_score(row, support_k=10):
    """Compute ratio score with support bias toward larger denominator."""
    match_total = int(row.get("document_match_count", 0)) + int(row.get("comment_match_count", 0))
    total = int(row.get("document_total_count", 0)) + int(row.get("comment_total_count", 0))
    if total <= 0:
        return 0.0
    ratio = match_total / total
    support = total / (total + support_k)
    return ratio * support


def _row_docket_key(row):
    """Stable id for de-duping SQL vs OpenSearch (Postgres uses docket_id; some mocks use id)."""
    if "docket_id" in row:
        return str(row["docket_id"])
    return str(row["id"])


def _cfr_part_patterns_match_row(row, patterns):
    """True if any pattern matches any cfrPart value (Postgres: cp.cfrPart ILIKE %pattern%)."""
    if not patterns:
        return True
    cfr_refs = row.get("cfr_refs") or []
    for ref in cfr_refs:
        for part_key in (ref.get("cfrParts") or {}).keys():
            pk_l = str(part_key).lower()
            if any(pat in pk_l for pat in patterns):
                return True
    return False


def _docket_type_matches_filter(row, docket_type_param):
    """Postgres: d.docket_type = %s when filter set."""
    return not docket_type_param or row.get("docket_type") == docket_type_param


def _agency_matches_filter(row, agency):
    """Postgres: OR of d.agency_id ILIKE %s when agency list set."""
    if not agency:
        return True
    aid = (row.get("agency_id") or "").lower()
    return any((a or "").strip().lower() in aid for a in agency)

def _modify_date_matches_filter(row, start_date=None, end_date=None): #pylint: disable=too-many-branches
    """Return True if row's modify_date is within the optional start_date and end_date range."""
    modify_date = row.get("modify_date")
    if modify_date is None:
        return True

    # convert string -> datetime
    if isinstance(modify_date, str):
        modify_date = datetime.fromisoformat(modify_date)

    # normalize to naive UTC for comparison
    if modify_date.tzinfo is not None:
        modify_date = modify_date.astimezone(timezone.utc).replace(tzinfo=None)

    if start_date:
        start = datetime.fromisoformat(start_date)
        if modify_date < start:
            return False
    if end_date:
        end = datetime.fromisoformat(end_date)
        if modify_date > end:
            return False
    return True

def _ref_has_exact_part(ref, title, part):
    """True if ref matches the given title and part exactly."""
    if str(ref.get("title") or "").strip() != title:
        return False
    return any(str(pk).strip() == part for pk in (ref.get("cfrParts") or {}).keys())


def _cfr_exact_pairs_match_row(row, exact_pairs):
    """True if any (title, part) pair matches any cfr_ref in the row."""
    cfr_refs = row.get("cfr_refs") or []
    return any(
        _ref_has_exact_part(ref, title, part)
        for title, part in exact_pairs
        for ref in cfr_refs
    )


def _cfr_matches_filter(row, cfr_part_param):
    """Postgres: OR of cp.cfrPart ILIKE when CFR filter set."""
    if not cfr_part_param:
        return True
    exact_pairs = _cfr_exact_title_part_pairs(cfr_part_param)
    if exact_pairs:
        return _cfr_exact_pairs_match_row(row, exact_pairs)
    patterns = cfr_part_filter_patterns(cfr_part_param)
    return not patterns or _cfr_part_patterns_match_row(row, patterns)


def _json_safe_scalar(value):
    """Convert DB/driver values that jsonify may not handle on all Flask/Python combos."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _sanitize_search_row_for_json(row):
    """In-place: e.g. Postgres returns datetime for modify_date."""
    if "modify_date" in row:
        row["modify_date"] = _json_safe_scalar(row["modify_date"])


def _row_matches_advanced_filters(row, docket_type_param, agency, cfr_part_param, #pylint: disable=too-many-arguments, too-many-positional-arguments
                                  start_date=None, end_date=None):
    """
    Same constraints as _search_dockets_postgres for full-text rows loaded via get_dockets_by_ids.
    Drops OpenSearch-only hits that fail advanced filters.
    """
    return (
        _docket_type_matches_filter(row, docket_type_param)
        and _agency_matches_filter(row, agency)
        and _cfr_matches_filter(row, cfr_part_param)
        and _modify_date_matches_filter(row, start_date, end_date)
    )

def _transform_cfr_refs(result):
    """Convert raw cfr_refs into the cfrPart list format for API responses."""
    cfr_refs = result.pop("cfr_refs", None)
    if cfr_refs is not None:
        result["cfrPart"] = [
            {"title": ref.get("title"), "part": part, "link": link}
            for ref in cfr_refs
            for part, link in ref.get("cfrParts", {}).items()
        ]


class InternalLogic:  # pylint: disable=too-few-public-methods
    """Internal logic for search operations with pagination"""

    def __init__(self, database, db_layer=None):
        self.database = database
        self.db_layer = db_layer if db_layer is not None else get_db()

    def _run_search_phase1(self, query, filters) -> Tuple[list, list]:
        """
        Run Postgres title/metadata search and OpenSearch term match in parallel.

        ``filters`` is
        ``(docket_type_param, agency, cfr_part_param, start_date, end_date)``.

        Safe for one shared DBLayer: ``search`` uses only ``conn``; ``text_match_terms``
        uses only OpenSearch (see ``DBLayer.text_match_terms``).
        """
        term = (query or "").strip()
        dbl = self.db_layer
        if not _parallel_search_phase1_enabled():
            return _phase1_run_sql(dbl, query, filters), _phase1_run_os(dbl, term)
        return _run_phase1_parallel_tasks(
            lambda: _phase1_run_sql(dbl, query, filters),
            lambda: _phase1_run_os(dbl, term),
        )

    def search(self, query, docket_type_param=None, agency=None,  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches,too-many-statements,too-many-locals
               cfr_part_param=None, start_date=None, end_date=None, page=1, page_size=10,
               sort_by=None):
        """
        Search with pagination support.

        Args:
            query: Search query string
            docket_type_param: Filter by docket type
            agency: Filter by agency
            cfr_part_param: Filter by CFR part
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            dict: Paginated response with metadata
        """
        sql_results, os_hits = self._run_search_phase1(
            query,
            (docket_type_param, agency, cfr_part_param, start_date, end_date),
        )
        title_rows = [{**r, "match_source": "title"} for r in sql_results]
        title_ids = {_row_docket_key(r) for r in sql_results}

        os_counts_by_id = {str(hit["docket_id"]): hit for hit in os_hits}

        # Get new IDs from OpenSearch not in SQL results
        new_ids_ordered = self._get_new_docket_ids(os_hits, title_ids)

        # Enhance title rows with OpenSearch counts
        self._enhance_rows_with_os_counts(title_rows, os_counts_by_id)

        # Get full text rows for new IDs
        full_text_rows = self._get_full_text_rows(
            new_ids_ordered, os_counts_by_id, docket_type_param, agency, cfr_part_param,
            start_date, end_date
        )

        all_results = title_rows + full_text_rows

        # Add totals and scores
        self._add_totals_and_scores(all_results)

        # Sort results
        self._sort_results(all_results, sort_by=sort_by)

        # Paginate
        return self._paginate_results(all_results, page, page_size)

    def _get_new_docket_ids(self, os_hits, title_ids):
        """Extract docket IDs from OpenSearch hits not already in title results."""
        new_ids_ordered = []
        seen_new = set()
        for hit in os_hits:
            did = str(hit["docket_id"])
            if did in title_ids or did in seen_new:
                continue
            seen_new.add(did)
            new_ids_ordered.append(did)
        return new_ids_ordered

    def _enhance_rows_with_os_counts(self, rows, os_counts_by_id):
        """Add OpenSearch match counts to rows."""
        for row in rows:
            did = _row_docket_key(row)
            hit = os_counts_by_id.get(did)
            row["document_match_count"] = hit["document_match_count"] if hit else 0
            row["comment_match_count"] = hit["comment_match_count"] if hit else 0

    def _get_full_text_rows(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
            self, docket_ids, os_counts_by_id,
            docket_type_param, agency, cfr_part_param,
            start_date=None, end_date=None):
        """Fetch and filter full text rows for docket IDs not in SQL results."""
        if not docket_ids:
            return []

        # Pre-filter docket IDs using lightweight query
        # This filters by agency, docket_type, and dates WITHOUT fetching full data
        filtered_ids = self.db_layer.get_docket_ids_matching_filters(
            docket_ids,
            agency=agency,
            docket_type=docket_type_param,
            start_date=start_date,
            end_date=end_date
        )

        # If nothing passed filters, return early
        if not filtered_ids:
            return []

        # Limit to top 100 to avoid fetching thousands of dockets
        filtered_ids = filtered_ids[:100]

        # Fetch full data only for dockets that passed filters
        fetched = self.db_layer.get_dockets_by_ids(filtered_ids)
        by_id = {str(r["docket_id"]): r for r in fetched}

        full_text_rows = []
        for did in filtered_ids:  # Iterate over filtered list, not original
            row = by_id.get(did)
            if row is None:
                continue
            # Still need to check CFR filter since we couldn't do that in SQL
            if not _row_matches_advanced_filters(row, docket_type_param, agency, cfr_part_param,
                                                start_date, end_date):
                continue
            h = os_counts_by_id.get(did, {})
            full_text_rows.append({
                **row,
                "match_source": "full_text",
                "document_match_count": h.get("document_match_count", 0),
                "comment_match_count": h.get("comment_match_count", 0),
            })
        return full_text_rows

    def _add_totals_and_scores(self, rows):
        """Add document/comment totals and correlation scores to rows."""
        docket_ids = [_row_docket_key(r) for r in rows]
        totals_map = self.db_layer.get_docket_document_comment_totals(docket_ids)

        for row in rows:
            did = _row_docket_key(row)
            totals = totals_map.get(did, {})
            row["document_total_count"] = totals.get("document_total_count", 0)
            row["comment_total_count"] = totals.get("comment_total_count", 0)
            row["correlation_score"] = _correlation_score(row)

    def _sort_results(self, rows, sort_by=None):
        """Sort results by the requested field, defaulting to relevance."""
        if sort_by == "modify_date":
            rows.sort(key=lambda r: r.get("modify_date") or "", reverse=True)
        elif sort_by == "comment_count":
            rows.sort(key=lambda r: int(r.get("comment_total_count", 0)), reverse=True)
        elif sort_by == "document_count":
            rows.sort(key=lambda r: int(r.get("document_total_count", 0)), reverse=True)
        else:
            rows.sort(
                key=lambda r: (
                    r.get("correlation_score", 0.0),
                    int(r.get("document_match_count", 0)) + int(r.get("comment_match_count", 0)),
                    int(r.get("document_total_count", 0)) + int(r.get("comment_total_count", 0)),
                    r.get("docket_id", ""),
                ),
                reverse=True
            )

    def _paginate_results(self, all_results, page, page_size): # pylint: disable=too-many-locals
        """Apply pagination and transform results for API response."""
        total_results = len(all_results)
        total_pages = (total_results + page_size - 1) // page_size

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        page_results = all_results[start_idx:end_idx]

        # Sanitize and transform results
        for result in page_results:
            _sanitize_search_row_for_json(result)
            _transform_cfr_refs(result)

        # Rename keys for API
        key_map = {
            "document_match_count": "documentNumerator",
            "comment_match_count": "commentNumerator",
            "document_total_count": "documentDenominator",
            "comment_total_count": "commentDenominator",
        }
        for result in page_results:
            for old, new in key_map.items():
                if old in result:
                    result[new] = result.pop(old)

        return {
            "results": page_results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": total_results,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    def get_collection_dockets(self, collection_id: int, user_email: str,
                               page: int = 1, page_size: int = 10) -> dict:
        # pylint: disable=too-many-locals
        """
        Return paginated dockets belonging to a collection owned by the user.

        Args:
            collection_id: ID of the collection
            user_email: Email of the requesting user (ownership check)
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            dict with paginated results and pagination metadata, or None if not found
        """
        collections = self.db_layer.get_collections(user_email)
        collection = next(
            (c for c in collections if c["collection_id"] == collection_id), None
        )
        if collection is None:
            return None

        docket_ids = collection.get("docket_ids") or []
        if not docket_ids:
            return {
                "results": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_results": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False,
                }
            }

        all_dockets = self.db_layer.get_dockets_by_ids(docket_ids)

        docket_id_list = [str(d["docket_id"]) for d in all_dockets]
        totals_map = self.db_layer.get_docket_document_comment_totals(docket_id_list)
        for result in all_dockets:
            did = str(result["docket_id"])
            totals = totals_map.get(did, {})
            result["documentDenominator"] = totals.get("document_total_count", 0)
            result["commentDenominator"] = totals.get("comment_total_count", 0)

        for result in all_dockets:
            _sanitize_search_row_for_json(result)
            _transform_cfr_refs(result)

        total_results = len(all_dockets)
        total_pages = max((total_results + page_size - 1) // page_size, 1)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return {
            "results": all_dockets[start_idx:end_idx],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": total_results,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }

    def get_agencies(self) -> List[str]:
        return self.db_layer.get_agencies()
