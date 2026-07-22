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
  - RiskLevel ordering satisfies LOW < MEDIUM < HIGH < CRITICAL.
  - Finding dataclass is immutable and carries required fields.
  - Recommendation dataclass is immutable and carries required fields.
  - ReadinessReport dataclass is immutable and enforces verdict typing.
"""

import dataclasses

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
    Finding,
    ReadinessReport,
    ReadinessVerdict,
    Recommendation,
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


# ---------------------------------------------------------------------------
# Sprint 1 tests — RiskLevel ordering, Finding, Recommendation, ReadinessReport
# ---------------------------------------------------------------------------


class TestRiskLevelOrdering:
    """
    Verify that RiskLevel comparison operators express severity ordering.

    Traceable to: specs/operational-drift-analysis/spec.md §1.2 Step 6
    "Severity ordering: LOW < MEDIUM < HIGH < CRITICAL."
    and changes/operational-drift-risk-model/delta.md §M-1.
    """

    def test_low_less_than_medium(self) -> None:
        """LOW < MEDIUM (spec §1.2 severity ordering)."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM

    def test_medium_less_than_high(self) -> None:
        """MEDIUM < HIGH (spec §1.2 severity ordering)."""
        assert RiskLevel.MEDIUM < RiskLevel.HIGH

    def test_high_less_than_critical(self) -> None:
        """HIGH < CRITICAL (spec §1.2 severity ordering; delta.md §M-1)."""
        assert RiskLevel.HIGH < RiskLevel.CRITICAL

    def test_full_ascending_chain(self) -> None:
        """LOW < MEDIUM < HIGH < CRITICAL as a single comparison chain."""
        assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH < RiskLevel.CRITICAL

    def test_critical_is_maximum(self) -> None:
        """CRITICAL must be strictly greater than every other level."""
        for level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
            assert RiskLevel.CRITICAL > level, f"CRITICAL must be > {level.name}"

    def test_low_is_minimum(self) -> None:
        """LOW must be strictly less than every other level."""
        for level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
            assert RiskLevel.LOW < level, f"LOW must be < {level.name}"

    def test_risk_level_str_returns_name(self) -> None:
        """str(RiskLevel.X) must return the label, not an integer."""
        assert str(RiskLevel.LOW) == "LOW"
        assert str(RiskLevel.MEDIUM) == "MEDIUM"
        assert str(RiskLevel.HIGH) == "HIGH"
        assert str(RiskLevel.CRITICAL) == "CRITICAL"

    def test_risk_level_integer_values_are_ordered(self) -> None:
        """Integer values must be strictly ascending in specification order."""
        levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        values = [level.value for level in levels]
        assert values == sorted(values), "Integer values must be strictly ascending"

    def test_risk_level_names(self) -> None:
        """All four required level names are present."""
        names = {level.name for level in RiskLevel}
        assert names == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class TestFinding:
    """
    Verify the Finding dataclass.

    Traceable to: specs/operational-drift-analysis/spec.md §1.2 Steps 2-4
    and §1.4 (evidence citation requirement).
    """

    def _make_finding(self, **overrides: object) -> Finding:
        """Factory helper — construct a minimal valid Finding."""
        defaults: dict[str, object] = {
            "component_type": "Deployment",
            "component_name": "cart-api",
            "category": "modified",
            "risk_level": RiskLevel.MEDIUM,
            "artefact_reference": "artefacts/800-wide/02-deploy-manifest.md",
        }
        defaults.update(overrides)
        return Finding(**defaults)  # type: ignore[arg-type]

    def test_finding_creation_with_required_fields(self) -> None:
        """Finding can be constructed with all required fields."""
        f = self._make_finding()
        assert f.component_type == "Deployment"
        assert f.component_name == "cart-api"
        assert f.category == "modified"
        assert f.risk_level == RiskLevel.MEDIUM
        assert f.artefact_reference == "artefacts/800-wide/02-deploy-manifest.md"

    def test_finding_default_owner_is_unknown(self) -> None:
        """owner defaults to UNKNOWN sentinel (spec §1.2 Steps 2-4; CLAUDE.md Rule 3)."""
        f = self._make_finding()
        assert f.owner == UNKNOWN

    def test_finding_default_state_values_are_empty_strings(self) -> None:
        """state_a_value and state_b_value default to empty string."""
        f = self._make_finding()
        assert f.state_a_value == ""
        assert f.state_b_value == ""

    def test_finding_with_explicit_owner(self) -> None:
        """owner can be set to a specific ownership label."""
        f = self._make_finding(owner="[ops]")
        assert f.owner == "[ops]"

    def test_finding_with_state_values(self) -> None:
        """State A and B values are stored correctly."""
        f = self._make_finding(
            state_a_value="sha256:abc123",
            state_b_value="latest",
        )
        assert f.state_a_value == "sha256:abc123"
        assert f.state_b_value == "latest"

    def test_finding_is_immutable(self) -> None:
        """Finding is frozen=True; mutation raises FrozenInstanceError."""
        f = self._make_finding()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            f.component_name = "other"  # type: ignore[misc]

    def test_finding_is_a_dataclass(self) -> None:
        """Finding is a dataclass (structural contract)."""
        assert dataclasses.is_dataclass(Finding)

    def test_finding_equality(self) -> None:
        """Two findings with identical fields compare as equal."""
        f1 = self._make_finding()
        f2 = self._make_finding()
        assert f1 == f2

    def test_finding_inequality_on_risk_level(self) -> None:
        """Findings with different risk levels are not equal."""
        f1 = self._make_finding(risk_level=RiskLevel.LOW)
        f2 = self._make_finding(risk_level=RiskLevel.HIGH)
        assert f1 != f2

    def test_finding_category_added(self) -> None:
        """category 'added' is accepted."""
        f = self._make_finding(category="added", state_a_value="")
        assert f.category == "added"

    def test_finding_category_removed(self) -> None:
        """category 'removed' is accepted."""
        f = self._make_finding(category="removed", state_b_value="")
        assert f.category == "removed"

    def test_finding_risk_level_type(self) -> None:
        """risk_level field accepts RiskLevel enum values."""
        for level in RiskLevel:
            f = self._make_finding(risk_level=level)
            assert f.risk_level is level


class TestRecommendation:
    """
    Verify the Recommendation dataclass.

    Traceable to: specs/operational-drift-analysis/spec.md §1.2 Step 7
    and SKILL.md §Escalation Policy / CLAUDE.md §Escalation Format.
    """

    def _make_recommendation(self, **overrides: object) -> Recommendation:
        """Factory helper — construct a minimal valid Recommendation."""
        defaults: dict[str, object] = {
            "action": "Review and reinstate PodDisruptionBudget",
            "role": "Platform Engineer",
            "condition": "PDB absent from State B",
            "artefact": "artefacts/800-wide/02-deploy-manifest.md",
        }
        defaults.update(overrides)
        return Recommendation(**defaults)  # type: ignore[arg-type]

    def test_recommendation_creation_with_required_fields(self) -> None:
        """Recommendation can be constructed with all required fields."""
        r = self._make_recommendation()
        assert r.action == "Review and reinstate PodDisruptionBudget"
        assert r.role == "Platform Engineer"
        assert r.condition == "PDB absent from State B"
        assert r.artefact == "artefacts/800-wide/02-deploy-manifest.md"

    def test_recommendation_default_risk_level_is_medium(self) -> None:
        """risk_level defaults to MEDIUM when not provided."""
        r = self._make_recommendation()
        assert r.risk_level == RiskLevel.MEDIUM

    def test_recommendation_explicit_risk_level(self) -> None:
        """risk_level can be set to any RiskLevel value."""
        r = self._make_recommendation(risk_level=RiskLevel.CRITICAL)
        assert r.risk_level == RiskLevel.CRITICAL

    def test_recommendation_is_immutable(self) -> None:
        """Recommendation is frozen=True; mutation raises FrozenInstanceError."""
        r = self._make_recommendation()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            r.action = "different action"  # type: ignore[misc]

    def test_recommendation_is_a_dataclass(self) -> None:
        """Recommendation is a dataclass (structural contract)."""
        assert dataclasses.is_dataclass(Recommendation)

    def test_recommendation_equality(self) -> None:
        """Two recommendations with identical fields compare as equal."""
        r1 = self._make_recommendation()
        r2 = self._make_recommendation()
        assert r1 == r2

    def test_recommendation_inequality_on_role(self) -> None:
        """Recommendations with different roles are not equal."""
        r1 = self._make_recommendation(role="Platform Engineer")
        r2 = self._make_recommendation(role="Security Engineer")
        assert r1 != r2

    def test_recommendation_required_escalation_fields_present(self) -> None:
        """All four escalation block fields (action/role/condition/artefact) are present."""
        r = self._make_recommendation()
        fields = {f.name for f in dataclasses.fields(r)}
        assert {"action", "role", "condition", "artefact"}.issubset(fields)

    def test_recommendation_all_risk_levels_accepted(self) -> None:
        """Recommendation accepts all four RiskLevel values."""
        for level in RiskLevel:
            r = self._make_recommendation(risk_level=level)
            assert r.risk_level is level


class TestReadinessReportModel:
    """
    Verify the ReadinessReport domain model (immutable summary in models.py).

    Traceable to: SKILL.md §Output Type 4; REFERENCE.md §Readiness Reviews;
    changes/operational-drift-risk-model/delta.md §A-3 (critical_drift_active).
    """

    def test_readiness_report_creation_with_verdict_only(self) -> None:
        """ReadinessReport can be constructed with just a verdict."""
        report = ReadinessReport(verdict=ReadinessVerdict.READY)
        assert report.verdict == ReadinessVerdict.READY

    def test_readiness_report_default_gaps_is_empty_tuple(self) -> None:
        """maturity_gaps defaults to an empty tuple."""
        report = ReadinessReport(verdict=ReadinessVerdict.READY)
        assert report.maturity_gaps == ()

    def test_readiness_report_default_artefact_reference_is_unknown(self) -> None:
        """artefact_reference defaults to the UNKNOWN sentinel."""
        report = ReadinessReport(verdict=ReadinessVerdict.READY)
        assert report.artefact_reference == UNKNOWN

    def test_readiness_report_default_critical_drift_is_false(self) -> None:
        """critical_drift_active defaults to False."""
        report = ReadinessReport(verdict=ReadinessVerdict.READY)
        assert report.critical_drift_active is False

    def test_readiness_report_with_maturity_gaps(self) -> None:
        """maturity_gaps stores gap descriptions."""
        gaps = ("No PodDisruptionBudget defined — owner: [ops]",)
        report = ReadinessReport(
            verdict=ReadinessVerdict.READY_WITH_MITIGATIONS,
            maturity_gaps=gaps,
        )
        assert report.maturity_gaps == gaps

    def test_readiness_report_with_critical_drift_active(self) -> None:
        """critical_drift_active=True reflects CRITICAL drift propagation (delta.md §A-3)."""
        report = ReadinessReport(
            verdict=ReadinessVerdict.NOT_READY,
            critical_drift_active=True,
        )
        assert report.critical_drift_active is True

    def test_readiness_report_is_immutable(self) -> None:
        """ReadinessReport is frozen=True; mutation raises FrozenInstanceError."""
        report = ReadinessReport(verdict=ReadinessVerdict.READY)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            report.verdict = ReadinessVerdict.NOT_READY  # type: ignore[misc]

    def test_readiness_report_is_a_dataclass(self) -> None:
        """ReadinessReport is a dataclass (structural contract)."""
        assert dataclasses.is_dataclass(ReadinessReport)

    def test_readiness_report_accepts_all_three_verdicts(self) -> None:
        """ReadinessReport accepts each of the three permitted verdicts."""
        for verdict in ReadinessVerdict:
            report = ReadinessReport(verdict=verdict)
            assert report.verdict == verdict

    def test_readiness_report_equality(self) -> None:
        """Two reports with identical fields compare as equal."""
        r1 = ReadinessReport(verdict=ReadinessVerdict.READY)
        r2 = ReadinessReport(verdict=ReadinessVerdict.READY)
        assert r1 == r2

    def test_readiness_report_inequality_on_verdict(self) -> None:
        """Reports with different verdicts are not equal."""
        r1 = ReadinessReport(verdict=ReadinessVerdict.READY)
        r2 = ReadinessReport(verdict=ReadinessVerdict.NOT_READY)
        assert r1 != r2

    def test_readiness_report_maturity_gaps_is_tuple(self) -> None:
        """maturity_gaps must be a tuple (immutable sequence)."""
        gaps = ("gap one", "gap two")
        report = ReadinessReport(verdict=ReadinessVerdict.READY, maturity_gaps=gaps)
        assert isinstance(report.maturity_gaps, tuple)

    def test_readiness_report_with_artefact_reference(self) -> None:
        """artefact_reference stores the evidence source string."""
        report = ReadinessReport(
            verdict=ReadinessVerdict.READY,
            artefact_reference="artefacts/800-wide/01-06",
        )
        assert report.artefact_reference == "artefacts/800-wide/01-06"
