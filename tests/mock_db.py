import re
from typing import List, Dict, Any, Set


class MockDBLayer:  # pylint: disable=too-many-public-methods
    """
    Mock DB layer that returns hardcoded dummy data for testing.
    Mirrors the interface of DBLayer without any DB connection.
    """

    def __init__(self):
        self._collections = {}
        self._next_collection_id = 1
        self._jobs = {}

    def _items(self) -> List[Dict[str, Any]]:
        return [
            {
                "docket_id": "CMS-2025-0240",
                "title": (
                    "CY 2026 Changes to the End-Stage Renal Disease (ESRD) "
                    "Prospective Payment System and Quality Incentive Program. "
                    "CMS1830-P Display"
                ),
                "cfrPart": "42 CFR Parts 413 and 512",
                "agency_id": "CMS",
                "document_type": "Proposed Rule",
            },
            {
                "docket_id": "CMS-2025-0240",
                "title": (
                    "Medicare Program: End-Stage Renal Disease Prospective "
                    "Payment System, Payment for Renal Dialysis Services "
                    "Furnished to Individuals with Acute Kidney Injury, "
                    "End-Stage Renal Disease Quality Incentive Program, and "
                    "End-Stage Renal Disease Treatment Choices Model"
                ),
                "cfrPart": "42 CFR Parts 413 and 512",
                "agency_id": "CMS",
                "document_type": "Proposed Rule",
            },
        ]

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all dummy records without filtering."""
        return self._items()

    def search( # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,unused-argument
            self,
            query: str,
            document_type_param: str = None,
            agency: List[str] = None,
            cfr_part_param: List[str] = None,
            start_date: str = None,
            end_date: str = None) \
            -> List[Dict[str, Any]]:
        q = re.sub(r'[^\w\s-]', '', (query or "")).strip().lower()
        results = [
            item for item in self._items()
            if not q
            or q in item["docket_id"].lower()
            or q in item["title"].lower()
            or q in item["agency_id"].lower()
        ]
        if document_type_param:
            results = [
                item for item in results
                if item["document_type"].lower() == document_type_param.lower()
            ]
        if agency:
            results = [
                item for item in results
                if any(a.lower() in item["agency_id"].lower() for a in agency)
            ]
        if cfr_part_param:
            results = [
                item for item in results
                if any(
                    c['title'].lower() in item["cfrPart"].lower()
                    and c['part'].lower() in item["cfrPart"].lower()
                    for c in cfr_part_param
                )
            ]
        return results

    def get_agencies(self) -> List[str]:
        return sorted({item["agency_id"] for item in self._items()})

    # pylint: disable=line-too-long
    def _opensearch_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """Dummy OpenSearch data matching real production structure"""
        return {
            "documents": [
                # CMS-2025-0001 - 1 document with Federal Register text
                {
                    "docketId": "CMS-2025-0001",
                    "documentId": "CMS-2025-0001-0001",
                    "documentText": "[Federal Register Volume 90, Number 2 (Friday, January 3, 2025)] Centers for Medicare & Medicaid Services Agency Information Collection Activities: Proposed Collection. The Centers for Medicare & Medicaid Services (CMS) is announcing an opportunity for the public to comment on CMS' intention to collect information from the public. Under the Paperwork Reduction Act of 1995 (PRA), Federal agencies are required to publish notice in the Federal Register. Medicare Advantage Model of Care Submission Requirements. Request for Termination of Medicare Premium Part A, Part B, or Part B Immunosuppressive Drug Coverage (Part B-ID) and Supporting Statute and Regulations. The CMS-1763 is the form used by individuals who wish to terminate their Medicare Part A, Part B or Part B-ID. This 2024 iteration is a revision that does not propose any program changes."
                },
            ],
            "comments": [
                # DEA-2024-0059 - 1 comment about marijuana
                {
                    "commentId": "DEA-2024-0059-16885",
                    "commentText": "I am writing to express my support for the proposal to reclassify marijuana from a Schedule I to a Schedule III substance",
                    "docketId": "DEA-2024-0059"
                },
                # CMS-2025-0240 - 2 comments about Medicare/phosphate
                {
                    "commentId": "CMS-2025-0240-0014",
                    "commentText": "On behalf of kidney disease patients throughout the Midwest, I ask you to please reconsider the decision to move phosphate lowering treatments (PLT) out of Medicare Part D",
                    "docketId": "CMS-2025-0240"
                },
                {
                    "commentId": "CMS-2025-0240-0030",
                    "commentText": "What if you were told the medication your patient depends on to stay alive is now harder to get. That's the reality for thousands of kidney patients since Medicare shifted Phosphate Lowering Therapies (PLTs)",
                    "docketId": "CMS-2025-0240"
                },
                # CMS-2019-0100 - 7 comments about Home Health
                {
                    "commentId": "CMS-2019-0100-0402",
                    "commentText": "Please see the attached document. Thank you",
                    "docketId": "CMS-2019-0100"
                },
                {
                    "commentId": "CMS-2019-0100-0415",
                    "commentText": "Attached please find comments from BayCare HomeCare in Largo, Florida.",
                    "docketId": "CMS-2019-0100"
                },
                {
                    "commentId": "CMS-2019-0100-0420",
                    "commentText": "The home health agency that I work for is located in Florida and serves approximately 250 unique Medicare beneficiaries each month",
                    "docketId": "CMS-2019-0100"
                },
                {
                    "commentId": "CMS-2019-0100-0423",
                    "commentText": "Another behavioral assumption related to diagnostic coding is also very concerning to me",
                    "docketId": "CMS-2019-0100"
                },
                {
                    "commentId": "CMS-2019-0100-0438",
                    "commentText": "On behalf of the Academy of Geriatric Physical Therapy I am writing to submit comments on the Medicare Home Health Prospective Payment System",
                    "docketId": "CMS-2019-0100"
                },
                {
                    "commentId": "CMS-2019-0100-0424",
                    "commentText": "I am writing in response to the request for comments on the Centers for Medicare and Medicaid Services Home Health Prospective Payment System",
                    "docketId": "CMS-2019-0100"
                },
                {
                    "commentId": "CMS-2019-0100-0431",
                    "commentText": "Seema Verma, Administrator Centers for Medicare and Medicaid Services",
                    "docketId": "CMS-2019-0100"
                },
            ],
            "comments_extracted_text": [
                # DEA-2024-0059 - 1 extracted text about cannabis
                {
                    "attachmentId": "DEA-2024-0059-24062-1",
                    "commentId": "DEA-2024-0059-24062",
                    "docketId": "DEA-2024-0059",
                    "extractedMethod": "pdfminer",
                    "extractedText": "I am providing comments in "
                    "support of the rescheduling of botanical cannabis. The Department of Health and Human Services appropriately concluded that cannabis has a currently accepted medical use"
                },
                # CMS-2025-0240 - 4 extracted texts about Medicare/ESRD
                {
                    "attachmentId": "CMS-2025-0240-0203-1",
                    "commentId": "CMS-2025-0240-0203",
                    "docketId": "CMS-2025-0240",
                    "extractedMethod": "pypdf",
                    "extractedText": "RE: Medicare End-Stage Renal Disease Prospective Payment System for CY 2026"
                },
                {
                    "attachmentId": "CMS-2025-0240-0156-1",
                    "commentId": "CMS-2025-0240-0156",
                    "docketId": "CMS-2025-0240",
                    "extractedMethod": "pypdf",
                    "extractedText": "Dialysis Patient Citizens August 27, 2025 Medicare ESRD Prospective Payment System"
                },
                {
                    "attachmentId": "CMS-2025-0240-0168-1",
                    "commentId": "CMS-2025-0240-0168",
                    "docketId": "CMS-2025-0240",
                    "extractedMethod": "pypdf",
                    "extractedText": "RE: Medicare Program End-Stage Renal Disease Prospective Payment System"
                },
                {
                    "attachmentId": "CMS-2025-0240-0165-1",
                    "commentId": "CMS-2025-0240-0165",
                    "docketId": "CMS-2025-0240",
                    "extractedMethod": "pypdf",
                    "extractedText": "The Honorable Mehmet Oz Administrator Centers for Medicare and Medicaid Services"
                },
                # CMS-2019-0100 - 3 extracted texts about Home Health/Medicare
                {
                    "attachmentId": "CMS-2019-0100-0177-1",
                    "commentId": "CMS-2019-0100-0177",
                    "docketId": "CMS-2019-0100",
                    "extractedMethod": "pdfminer",
                    "extractedText": "RE: Medicare and Medicaid Programs CY 2020 Home Health Prospective Payment System"
                },
                {
                    "attachmentId": "CMS-2019-0100-0519-1",
                    "commentId": "CMS-2019-0100-0519",
                    "docketId": "CMS-2019-0100",
                    "extractedMethod": "pdfminer",
                    "extractedText": "Seema Verma, Administrator Centers for Medicare & Medicaid Services"
                },
                {
                    "attachmentId": "CMS-2019-0100-0205-1",
                    "commentId": "CMS-2019-0100-0205",
                    "docketId": "CMS-2019-0100",
                    "extractedMethod": "pdfminer",
                    "extractedText": "CMS-1711-P proposes several significant changes for Home Health Provider community"
                },
            ]
        }

    def text_match_terms(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,unused-argument
            self,
            terms: List[str],
            opensearch_client=None) -> List[Dict[str, Any]]:
        """
        Mock version that mirrors OpenSearch behavior:
        - documents: documentText (and aligns with documents index)
        - comments: commentText → comment_match_count
        - comments_extracted_text: extractedText → document_match_count (distinct commentId)
        """
        data = self._opensearch_items()

        def matches_phrase(text: str, term: str) -> bool:
            """Simple phrase matching - term appears in text"""
            if text is None:
                return False
            return term.lower() in text.lower()

        matching_docs = [
            doc for doc in data["documents"]
            if any(
                matches_phrase(doc.get("documentText", ""), term)
                for term in terms
            )
        ]

        comment_ids_by_docket: Dict[str, Set[str]] = {}
        for comment in data["comments"]:
            if any(matches_phrase(comment["commentText"], term) for term in terms):
                did = comment["docketId"]
                comment_ids_by_docket.setdefault(did, set()).add(comment["commentId"])

        extracted_ids_by_docket: Dict[str, Set[str]] = {}
        for extracted in data["comments_extracted_text"]:
            if any(matches_phrase(extracted["extractedText"], term) for term in terms):
                did = extracted["docketId"]
                extracted_ids_by_docket.setdefault(did, set()).add(extracted["commentId"])

        docket_counts: Dict[str, Dict[str, int]] = {}

        for doc in matching_docs:
            docket_id = doc["docketId"]
            docket_counts.setdefault(docket_id, {
                "document_match_count": 0,
                "comment_match_count": 0
            })
            docket_counts[docket_id]["document_match_count"] += 1

        for did, ids in extracted_ids_by_docket.items():
            if not ids:
                continue
            docket_counts.setdefault(did, {
                "document_match_count": 0,
                "comment_match_count": 0
            })
            docket_counts[did]["document_match_count"] += len(ids)

        for did, ids in comment_ids_by_docket.items():
            if not ids:
                continue
            docket_counts.setdefault(did, {
                "document_match_count": 0,
                "comment_match_count": 0
            })
            docket_counts[did]["comment_match_count"] = len(ids)

        return [
            {
                "docket_id": docket_id,
                "document_match_count": counts["document_match_count"],
                "comment_match_count": counts["comment_match_count"]
            }
            for docket_id, counts in docket_counts.items()
        ]

    def get_dockets_by_ids(self, docket_ids: List[str]) -> List[Dict[str, Any]]:  # pylint: disable=unused-argument
        return []

    def get_docket_ids_matching_filters( # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches,too-many-locals,unused-argument
            self,
            docket_ids: List[str],
            agency: List[str] = None,
            docket_type: str = None,
            start_date: str = None,
            end_date: str = None
    ) -> List[str]:
        """
        Mock version: filters docket IDs based on criteria.
        Uses the same dummy data from _items().
        """
        if not docket_ids:
            return []

        # Get all dockets to check filters
        all_dockets = self._get_all_dockets_dict()

        filtered = []
        for did in docket_ids:
            docket = all_dockets.get(did)
            if docket is None:
                continue

            # Check agency filter
            if agency:
                if not any((a or "").strip().lower() in (docket.get("agency_id") or "").lower()
                        for a in agency):
                    continue

            # Check docket type filter
            if docket_type:
                if docket.get("document_type", "").lower() != docket_type.lower():
                    continue

            # Date filters - mock doesn't have dates, so skip
            # In real implementation, these would be checked

            filtered.append(did)

        return filtered

    def _get_all_dockets_dict(self) -> Dict[str, Dict]:
        """Helper: return all dockets as a dict keyed by docket_id"""
        dockets = {}
        for item in self._items():
            did = item["docket_id"]
            if did not in dockets:
                dockets[did] = item
        return dockets

    def get_collections(self, user_email: str) -> List[Dict[str, Any]]:
        return [c for c in self._collections.values() if c["user_email"] == user_email]

    def create_collection(self, user_email: str, name: str) -> int:
        collection_id = self._next_collection_id
        self._next_collection_id += 1
        self._collections[collection_id] = {
            "collection_id": collection_id,
            "user_email": user_email,
            "name": name,
            "created_at": None,
            "docket_ids": []
        }
        return collection_id

    def delete_collection(self, collection_id: int, user_email: str) -> bool:
        c = self._collections.get(collection_id)
        if c is None or c["user_email"] != user_email:
            return False
        del self._collections[collection_id]
        return True

    def add_docket_to_collection(
            self, collection_id: int, docket_id: str, user_email: str) -> bool:
        c = self._collections.get(collection_id)
        if c is None or c["user_email"] != user_email:
            return False
        if docket_id not in c["docket_ids"]:
            c["docket_ids"].append(docket_id)
        return True

    def remove_docket_from_collection(
            self, collection_id: int, docket_id: str, user_email: str) -> bool:
        c = self._collections.get(collection_id)
        if c is None or c["user_email"] != user_email:
            return False
        c["docket_ids"] = [d for d in c["docket_ids"] if d != docket_id]
        return True

    def get_docket_document_comment_totals(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
            self,
            docket_ids: List[str],
            opensearch_client=None) -> Dict[str, Dict[str, int]]:
        # Denominators derived from the same dummy OpenSearch data used by
        # text_match_terms(), so numerator/denominator are consistent.
        _ = opensearch_client
        data = self._opensearch_items()

        totals: Dict[str, Dict[str, int]] = {}
        docket_ids_str = {str(d) for d in docket_ids}

        for doc in data["documents"]:
            did = str(doc["docketId"])
            if did not in docket_ids_str:
                continue
            totals.setdefault(did, {
                "document_total_count": 0,
                "comment_total_count": 0,
            })
            totals[did]["document_total_count"] += 1

        # Distinct commentId from comments index only (matches OpenSearch denominator).
        comment_ids_by_docket: Dict[str, Set[str]] = {}
        for comment in data["comments"]:
            did = str(comment["docketId"])
            if did not in docket_ids_str:
                continue
            comment_ids_by_docket.setdefault(did, set()).add(comment["commentId"])
        for did, cids in comment_ids_by_docket.items():
            totals.setdefault(did, {
                "document_total_count": 0,
                "comment_total_count": 0,
            })
            totals[did]["comment_total_count"] = len(cids)

        return totals

    def create_download_job(  # pylint: disable=too-many-arguments,too-many-positional-arguments
            self, user_email, docket_ids, data_format, include_binaries):  # pylint: disable=unused-argument
        """Mock create download job - returns a fake job id"""
        job_id = f"mock-job-{len(self._jobs) + 1}"
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "format": data_format,
            "docket_ids": docket_ids,
            "created_at": "2026-04-01T00:00:00",
            "completed_at": None,
            "up_to_date": True
        }
        return job_id

    def get_download_job(self, job_id, user_email):  # pylint: disable=unused-argument
        """Mock get download job - returns job or None"""
        return self._jobs.get(job_id)

    def get_download_s3_url(self, job_id, user_email):  # pylint: disable=unused-argument
        """Mock get download s3 url - returns None since jobs are pending in mock"""
        return None
