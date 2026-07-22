"""
test_models.py — Invariant tests for domain constants and enumerations.

Every test here verifies a specification invariant:
  - Hypothesis count constant matches SKILL.md §Output Type 1.
  - Audit checklist size constant matches SKILL.md §Output Type 2.
  - Readiness question count constant matches SKILL.md §Output Type 4.
  - AUDIT_CHECKLIST tuple length == AUDIT_CHECKLIST_SIZE.
  - READINESS_QUESTIONS tuple length == READINESS_QUESTION_COUNT.
  - ReadinessVerdict has exactly three values.
  - AuditStatus has exactly four values.
  - UNKNOWN sentinel is the exact string required by CLAUDE.md Rule 3.
"""

import pytest

from readiness_engine.models import (
    ALERT_THRESHOLD_CEILING_MULTIPLIER,
    AUDIT_CHECKLIST,
    AUDIT_CHECKLIST_SIZE,
    HARD_CAP_FLOOR_MULTIPLIER,
    HYPOTHESIS_COUNT,
    READINESS_QUESTION_COUNT,
    READINESS_QUESTIONS,
    UNKNOWN,
    AuditStatus,
    ReadinessVerdict,
    RequestType,
    RiskLevel,
)


class TestSpecificationConstants:
    """Verify that constants match SKILL.md values exactly."""

    def test_hypothesis_count_is_three(self) -> None:
        """SKILL.md §Output Type 1: exactly three hypotheses."""
        assert HYPOTHESIS_COUNT == 3

    def test_audit_checklist_size_is_twelve(self) -> None:
        """SKILL.md §Output Type 2: exactly 12 checklist items."""
        assert AUDIT_CHECKLIST_SIZE == 12

    def test_readiness_question_count_is_six(self) -> None:
        """SKILL.md §Output Type 4: exactly six readiness questions."""
        assert READINESS_QUESTION_COUNT == 6

    def test_hard_cap_floor_is_120_percent(self) -> None:
        """SKILL.md §Output Type 3 / CLAUDE.md Rule 6: hard cap >= 120% of baseline."""
        assert HARD_CAP_FLOOR_MULTIPLIER == pytest.approx(1.20)

    def test_alert_threshold_ceiling_is_75_percent(self) -> None:
        """SKILL.md §Output Type 3 / CLAUDE.md Rule 6: alert threshold <= 75% of hard cap."""
        assert ALERT_THRESHOLD_CEILING_MULTIPLIER == pytest.approx(0.75)


class TestAuditChecklist:
    """Verify the AUDIT_CHECKLIST tuple integrity."""

    def test_checklist_length_equals_constant(self) -> None:
        assert len(AUDIT_CHECKLIST) == AUDIT_CHECKLIST_SIZE

    def test_checklist_items_are_numbered_sequentially(self) -> None:
        for idx, item in enumerate(AUDIT_CHECKLIST):
            assert item.number == idx + 1, (
                f"Item at index {idx} has number {item.number}; expected {idx + 1}"
            )

    def test_checklist_item_names_are_non_empty(self) -> None:
        for item in AUDIT_CHECKLIST:
            assert item.name.strip(), f"Item {item.number} has an empty name"

    def test_checklist_criteria_are_non_empty(self) -> None:
        for item in AUDIT_CHECKLIST:
            assert item.evaluation_criteria.strip(), (
                f"Item {item.number} has empty evaluation_criteria"
            )

    def test_first_item_is_resource_limits(self) -> None:
        """Order is normative in SKILL.md §Output Type 2."""
        assert AUDIT_CHECKLIST[0].name == "Resource limits"

    def test_last_item_is_anti_affinity(self) -> None:
        assert (
            "anti-affinity" in AUDIT_CHECKLIST[-1].name.lower()
            or "topology" in AUDIT_CHECKLIST[-1].name.lower()
        )


class TestReadinessQuestions:
    """Verify the READINESS_QUESTIONS tuple integrity."""

    def test_questions_length_equals_constant(self) -> None:
        assert len(READINESS_QUESTIONS) == READINESS_QUESTION_COUNT

    def test_questions_numbered_sequentially(self) -> None:
        for idx, q in enumerate(READINESS_QUESTIONS):
            assert q.number == idx + 1

    def test_first_question_is_deployment(self) -> None:
        """SKILL.md §Output Type 4: Q1 is about deployment."""
        assert "deploy" in READINESS_QUESTIONS[0].question.lower()

    def test_last_question_is_kill_switch(self) -> None:
        """SKILL.md §Output Type 4: Q6 is about the operational kill switch."""
        assert "kill switch" in READINESS_QUESTIONS[-1].question.lower()


class TestEnumerations:
    """Verify enumeration membership matches specification."""

    def test_request_type_has_four_values(self) -> None:
        """SKILL.md §Outputs: four output types."""
        assert len(RequestType) == 4

    def test_request_type_values(self) -> None:
        assert {rt.value for rt in RequestType} == {"DIAGNOSIS", "AUDIT", "COST", "READINESS"}

    def test_readiness_verdict_has_three_values(self) -> None:
        """CLAUDE.md Rule 7: verdicts are one of three named values."""
        assert len(ReadinessVerdict) == 3

    def test_readiness_verdict_values(self) -> None:
        assert {v.value for v in ReadinessVerdict} == {
            "Ready",
            "Ready with Mitigations",
            "Not Ready",
        }

    def test_audit_status_has_four_values(self) -> None:
        """SKILL.md §Output Type 2: four audit statuses."""
        assert len(AuditStatus) == 4

    def test_audit_status_values(self) -> None:
        assert {s.value for s in AuditStatus} == {"PASS", "FAIL", "PARTIAL", "NOT APPLICABLE"}

    def test_risk_level_has_four_values(self) -> None:
        assert len(RiskLevel) == 4


class TestUnknownSentinel:
    """CLAUDE.md Rule 3: the UNKNOWN sentinel must be the exact required string."""

    def test_unknown_sentinel_value(self) -> None:
        assert UNKNOWN == "UNKNOWN — owner needed"

    def test_unknown_contains_em_dash(self) -> None:
        assert "—" in UNKNOWN, "UNKNOWN sentinel must use an em dash (—), not a hyphen"
