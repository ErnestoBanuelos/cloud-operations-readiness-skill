"""
test_validator.py — Structural validation rule tests.

Tests verify that validator.py correctly enforces the invariants from SKILL.md.
All test data is synthetic.

Test structure
--------------
- Each validator function has a dedicated test class.
- Each test class contains:
    - A valid fixture that should pass.
    - One or more invalid fixtures, each triggering a specific violation.
"""

import pytest

from readiness_engine.models import (
    AUDIT_CHECKLIST_SIZE,
    READINESS_QUESTION_COUNT,
    UNKNOWN,
    AuditStatus,
    ReadinessVerdict,
)
from readiness_engine.validator import (
    ValidationResult,
    validate_audit_checklist_completeness,
    validate_audit_item_status,
    validate_audit_report,
    validate_cost_cap,
    validate_cost_line_items,
    validate_cost_report,
    validate_diagnosis_report,
    validate_hypothesis_count,
    validate_hypothesis_structure,
    validate_readiness_question_count,
    validate_readiness_report,
    validate_readiness_verdict,
    validate_unknown_not_fabricated,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hypothesis(rank: int = 1, confidence_pct: int = 80) -> dict:
    return {
        "rank": rank,
        "confidence_pct": confidence_pct,
        "evidence_for": ["pod restarted 5 times"],
        "evidence_against": ["no memory pressure on node"],
        "verification_command": "kubectl top pods -n checkout",
    }


def _make_audit_item(number: int, status: str = AuditStatus.PASS.value) -> dict:
    return {
        "number": number,
        "name": f"Checklist item {number}",
        "status": status,
    }


def _make_valid_checklist() -> list[dict]:
    return [_make_audit_item(i) for i in range(1, AUDIT_CHECKLIST_SIZE + 1)]


def _make_cost_report(
    cloud_rent: float = 1500.0,
    ai_meter: float = 15000.0,
    monthly_total: float = 16500.0,
    hard_cap: float = 18000.0,
    alert_threshold: float = 13500.0,
) -> dict:
    return {
        "cloud_rent": cloud_rent,
        "ai_meter": ai_meter,
        "monthly_total": monthly_total,
        "hard_cap": hard_cap,
        "alert_threshold": alert_threshold,
    }


def _make_readiness_answer(number: int, status: str = "ANSWERED") -> dict:
    return {
        "number": number,
        "question": f"Question {number}",
        "answer": f"Answer to question {number}",
        "status": status,
    }


def _make_valid_readiness_answers() -> list[dict]:
    return [_make_readiness_answer(i) for i in range(1, READINESS_QUESTION_COUNT + 1)]


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_default_passes(self) -> None:
        result = ValidationResult()
        assert result.passed is True
        assert result.violations == []
        assert bool(result) is True

    def test_fail_records_violation(self) -> None:
        result = ValidationResult()
        result.fail("something went wrong")
        assert result.passed is False
        assert "something went wrong" in result.violations

    def test_merge_propagates_failure(self) -> None:
        r1 = ValidationResult()
        r2 = ValidationResult()
        r2.fail("child failure")
        r1.merge(r2)
        assert r1.passed is False
        assert "child failure" in r1.violations

    def test_merge_passing_does_not_fail_parent(self) -> None:
        r1 = ValidationResult()
        r2 = ValidationResult()
        r1.merge(r2)
        assert r1.passed is True


# ---------------------------------------------------------------------------
# Hypothesis validators
# ---------------------------------------------------------------------------


class TestValidateHypothesisCount:
    def test_exactly_three_passes(self) -> None:
        result = validate_hypothesis_count([1, 2, 3])
        assert result.passed

    def test_two_fails(self) -> None:
        result = validate_hypothesis_count([1, 2])
        assert not result.passed
        assert any("3" in v for v in result.violations)

    def test_four_fails(self) -> None:
        result = validate_hypothesis_count([1, 2, 3, 4])
        assert not result.passed

    def test_zero_fails(self) -> None:
        result = validate_hypothesis_count([])
        assert not result.passed


class TestValidateHypothesisStructure:
    def test_complete_hypothesis_passes(self) -> None:
        result = validate_hypothesis_structure(_make_hypothesis())
        assert result.passed

    def test_missing_confidence_pct_fails(self) -> None:
        h = _make_hypothesis()
        del h["confidence_pct"]
        result = validate_hypothesis_structure(h)
        assert not result.passed
        assert any("confidence_pct" in v for v in result.violations)

    def test_confidence_above_100_fails(self) -> None:
        h = _make_hypothesis(confidence_pct=101)
        result = validate_hypothesis_structure(h)
        assert not result.passed

    def test_confidence_below_0_fails(self) -> None:
        h = _make_hypothesis(confidence_pct=-1)
        result = validate_hypothesis_structure(h)
        assert not result.passed

    def test_confidence_at_boundary_0_passes(self) -> None:
        result = validate_hypothesis_structure(_make_hypothesis(confidence_pct=0))
        assert result.passed

    def test_confidence_at_boundary_100_passes(self) -> None:
        result = validate_hypothesis_structure(_make_hypothesis(confidence_pct=100))
        assert result.passed

    def test_missing_verification_command_fails(self) -> None:
        h = _make_hypothesis()
        del h["verification_command"]
        result = validate_hypothesis_structure(h)
        assert not result.passed


# ---------------------------------------------------------------------------
# Audit validators
# ---------------------------------------------------------------------------


class TestValidateAuditChecklistCompleteness:
    def test_twelve_items_passes(self) -> None:
        result = validate_audit_checklist_completeness(_make_valid_checklist())
        assert result.passed

    def test_eleven_items_fails(self) -> None:
        result = validate_audit_checklist_completeness(_make_valid_checklist()[:-1])
        assert not result.passed

    def test_thirteen_items_fails(self) -> None:
        items = [*_make_valid_checklist(), _make_audit_item(13)]
        result = validate_audit_checklist_completeness(items)
        assert not result.passed

    def test_out_of_order_fails(self) -> None:
        items = _make_valid_checklist()
        # Swap items 1 and 2
        items[0], items[1] = items[1], items[0]
        result = validate_audit_checklist_completeness(items)
        assert not result.passed


class TestValidateAuditItemStatus:
    @pytest.mark.parametrize("status", [s.value for s in AuditStatus])
    def test_valid_statuses_pass(self, status: str) -> None:
        item = _make_audit_item(1, status=status)
        result = validate_audit_item_status(item)
        assert result.passed

    def test_invalid_status_fails(self) -> None:
        item = _make_audit_item(1, status="MOSTLY PASS")
        result = validate_audit_item_status(item)
        assert not result.passed

    def test_empty_status_fails(self) -> None:
        item = _make_audit_item(1, status="")
        result = validate_audit_item_status(item)
        assert not result.passed

    def test_gradational_language_fails(self) -> None:
        for bad in ("mostly pass", "nearly fail", "almostok"):
            item = _make_audit_item(1, status=bad)
            assert not validate_audit_item_status(item).passed, (
                f"Expected '{bad}' to fail status validation"
            )


# ---------------------------------------------------------------------------
# Cost validators
# ---------------------------------------------------------------------------


class TestValidateCostLineItems:
    def test_both_present_passes(self) -> None:
        result = validate_cost_line_items(_make_cost_report())
        assert result.passed

    def test_missing_cloud_rent_fails(self) -> None:
        report = _make_cost_report()
        del report["cloud_rent"]
        result = validate_cost_line_items(report)
        assert not result.passed

    def test_missing_ai_meter_fails(self) -> None:
        report = _make_cost_report()
        del report["ai_meter"]
        result = validate_cost_line_items(report)
        assert not result.passed


class TestValidateCostCap:
    def test_valid_cap_passes(self) -> None:
        # hard_cap=18000 is 18000/16500 = 109% — wait, spec says >= 120%
        # Reference figures: baseline=16500, hard_cap=18000 → 18000/16500 = 1.09 < 1.20
        # The reference figures in CLAUDE.md show $18,000 as 120% of $15,000 (AI meter baseline),
        # but in the cost report the monthly_total is $16,500 (cloud rent + AI meter).
        # 18000 / 16500 = 1.09 which is < 1.20.
        # Per SKILL.md, hard cap >= 120% of "current baseline spend" (the monthly total).
        # So a valid cap for $16,500 baseline is >= $19,800.
        result = validate_cost_cap(
            _make_cost_report(
                monthly_total=16500.0,
                hard_cap=19800.0,
                alert_threshold=14850.0,  # 75% of 19800 = 14850
            )
        )
        assert result.passed

    def test_hard_cap_below_120_percent_fails(self) -> None:
        result = validate_cost_cap(
            _make_cost_report(
                monthly_total=16500.0,
                hard_cap=18000.0,  # only 109%
                alert_threshold=13500.0,
            )
        )
        assert not result.passed

    def test_alert_threshold_above_75_percent_of_cap_fails(self) -> None:
        result = validate_cost_cap(
            _make_cost_report(
                monthly_total=16500.0,
                hard_cap=19800.0,
                alert_threshold=16000.0,  # 16000/19800 = 80.8% > 75%
            )
        )
        assert not result.passed

    def test_missing_monthly_total_fails(self) -> None:
        report = _make_cost_report()
        del report["monthly_total"]
        result = validate_cost_cap(report)
        assert not result.passed

    def test_missing_hard_cap_fails(self) -> None:
        report = _make_cost_report(monthly_total=16500.0, hard_cap=19800.0, alert_threshold=14850.0)
        del report["hard_cap"]
        result = validate_cost_cap(report)
        assert not result.passed

    def test_alert_threshold_at_exactly_75_percent_passes(self) -> None:
        hard_cap = 19800.0
        alert_threshold = hard_cap * 0.75  # exactly 75%
        result = validate_cost_cap(
            _make_cost_report(
                monthly_total=16500.0,
                hard_cap=hard_cap,
                alert_threshold=alert_threshold,
            )
        )
        assert result.passed


# ---------------------------------------------------------------------------
# Readiness validators
# ---------------------------------------------------------------------------


class TestValidateReadinessQuestionCount:
    def test_six_answers_passes(self) -> None:
        result = validate_readiness_question_count(_make_valid_readiness_answers())
        assert result.passed

    def test_five_answers_fails(self) -> None:
        result = validate_readiness_question_count(_make_valid_readiness_answers()[:-1])
        assert not result.passed

    def test_seven_answers_fails(self) -> None:
        answers = [*_make_valid_readiness_answers(), _make_readiness_answer(7)]
        result = validate_readiness_question_count(answers)
        assert not result.passed


class TestValidateReadinessVerdict:
    @pytest.mark.parametrize("verdict", [v.value for v in ReadinessVerdict])
    def test_valid_verdicts_pass(self, verdict: str) -> None:
        assert validate_readiness_verdict(verdict).passed

    def test_gradational_language_fails(self) -> None:
        for bad in ("mostly ready", "nearly there", "almost ready", "ready-ish"):
            result = validate_readiness_verdict(bad)
            assert not result.passed, f"Expected '{bad}' to fail verdict validation"

    def test_none_fails(self) -> None:
        result = validate_readiness_verdict(None)
        assert not result.passed

    def test_empty_string_fails(self) -> None:
        result = validate_readiness_verdict("")
        assert not result.passed


class TestValidateUnknownNotFabricated:
    def test_valid_unknown_sentinel_passes(self) -> None:
        answers = [{"status": "UNKNOWN", "answer": UNKNOWN}]
        result = validate_unknown_not_fabricated(answers)
        assert result.passed

    def test_fabricated_answer_with_unknown_status_fails(self) -> None:
        answers = [{"status": "UNKNOWN", "answer": "The on-call engineer is Alice"}]
        result = validate_unknown_not_fabricated(answers)
        assert not result.passed

    def test_answered_status_with_real_answer_passes(self) -> None:
        answers = [{"status": "ANSWERED", "answer": "Deployed via GitHub Actions on merge to main"}]
        result = validate_unknown_not_fabricated(answers)
        assert result.passed


# ---------------------------------------------------------------------------
# Aggregate validators
# ---------------------------------------------------------------------------


class TestValidateDiagnosisReport:
    def test_valid_report_passes(self) -> None:
        report = {"hypotheses": [_make_hypothesis(rank=i) for i in range(1, 4)]}
        assert validate_diagnosis_report(report).passed

    def test_empty_hypotheses_fails(self) -> None:
        assert not validate_diagnosis_report({"hypotheses": []}).passed

    def test_missing_hypotheses_key_fails(self) -> None:
        assert not validate_diagnosis_report({}).passed


class TestValidateAuditReport:
    def test_valid_report_passes(self) -> None:
        report = {"checklist": _make_valid_checklist()}
        assert validate_audit_report(report).passed

    def test_incomplete_checklist_fails(self) -> None:
        report = {"checklist": _make_valid_checklist()[:6]}
        assert not validate_audit_report(report).passed


class TestValidateCostReport:
    def test_valid_report_passes(self) -> None:
        report = _make_cost_report(
            monthly_total=16500.0,
            hard_cap=19800.0,
            alert_threshold=14850.0,
        )
        assert validate_cost_report(report).passed

    def test_report_missing_cloud_rent_fails(self) -> None:
        report = _make_cost_report(monthly_total=16500.0, hard_cap=19800.0, alert_threshold=14850.0)
        del report["cloud_rent"]
        assert not validate_cost_report(report).passed


class TestValidateReadinessReport:
    def test_valid_report_passes(self) -> None:
        report = {
            "answers": _make_valid_readiness_answers(),
            "verdict": ReadinessVerdict.READY.value,
        }
        assert validate_readiness_report(report).passed

    def test_invalid_verdict_fails(self) -> None:
        report = {
            "answers": _make_valid_readiness_answers(),
            "verdict": "mostly ready",
        }
        assert not validate_readiness_report(report).passed

    def test_wrong_answer_count_fails(self) -> None:
        report = {
            "answers": _make_valid_readiness_answers()[:3],
            "verdict": ReadinessVerdict.NOT_READY.value,
        }
        assert not validate_readiness_report(report).passed
