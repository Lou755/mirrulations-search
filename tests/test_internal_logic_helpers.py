# test_internal_logic_helpers.py
# pylint: disable=protected-access
from datetime import datetime, timezone

from mirrsearch import internal_logic as internal_logic_mod
from mirrsearch.internal_logic import (
    _modify_date_matches_filter,
    _docket_type_matches_filter,
    _agency_matches_filter,
    _parallel_search_phase1_enabled,
    _json_safe_scalar,
    _cfr_part_patterns_match_row,
    _ref_has_exact_part,
)

# --- _modify_date_matches_filter tests ---
def test_modify_date_none_returns_true():
    row = {}
    assert _modify_date_matches_filter(row) is True

def test_modify_date_within_range():
    row = {"modify_date": "2024-06-01T12:00:00"}
    start = "2024-01-01T00:00:00"
    end = "2024-12-31T23:59:59"
    assert _modify_date_matches_filter(row, start, end) is True

def test_modify_date_before_start():
    row = {"modify_date": "2023-12-31T23:59:59"}
    start = "2024-01-01T00:00:00"
    assert _modify_date_matches_filter(row, start_date=start) is False

def test_modify_date_after_end():
    row = {"modify_date": "2025-01-01T00:00:00"}
    end = "2024-12-31T23:59:59"
    assert _modify_date_matches_filter(row, end_date=end) is False

# --- _docket_type_matches_filter tests ---
def test_docket_type_none_or_matches():
    row = {"docket_type": "Proposed Rule"}
    assert _docket_type_matches_filter(row, None) is True
    assert _docket_type_matches_filter(row, "Proposed Rule") is True
    assert _docket_type_matches_filter(row, "Final Rule") is False

# --- _agency_matches_filter tests ---
def test_agency_none_or_matches():
    row = {"agency_id": "CMS"}
    assert _agency_matches_filter(row, None) is True
    assert _agency_matches_filter(row, []) is True
    assert _agency_matches_filter(row, ["CMS"]) is True
    assert _agency_matches_filter(row, ["cms"]) is True
    assert _agency_matches_filter(row, ["EPA"]) is False
    assert _agency_matches_filter(row, ["CMS", "EPA"]) is True


def test_parallel_phase1_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MIRRSEARCH_PHASE1_PARALLEL", raising=False)
    assert _parallel_search_phase1_enabled() is False


def test_parallel_phase1_enabled_explicit(monkeypatch):
    monkeypatch.setenv("MIRRSEARCH_PHASE1_PARALLEL", "1")
    assert _parallel_search_phase1_enabled() is True


def test_parallel_phase1_disabled_explicit_zero(monkeypatch):
    monkeypatch.setenv("MIRRSEARCH_PHASE1_PARALLEL", "0")
    assert _parallel_search_phase1_enabled() is False


def test_modify_date_tz_aware_normalized_to_utc_naive():
    row = {"modify_date": datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)}
    start = "2024-06-01T00:00:00"
    end = "2024-06-30T23:59:59"
    assert _modify_date_matches_filter(row, start, end) is True


def test_json_safe_scalar_non_datetime_unchanged():
    assert _json_safe_scalar("plain") == "plain"
    assert _json_safe_scalar(42) == 42


def test_cfr_part_patterns_empty_returns_true():
    row = {"cfr_refs": []}
    assert _cfr_part_patterns_match_row(row, []) is True


def test_cfr_part_patterns_no_match_returns_false():
    row = {"cfr_refs": [{"cfrParts": {"999": "u"}}]}
    assert _cfr_part_patterns_match_row(row, ["413"]) is False


def test_ref_has_exact_part_title_mismatch():
    ref = {"title": "40", "cfrParts": {"413": "u"}}
    assert _ref_has_exact_part(ref, "42", "413") is False


def test_ref_has_exact_part_matching_title_and_part():
    ref = {"title": "42", "cfrParts": {"413": "u"}}
    assert _ref_has_exact_part(ref, "42", "413") is True


def test_phase1_executor_shutdown_resets_singleton():
    internal_logic_mod._shutdown_phase1_executor()
    first = internal_logic_mod._get_phase1_executor()
    assert internal_logic_mod._get_phase1_executor() is first
    internal_logic_mod._shutdown_phase1_executor()
    second = internal_logic_mod._get_phase1_executor()
    assert second is not first
    internal_logic_mod._shutdown_phase1_executor()
