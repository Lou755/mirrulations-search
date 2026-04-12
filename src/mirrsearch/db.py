import json
from dataclasses import dataclass
from typing import List, Dict, Any, Set
import os
import psycopg2
from opensearchpy import OpenSearch
try:
    import requests
    from requests_aws4auth import AWS4Auth
except ImportError:
    requests = None
    AWS4Auth = None

try:
    import boto3
except ImportError:
    boto3 = None

try:
    from dotenv import load_dotenv
except ImportError:
    LOAD_DOTENV = None
else:
    LOAD_DOTENV = load_dotenv


def _parse_opensearch_port_env(var_name: str, default: int = 9200) -> int:
    """Parse OPENSEARCH_PORT safely — empty or invalid values fall back to default."""
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        return default
    try:
        port = int(raw)
    except ValueError:
        return default
    if port < 1 or port > 65535:
        return default
    return port


def _env_flag_true(var_name: str) -> bool:
    return (os.getenv(var_name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _cfr_part_item_pattern(item: Any) -> str:
    """Single CFR filter value → lowercase substring, or '' if absent."""
    if isinstance(item, dict):
        return (item.get("part") or "").strip().lower()
    if item is None:
        return ""
    return str(item).strip().lower()


def cfr_part_filter_patterns(cfr_part_param) -> List[str]:
    """
    Build lowercase substring patterns for CFR part filtering.

    Accepts plain strings or dicts with a ``part`` key from the UI.
    """
    if not cfr_part_param:
        return []
    return [p for p in (_cfr_part_item_pattern(i) for i in cfr_part_param) if p]


def _cfr_exact_title_part_pairs(cfr_part_param) -> List[tuple]:
    """Extract exact CFR (title, part) pairs from dict-style filter payloads."""
    if not cfr_part_param:
        return []
    pairs: List[tuple] = []
    for item in cfr_part_param:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        part = str(item.get("part") or "").strip()
        if title and part:
            pairs.append((title, part))
    return pairs


def _parse_positive_int_env(var_name: str, default: int) -> int:
    """Parse env var as positive int, falling back to default."""
    raw = (os.getenv(var_name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def _opensearch_match_docket_bucket_size() -> int:
    """How many docket buckets to request for corpus-wide match aggregations."""
    return _parse_positive_int_env("OPENSEARCH_MATCH_DOCKET_BUCKET_SIZE", 50000)


def _opensearch_comment_id_terms_size() -> int:
    """Max distinct commentId values per docket in nested terms aggregations."""
    return _parse_positive_int_env("OPENSEARCH_COMMENT_ID_TERMS_SIZE", 65535)


@dataclass(frozen=True)
class DBLayer:  # pylint: disable=too-many-public-methods
    conn: Any = None

    def search( # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
            self,
            query: str,
            docket_type_param: str = None,
            agency: List[str] = None,
            cfr_part_param: List[str] = None,
            start_date: str = None,
            end_date: str = None) \
            -> List[Dict[str, Any]]:
        if self.conn is None:
            return []
        results = self._search_dockets_postgres(
            query, docket_type_param, agency, cfr_part_param, start_date, end_date
        )
        exact_pairs = _cfr_exact_title_part_pairs(cfr_part_param)
        if not exact_pairs:
            return results
        allowed = self._get_cfr_docket_ids(exact_pairs)
        return [row for row in results if row["docket_id"] in allowed]

    def _get_cfr_docket_ids(self, cfr_pairs: List[tuple]) -> Set[str]:
        """Return docket IDs matching exact CFR title+part pairs."""
        if self.conn is None or not cfr_pairs:
            return set()
        clauses = " OR ".join("(cp.title = %s AND cp.cfrPart = %s)" for _ in cfr_pairs)
        sql = f"""
            SELECT DISTINCT d.docket_id
            FROM documentsWithFRdoc d
            JOIN cfrparts cp ON cp.frdocnum = d.frdocnum
            WHERE ({clauses})
        """
        params: List[str] = []
        for title, part in cfr_pairs:
            params.append(title)
            params.append(part)
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return {row[0] for row in cur.fetchall()}

    def _search_dockets_postgres(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
            self, query: str, docket_type_param: str = None,
            agency: List[str] = None,
            cfr_part_param: List[str] = None,
            start_date: str = None,
            end_date: str = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT DISTINCT
                d.docket_id,
                d.docket_title,
                d.agency_id,
                d.docket_type,
                d.modify_date,
                cp.title,
                cp.cfrPart,
                l.link
            FROM dockets d
            JOIN documentsWithFRdoc doc ON doc.docket_id = d.docket_id
            LEFT JOIN cfrparts cp ON cp.frdocnum = doc.frdocnum
            LEFT JOIN links l ON l.title = cp.title AND l.cfrPart = cp.cfrPart
            WHERE d.docket_title ILIKE %s
        """
        params = [f"%{(query or '').strip().lower()}%"]

        if docket_type_param:
            sql += " AND d.docket_type = %s"
            params.append(docket_type_param)

        if agency:
            clauses = " OR ".join("d.agency_id ILIKE %s" for _ in agency)
            sql += f" AND ({clauses})"
            params.extend(f"%{a}%" for a in agency)

        if start_date:
            sql += " AND d.modify_date::date >= %s::date"
            params.append(start_date)

        if end_date:
            sql += " AND d.modify_date::date <= %s::date"
            params.append(end_date)

        cfr_patterns = cfr_part_filter_patterns(cfr_part_param)
        if cfr_patterns:
            clauses = " OR ".join("cp3.cfrPart = %s" for _ in cfr_patterns)
            sql += (
                " AND EXISTS ("
                "SELECT 1 FROM documentsWithFRdoc d3 "
                "JOIN cfrparts cp3 ON cp3.frdocnum = d3.frdocnum "
                "WHERE d3.docket_id = d.docket_id "
                f"AND ({clauses})"
                ")"
            )
            params.extend(cfr_patterns)

        exact_pairs = _cfr_exact_title_part_pairs(cfr_part_param)
        if exact_pairs:
            exact_clauses = " OR ".join(
                "(cp2.title = %s AND cp2.cfrPart = %s)" for _ in exact_pairs
            )
            sql += (
                " AND EXISTS ("
                "SELECT 1 FROM documentsWithFRdoc d2 "
                "JOIN cfrparts cp2 ON cp2.frdocnum = d2.frdocnum "
                "WHERE d2.docket_id = d.docket_id "
                f"AND ({exact_clauses})"
                ")"
            )
            for title, part in exact_pairs:
                params.extend([title, part])

        sql += " ORDER BY d.modify_date DESC, d.docket_id, cp.title, cp.cfrPart LIMIT 50"

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            dockets = {}
            for row in cur.fetchall():
                self._process_docket_row(dockets, row)
            return [
                {**d, "cfr_refs": list(d["cfr_refs"].values())}
                for d in dockets.values()
            ]

    def get_dockets_by_ids(self, docket_ids: List[str]) -> List[Dict[str, Any]]:
        if self.conn is None or not docket_ids:
            return []
        sql = """
            SELECT DISTINCT
                d.docket_id,
                d.docket_title,
                d.agency_id,
                d.docket_type,
                d.modify_date,
                cp.title,
                cp.cfrPart,
                l.link
            FROM dockets d
            JOIN documentsWithFRdoc doc ON doc.docket_id = d.docket_id
            LEFT JOIN cfrparts cp ON cp.frdocnum = doc.frdocnum
            LEFT JOIN links l ON l.title = cp.title AND l.cfrPart = cp.cfrPart
            WHERE d.docket_id = ANY(%s)
            ORDER BY d.modify_date DESC, d.docket_id, cp.title, cp.cfrPart
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (list(docket_ids),))
            dockets = {}
            for row in cur.fetchall():
                self._process_docket_row(dockets, row)
            return [
                {**d, "cfr_refs": list(d["cfr_refs"].values())}
                for d in dockets.values()
            ]

    def get_docket_ids_matching_filters(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
            self,
            docket_ids: List[str],
            agency: List[str] = None,
            docket_type: str = None,
            start_date: str = None,
            end_date: str = None
    ) -> List[str]:
        """
        Lightweight query: returns only docket IDs that match filter criteria.
        Much faster than get_dockets_by_ids since it doesn't fetch full docket data.
        """
        if self.conn is None or not docket_ids:
            return []

        sql = "SELECT docket_id FROM dockets WHERE docket_id = ANY(%s)"
        params = [docket_ids]

        if agency:
            clauses = " OR ".join("agency_id ILIKE %s" for _ in agency)
            sql += f" AND ({clauses})"
            params.extend(f"%{a}%" for a in agency)

        if docket_type:
            sql += " AND docket_type = %s"
            params.append(docket_type)

        if start_date:
            sql += " AND modify_date >= %s::TIMESTAMP"
            params.append(start_date)

        if end_date:
            sql += " AND modify_date <= %s::TIMESTAMP"
            params.append(end_date)

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return [row[0] for row in cur.fetchall()]

    def get_agencies(self) -> List[str]:
        if self.conn is None:
            return []
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT agency_id FROM dockets ORDER BY agency_id")
            return [row[0] for row in cur.fetchall()]

    @staticmethod
    def _process_docket_row(dockets, row):
        docket_id = row[0]
        if docket_id not in dockets:
            dockets[docket_id] = {
                "docket_id": row[0],
                "docket_title": row[1],
                "agency_id": row[2],
                "docket_type": row[3],
                "modify_date": row[4],
                "cfr_refs": {}
            }
        title, cfr_part, link = row[5], row[6], row[7]
        if title is not None and cfr_part is not None:
            if title not in dockets[docket_id]["cfr_refs"]:
                dockets[docket_id]["cfr_refs"][title] = {
                    "title": title,
                    "cfrParts": {}
                }
            dockets[docket_id]["cfr_refs"][title]["cfrParts"][cfr_part] = link

    @staticmethod
    def _build_docket_agg_query(agg_name: str, match_clauses: List[Dict]) -> Dict:
        """Build a docket-bucketed aggregation query with an inner filter."""
        return {
            "size": 0,
            "aggs": {
                "by_docket": {
                    "terms": {
                        "field": "docketId.keyword",
                        "size": _opensearch_match_docket_bucket_size(),
                    },
                    "aggs": {
                        agg_name: {
                            "filter": {
                                "bool": {
                                    "should": match_clauses,
                                    "minimum_should_match": 1
                                }
                            }
                        }
                    }
                }
            }
        }

    @staticmethod
    def _build_docket_agg_query_unique_comments(
            agg_name: str, match_clauses: List[Dict]) -> Dict:
        """Like _build_docket_agg_query but counts unique commentId per docket."""
        return {
            "size": 0,
            "aggs": {
                "by_docket": {
                    "terms": {
                        "field": "docketId.keyword",
                        "size": _opensearch_match_docket_bucket_size(),
                    },
                    "aggs": {
                        agg_name: {
                            "filter": {
                                "bool": {
                                    "should": match_clauses,
                                    "minimum_should_match": 1
                                }
                            },
                            "aggs": {
                                "by_comment": {
                                    "terms": {
                                        "field": "commentId.keyword",
                                        "size": _opensearch_comment_id_terms_size(),
                                    }
                                }
                            },
                        }
                    },
                }
            },
        }

    @staticmethod
    def _comment_ids_per_docket_from_agg(
            resp: Dict, agg_name: str) -> Dict[str, Set[str]]:
        """Parse by_docket -> filter agg -> terms on commentId."""
        out: Dict[str, Set[str]] = {}
        for bucket in resp.get("aggregations", {}).get("by_docket", {}).get("buckets", []):
            did = str(bucket["key"])
            inner = bucket.get(agg_name, {})
            by_comment = inner.get("by_comment", {})
            keys = {str(b["key"]) for b in by_comment.get("buckets", [])}
            if keys:
                out.setdefault(did, set()).update(keys)
        return out

    @staticmethod
    def _merge_unique_comment_matches(
            comments_resp: Dict, extracted_resp: Dict) -> Dict[str, int]:
        """Union commentIds from comments and extracted-text index per docket."""
        from_comments = DBLayer._comment_ids_per_docket_from_agg(
            comments_resp, "matching_comments")
        from_extracted = DBLayer._comment_ids_per_docket_from_agg(
            extracted_resp, "matching_extracted")
        counts: Dict[str, int] = {}
        for did in set(from_comments) | set(from_extracted):
            merged = set(from_comments.get(did, set())) | set(from_extracted.get(did, set()))
            if merged:
                counts[did] = len(merged)
        return counts

    @staticmethod
    def _accumulate_counts(
            docket_counts: Dict, buckets: List, agg_name: str, count_key: str) -> None:
        """Add match counts from OpenSearch buckets into docket_counts in place."""
        for bucket in buckets:
            match_count = bucket[agg_name]["doc_count"]
            if match_count > 0:
                docket_id = bucket["key"]
                docket_counts.setdefault(
                    docket_id, {"document_match_count": 0, "comment_match_count": 0}
                )
                docket_counts[docket_id][count_key] += match_count

    def text_match_terms(
            self, terms: List[str], opensearch_client=None) -> List[Dict[str, Any]]:
        """
        Search OpenSearch for dockets containing the given terms.

        Searches:
        - documents_text index: title and documentText fields
        - comments index: commentText field
        - comments_extracted_text index: extractedText field

        Returns list of {docket_id, document_match_count, comment_match_count}.
        """
        if opensearch_client is None:
            opensearch_client = get_opensearch_connection()
        try:
            return self._run_text_match_queries(opensearch_client, terms)
        except (KeyError, AttributeError) as e:
            print(f"OpenSearch query failed: {e}")
            return []
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"OpenSearch query failed (fallback to SQL): {e}")
            return []

    @staticmethod
    def _comment_total_query(docket_ids: List[str]) -> Dict:
        """Aggregation: per docket, distinct commentId across all matching docs."""
        return {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"docketId.keyword": docket_ids}}
                    ]
                }
            },
            "aggs": {
                "by_docket": {
                    "terms": {"field": "docketId.keyword", "size": len(docket_ids)},
                    "aggs": {
                        "by_comment": {
                            "terms": {
                                "field": "commentId.keyword",
                                "size": _opensearch_comment_id_terms_size(),
                            }
                        }
                    },
                }
            },
        }

    def get_docket_document_comment_totals(
            self,
            docket_ids: List[str],
            opensearch_client=None
    ) -> Dict[str, Dict[str, int]]:
        """Return per-docket totals for documents and comments."""
        if not docket_ids:
            return {}
        if opensearch_client is None:
            opensearch_client = get_opensearch_connection()
        try:
            return self._fetch_docket_totals(opensearch_client, docket_ids)
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"OpenSearch totals query failed (fallback zeros): {e}")
            return {}

    def _fetch_docket_totals(  # pylint: disable=too-many-locals
            self, opensearch_client, docket_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """Document totals from RDS, comment totals from OpenSearch."""
        totals: Dict[str, Dict[str, int]] = {}
        if self.conn is not None:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT docket_id, COUNT(*) FROM documentsWithFRdoc "
                    "WHERE docket_id = ANY(%s) GROUP BY docket_id",
                    (list(docket_ids),)
                )
                for docket_id, count in cur.fetchall():
                    totals[docket_id] = {"document_total_count": count, "comment_total_count": 0}
        comment_query = {
            "size": 0,
            "query": {"bool": {"filter": [{"terms": {"docketId.keyword": docket_ids}}]}},
            "aggs": {"by_docket": {"terms": {"field": "docketId.keyword", "size": len(docket_ids)}}}
        }
        try:
            resp = opensearch_client.search(index="comments", body=comment_query)
            for bucket in resp["aggregations"]["by_docket"]["buckets"]:
                docket_id = str(bucket["key"])
                totals.setdefault(docket_id, {"document_total_count": 0, "comment_total_count": 0})
                totals[docket_id]["comment_total_count"] = bucket["doc_count"]
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Comment totals query failed: {e}")
        return totals

    def _run_text_match_queries(  # pylint: disable=too-many-locals
            self, opensearch_client, terms: List[str]) -> List[Dict[str, Any]]:
        """Execute all three OpenSearch queries and merge their results."""
        def buckets(resp):
            return resp["aggregations"]["by_docket"]["buckets"]

        def safe_search(index: str, body: Dict) -> Dict:
            try:
                return opensearch_client.search(index=index, body=body)
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"OpenSearch index query failed for '{index}': {e}")
                return {"aggregations": {"by_docket": {"buckets": []}}}

        docket_counts: Dict = {}
        doc_resp = safe_search(
            "documents_text",
            self._build_docket_agg_query(
                "matching_docs",
                [{"multi_match": {"query": t, "fields": ["title", "documentText"]}}
                 for t in terms],
            ),
        )
        comment_resp = safe_search(
            "comments",
            self._build_docket_agg_query_unique_comments(
                "matching_comments",
                [{"match": {"commentText": t}} for t in terms],
            ),
        )
        extracted_resp = safe_search(
            "comments_extracted_text",
            self._build_docket_agg_query_unique_comments(
                "matching_extracted",
                [{"match": {"extractedText": t}} for t in terms],
            ),
        )
        self._accumulate_counts(
            docket_counts, buckets(doc_resp), "matching_docs", "document_match_count"
        )
        comment_ids_by_docket = self._comment_ids_per_docket_from_agg(
            comment_resp, "matching_comments"
        )
        extracted_ids_by_docket = self._comment_ids_per_docket_from_agg(
            extracted_resp, "matching_extracted"
        )
        all_dockets = set(comment_ids_by_docket) | set(extracted_ids_by_docket)
        for did in all_dockets:
            merged = (set(comment_ids_by_docket.get(did, set()))
                      | set(extracted_ids_by_docket.get(did, set())))
            docket_counts.setdefault(
                did, {"document_match_count": 0, "comment_match_count": 0}
            )
            docket_counts[did]["comment_match_count"] = len(merged)
        return [{"docket_id": did, **counts} for did, counts in docket_counts.items()]

    def get_collections(self, user_email: str) -> List[Dict[str, Any]]:
        """Return all collections belonging to the given user."""
        if self.conn is None:
            return []
        sql = """
            SELECT c.collection_id, c.collection_name, c.user_email,
                   COALESCE(
                       json_agg(cd.docket_id) FILTER (WHERE cd.docket_id IS NOT NULL),
                       '[]'
                   ) AS docket_ids
            FROM collections c
            LEFT JOIN collection_dockets cd ON cd.collection_id = c.collection_id
            WHERE c.user_email = %s
            GROUP BY c.collection_id, c.collection_name, c.user_email
            ORDER BY c.collection_id
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (user_email,))
            return [
                {
                    "collection_id": row[0],
                    "name": row[1],
                    "user_email": row[2],
                    "docket_ids": row[3] if isinstance(row[3], list) else []
                }
                for row in cur.fetchall()
            ]

    def create_collection(self, user_email: str, name: str) -> int:
        """Create a new collection for the user and return its id."""
        if self.conn is None:
            return -1
        upsert_user_sql = """
            INSERT INTO users (email, name) VALUES (%s, %s)
            ON CONFLICT (email) DO NOTHING
        """
        with self.conn.cursor() as cur:
            cur.execute(upsert_user_sql, (user_email, user_email))
        insert_sql = """
            INSERT INTO collections (user_email, collection_name)
            VALUES (%s, %s)
            RETURNING collection_id
        """
        with self.conn.cursor() as cur:
            cur.execute(insert_sql, (user_email, name))
            collection_id = cur.fetchone()[0]
        self.conn.commit()
        return collection_id

    def delete_collection(self, collection_id: int, user_email: str) -> bool:
        """Delete a collection owned by the user. Returns True if deleted."""
        if self.conn is None:
            return False
        sql = """
            DELETE FROM collections
            WHERE collection_id = %s AND user_email = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (collection_id, user_email))
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def add_docket_to_collection(
            self, collection_id: int, docket_id: str, user_email: str) -> bool:
        """Add a docket to a collection the user owns. Returns True if successful."""
        if self.conn is None:
            return False
        check_sql = """
            SELECT 1 FROM collections
            WHERE collection_id = %s AND user_email = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(check_sql, (collection_id, user_email))
            if cur.fetchone() is None:
                return False
        insert_sql = """
            INSERT INTO collection_dockets (collection_id, docket_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """
        with self.conn.cursor() as cur:
            cur.execute(insert_sql, (collection_id, docket_id))
        self.conn.commit()
        return True

    def remove_docket_from_collection(
            self, collection_id: int, docket_id: str, user_email: str) -> bool:
        """Remove a docket from a collection the user owns. Returns True if successful."""
        if self.conn is None:
            return False
        check_sql = """
            SELECT 1 FROM collections
            WHERE collection_id = %s AND user_email = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(check_sql, (collection_id, user_email))
            if cur.fetchone() is None:
                return False
        delete_sql = """
            DELETE FROM collection_dockets
            WHERE collection_id = %s AND docket_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(delete_sql, (collection_id, docket_id))
        self.conn.commit()
        return True

    def create_download_job(  # pylint: disable=too-many-locals
            self,
            user_email: str,
            docket_ids: List[str],
            format: str = "zip",  # pylint: disable=redefined-builtin
            include_binaries: bool = False,
    ) -> str:
        """Create a download job and return the new job_id (UUID string)."""
        if self.conn is None:
            return ""
        upsert_user_sql = """
            INSERT INTO users (email, name) VALUES (%s, %s)
            ON CONFLICT (email) DO NOTHING
        """
        with self.conn.cursor() as cur:
            cur.execute(upsert_user_sql, (user_email, user_email))
        insert_sql = """
            INSERT INTO download_jobs
                (user_email, docket_ids, format, include_binaries)
            VALUES (%s, %s, %s, %s)
            RETURNING job_id
        """
        with self.conn.cursor() as cur:
            cur.execute(insert_sql, (user_email, docket_ids, format, include_binaries))
            job_id = str(cur.fetchone()[0])
        self.conn.commit()
        return job_id

    def get_download_job(self, job_id: str, user_email: str) -> Dict[str, Any]:
        """Return job details for the given job_id owned by user_email, or {}."""
        if self.conn is None:
            return {}
        sql = """
            SELECT job_id, user_email, docket_ids, format, include_binaries,
                   status, s3_path, created_at, updated_at, expires_at
            FROM download_jobs
            WHERE job_id = %s AND user_email = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (job_id, user_email))
            row = cur.fetchone()
        if row is None:
            return {}
        return {
            "job_id": str(row[0]),
            "user_email": row[1],
            "docket_ids": row[2],
            "format": row[3],
            "include_binaries": row[4],
            "status": row[5],
            "s3_path": row[6],
            "created_at": row[7],
            "updated_at": row[8],
            "expires_at": row[9],
        }

    def update_download_job_status(
            self, job_id: str, status: str, s3_path: str = None) -> bool:
        """Update the status (and optionally s3_path) of a download job.

        Returns True if a row was updated.
        """
        if self.conn is None:
            return False
        sql = """
            UPDATE download_jobs
            SET status = %s, s3_path = %s, updated_at = NOW()
            WHERE job_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (status, s3_path, job_id))
            updated = cur.rowcount > 0
        self.conn.commit()
        return updated

    def prune_expired_download_jobs(self) -> int:
        """Delete download_jobs past their expires_at. Returns the number of rows deleted."""
        if self.conn is None:
            return 0
        sql = "DELETE FROM download_jobs WHERE expires_at < NOW()"
        with self.conn.cursor() as cur:
            cur.execute(sql)
            deleted = cur.rowcount
        self.conn.commit()
        return deleted

    def is_admin(self, email: str) -> bool:
        """Return True if the given email belongs to an admin."""
        if self.conn is None:
            return False
        sql = "SELECT 1 FROM admins WHERE email = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (email,))
            return cur.fetchone() is not None

    def is_authorized_user(self, email: str) -> bool:
        """Return True if the given email is in the authorized users list."""
        if self.conn is None:
            return False
        sql = "SELECT 1 FROM authorized_users WHERE email = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (email,))
            return cur.fetchone() is not None

    def add_authorized_user(self, email: str, name: str) -> bool:
        """Add a user to the authorized users list. Returns True if successful."""
        if self.conn is None:
            return False
        sql = """
            INSERT INTO authorized_users (email, name)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (email, name))
        self.conn.commit()
        return True

    def remove_authorized_user(self, email: str) -> bool:
        """Remove a user from the authorized users list. Returns True if deleted."""
        if self.conn is None:
            return False
        sql = "DELETE FROM authorized_users WHERE email = %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, (email,))
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def get_authorized_users(self) -> List[Dict[str, Any]]:
        """Return all authorized users."""
        if self.conn is None:
            return []
        sql = """
            SELECT email, name, authorized_at
            FROM authorized_users
            ORDER BY authorized_at DESC
        """
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return [
                {
                    "email": row[0],
                    "name": row[1],
                    "authorized_at": row[2]
                }
                for row in cur.fetchall()
            ]

def _get_secrets_from_aws() -> Dict[str, str]:
    if boto3 is None:
        raise ImportError("boto3 is required to use AWS Secrets Manager.")
    client = boto3.client("secretsmanager", region_name="YOUR_REGION")
    response = client.get_secret_value(SecretId="YOUR_SECRET_NAME")
    return json.loads(response["SecretString"])


def get_postgres_connection() -> DBLayer:
    use_aws_secrets = os.getenv("USE_AWS_SECRETS", "").lower() in {"1", "true", "yes", "on"}
    if use_aws_secrets:
        creds = _get_secrets_from_aws()
        conn = psycopg2.connect(
            host=creds["host"],
            port=creds["port"],
            database=creds["db"],
            user=creds["username"],
            password=creds["password"]
        )
    else:
        if LOAD_DOTENV is not None:
            LOAD_DOTENV()
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "your_db"),
            user=os.getenv("DB_USER", "your_user"),
            password=os.getenv("DB_PASSWORD", "your_password")
        )
    return DBLayer(conn)


def get_db() -> DBLayer:
    if LOAD_DOTENV is not None:
        LOAD_DOTENV()
    try:
        return get_postgres_connection()
    except psycopg2.OperationalError:
        return DBLayer()


def _opensearch_use_ssl_from_env(user: str, password: str) -> bool:
    """Default to HTTPS when both user and password are set."""
    raw = (os.getenv("OPENSEARCH_USE_SSL") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if _env_flag_true("OPENSEARCH_USE_SSL"):
        return True
    return bool(not raw and user and password)


def _opensearch_client_kwargs() -> Dict[str, Any]:
    """Build keyword args for OpenSearch client."""
    host = (os.getenv("OPENSEARCH_HOST") or "localhost").strip() or "localhost"
    port = _parse_opensearch_port_env("OPENSEARCH_PORT", 9200)
    user = (os.getenv("OPENSEARCH_USER") or os.getenv("OPENSEARCH_USERNAME") or "").strip()
    password = (
        os.getenv("OPENSEARCH_PASSWORD")
        or os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")
        or ""
    ).strip()
    use_ssl = _opensearch_use_ssl_from_env(user, password)
    verify = _env_flag_true("OPENSEARCH_VERIFY_CERTS")
    host_entry: Dict[str, Any] = {"host": host, "port": port}
    if use_ssl:
        host_entry["scheme"] = "https"
    kwargs: Dict[str, Any] = {
        "hosts": [host_entry],
        "use_ssl": use_ssl,
        "verify_certs": verify if use_ssl else False,
        "ssl_show_warn": False,
    }
    if use_ssl and not verify:
        kwargs["ssl_assert_hostname"] = False
    if user and password:
        kwargs["http_auth"] = (user, password)
    return kwargs


class _AossClient:  # pylint: disable=too-few-public-methods
    """Thin requests-based client that mimics opensearchpy .search() interface."""
    def __init__(self, base_url, session):
        self.base_url = base_url.rstrip('/')
        self.session = session

    def search(self, index, body):
        url = f"{self.base_url}/{index}/_search"
        resp = self.session.post(url, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


_OPENSEARCH_CLIENT_SINGLETON = None


def get_opensearch_connection():  # pylint: disable=too-many-branches,too-many-statements
    global _OPENSEARCH_CLIENT_SINGLETON  # pylint: disable=global-statement

    host = (os.getenv("OPENSEARCH_HOST") or "").strip()

    use_aws = os.getenv("USE_AWS_SECRETS", "").lower() in {"1", "true", "yes", "on"}
    if not host and use_aws and boto3 is not None:
        try:
            sm = boto3.client("secretsmanager", region_name="us-east-1")
            secret = json.loads(
                sm.get_secret_value(SecretId="mirrulations/opensearch")["SecretString"]
            )
            raw_host = secret.get("host", "").strip()
            if raw_host and not raw_host.startswith("http"):
                raw_host = "https://" + raw_host
            host = raw_host
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    if "aoss.amazonaws.com" in host:
        if _OPENSEARCH_CLIENT_SINGLETON is not None:
            return _OPENSEARCH_CLIENT_SINGLETON
        creds = boto3.Session().get_credentials()
        auth = AWS4Auth(
            refreshable_credentials=creds,
            region="us-east-1",
            service="aoss",
        )
        session = requests.Session()
        session.auth = auth
        _OPENSEARCH_CLIENT_SINGLETON = _AossClient(host, session)
        return _OPENSEARCH_CLIENT_SINGLETON

    if LOAD_DOTENV is not None:
        LOAD_DOTENV()
    return OpenSearch(**_opensearch_client_kwargs())
