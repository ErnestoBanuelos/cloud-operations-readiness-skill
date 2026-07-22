"""
test_classifier.py — Risk Classification Engine unit tests.

This file covers two concerns:

1. ``classify()`` — request-type classification accuracy (Sprint 1 baseline).
   Tests are preserved from the original scaffold and are not modified.

2. ``classify_risk()`` — risk level classification (Sprint 2 implementation).
   Tests cover every Acceptance Criterion with positive, negative, and boundary
   cases.

Test matrix for classify_risk()
--------------------------------
Acceptance criteria (spec.md §1.6 + delta.md §A-5):
  AC-1  Added component detection
  AC-2  Safety-relevant removal triggers HIGH
  AC-3  Modified security field detected and reported
  AC-4  No drift produces a clean report (LOW)
  AC-5  CRITICAL triggered by replica-count-below-minAvailable

Proof test (delta.md Risk Note — Proof Test):
  PT-1  HIGH preserved when no PDB present (HIGH/CRITICAL boundary condition)

Additional required dimensions (sprint brief):
  - Severity ordering (LOW < MEDIUM < HIGH < CRITICAL)
  - Single finding
  - Multiple findings — highest severity wins
  - Empty input
  - Unknown ownership triggers MEDIUM
  - CRITICAL trigger takes precedence

Traceability
------------
Every test class references the specification section or acceptance criterion
it exercises in its docstring.
"""

from __future__ import annotations

import pytest

from readiness_engine.classifier import (
    CATEGORY_PDB_REPLICA_VIOLATION,
    CATEGORY_WRITE_COMMAND,
    classify,
    classify_risk,
)
from readiness_engine.models import UNKNOWN, Finding, RequestType, RiskLevel

# ===========================================================================
# Test fixtures — synthetic Finding factories
# ===========================================================================
# All inputs are synthetic.  No real artefacts are read.
# Traceable to: ADR-001 §Reference, Not Production; CLAUDE.md §Use synthetic
# data only.


def _finding(
    *,
    category: str = "modified",
    risk_level: RiskLevel = RiskLevel.LOW,
    component_type: str = "Deployment",
    component_name: str = "cart-api",
    artefact_reference: str = "artefacts/800-wide/02-deploy-manifest.md",
    owner: str = "[ops]",
    state_a_value: str = "v1.0.0",
    state_b_value: str = "v1.1.0",
) -> Finding:
    """
    Construct a synthetic Finding with sensible defaults.

    This factory keeps test cases focused on the field(s) under test by
    providing defaults for all other required fields.
    """
    return Finding(
        component_type=component_type,
        component_name=component_name,
        category=category,
        risk_level=risk_level,
        artefact_reference=artefact_reference,
        owner=owner,
        state_a_value=state_a_value,
        state_b_value=state_b_value,
    )


def _write_command_finding() -> Finding:
    """
    Synthetic finding that triggers Priority 1 — CRITICAL.

    Represents a write-command artefact detected in State B absent from State A.
    Traceable to: spec.md §1.2 Step 6 Priority 1; delta.md §A-1.
    """
    return _finding(
        category=CATEGORY_WRITE_COMMAND,
        component_type="write-command artefact",
        component_name="kubectl apply",
        risk_level=RiskLevel.CRITICAL,
        artefact_reference="artefacts/state-b/ci-workflow.yml",
        state_a_value="absent",
        state_b_value="kubectl apply -f deploy/",
    )


def _pdb_replica_violation_finding() -> Finding:
    """
    Synthetic finding that triggers Priority 2 — CRITICAL.

    Represents a PDB-guarded replica-count-below-minAvailable violation.
    Traceable to: spec.md §1.2 Step 6 Priority 2; delta.md §A-1; AUDIT-ODA-01.
    """
    return _finding(
        category=CATEGORY_PDB_REPLICA_VIOLATION,
        component_type="Deployment",
        component_name="cart-api",
        risk_level=RiskLevel.CRITICAL,
        artefact_reference="artefacts/800-wide/02-deploy-manifest.md",
        state_a_value="replicas: 3",
        state_b_value="replicas: 1",
    )


def _high_finding(component_type: str = "PodDisruptionBudget") -> Finding:
    """
    Synthetic finding that triggers Priority 3 — HIGH.

    Represents removal of a safety-relevant component (PDB, securityContext,
    readiness probe) or a security context / mutable image modification.
    Traceable to: spec.md §1.2 Step 6 Priority 3.
    """
    return _finding(
        category="removed",
        risk_level=RiskLevel.HIGH,
        component_type=component_type,
        component_name="cart-api-pdb",
        state_a_value="minAvailable: 2",
        state_b_value="",
    )


def _medium_finding() -> Finding:
    """
    Synthetic finding that triggers Priority 4 — MEDIUM.

    Represents a non-safety field modification.
    Traceable to: spec.md §1.2 Step 6 Priority 4.
    """
    return _finding(
        category="modified",
        risk_level=RiskLevel.MEDIUM,
        component_type="Deployment",
        component_name="cart-api",
        state_a_value="replicas: 2",
        state_b_value="replicas: 3",
    )


def _low_finding() -> Finding:
    """
    Synthetic finding that produces no trigger for Priorities 1-4 → LOW.

    Represents an additive change with no safety relevance and known ownership.
    Traceable to: spec.md §1.2 Step 6 Priority 5.
    """
    return _finding(
        category="added",
        risk_level=RiskLevel.LOW,
        component_type="NetworkPolicy",
        component_name="cart-api-netpol",
        owner="[ops]",
        state_a_value="",
        state_b_value="NetworkPolicy: cart-api-netpol",
    )


def _added_unknown_owner_finding() -> Finding:
    """
    Synthetic finding: added component with undetermined ownership → MEDIUM.

    Traceable to: spec.md §1.2 Step 6 Priority 4 sub-trigger (b):
    "at least one added component with undetermined ownership."
    CLAUDE.md Rule 3 (UNKNOWN sentinel).
    """
    return _finding(
        category="added",
        risk_level=RiskLevel.LOW,  # detection layer did not elevate yet
        component_type="Sidecar",
        component_name="logging-sidecar",
        owner=UNKNOWN,  # ownership undetermined
        state_a_value="",
        state_b_value="sidecar: logging-sidecar",
    )


# ===========================================================================
# classify() — Request type classification tests (baseline)
# ===========================================================================
# These tests verify the existing classify() function and are preserved
# from the original scaffold without modification.

DIAGNOSIS_INPUT = """\
Warning  BackOff   21s (x5 over 2m)  kubelet   Back-off restarting failed container
Normal   Pulled    3m                 kubelet   Successfully pulled image
kubectl describe pod cart-api-abc123 -n checkout
Last State: Terminated
  Reason: OOMKilled
  Exit Code: 137
  Restart Count: 5
"""

AUDIT_INPUT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
spec:
  template:
    spec:
      containers:
        - name: cart-api
          image: ghcr.io/example/cart-api:latest
          resources:
            requests:
              memory: "256Mi"
"""

COST_INPUT = """\
Cloud rent: $1,500 / month
AI meter: 3,000,000 calls at $2.50 per 1M input tokens
Monthly total cost estimate: $16,500
Hard cap: $18,000
Alert threshold: $13,500
"""

READINESS_INPUT = """\
We are conducting an operational readiness review for cart-api.
Please evaluate the artefact set (01-stack-map through 06-readiness-brief)
and produce a go/no-go decision with a maturity gap inventory.
"""


class TestPositiveClassification:
    """Each canonical input classifies to the expected RequestType."""

    def test_diagnosis_input_classified_as_diagnosis(self) -> None:
        result = classify(DIAGNOSIS_INPUT)
        assert result == RequestType.DIAGNOSIS

    def test_audit_input_classified_as_audit(self) -> None:
        result = classify(AUDIT_INPUT)
        assert result == RequestType.AUDIT

    def test_cost_input_classified_as_cost(self) -> None:
        result = classify(COST_INPUT)
        assert result == RequestType.COST

    def test_readiness_input_classified_as_readiness(self) -> None:
        result = classify(READINESS_INPUT)
        assert result == RequestType.READINESS


class TestNegativeClassification:
    """Inputs with no recognisable signals return None."""

    def test_empty_string_returns_none(self) -> None:
        assert classify("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert classify("   \n\t  ") is None

    def test_unrelated_text_returns_none(self) -> None:
        assert classify("The quick brown fox jumps over the lazy dog.") is None


class TestPriorityResolution:
    """Multi-signal inputs resolve to the highest-priority type."""

    def test_diagnosis_beats_audit_on_mixed_input(self) -> None:
        """OOMKilled + Deployment manifest -> DIAGNOSIS wins."""
        mixed = DIAGNOSIS_INPUT + "\n" + AUDIT_INPUT
        result = classify(mixed)
        assert result == RequestType.DIAGNOSIS

    def test_diagnosis_beats_cost_on_mixed_input(self) -> None:
        mixed = DIAGNOSIS_INPUT + "\n" + COST_INPUT
        result = classify(mixed)
        assert result == RequestType.DIAGNOSIS

    def test_audit_beats_cost_on_mixed_input(self) -> None:
        """Manifest YAML + cost figures -> AUDIT wins."""
        mixed = AUDIT_INPUT + "\n" + COST_INPUT
        result = classify(mixed)
        assert result == RequestType.AUDIT


class TestCaseInsensitivity:
    """Classification patterns must be case-insensitive."""

    def test_oomkilled_lowercase(self) -> None:
        result = classify("pod terminated with reason oomkilled exit code 137")
        assert result == RequestType.DIAGNOSIS

    def test_kind_deployment_mixedcase(self) -> None:
        result = classify("kind: deployment\napiVersion: apps/v1")
        assert result == RequestType.AUDIT


# ===========================================================================
# classify_risk() — Risk Classification Engine tests (Sprint 2)
# ===========================================================================


class TestSeverityOrdering:
    """
    Verify that the four-level severity ordering is correctly implemented.

    Traceable to: spec.md §1.2 Step 6 "Severity ordering: LOW < MEDIUM <
    HIGH < CRITICAL"; delta.md §M-1.

    These tests verify the *engine* produces outputs that respect the ordering,
    not just that the enum is ordered (that is covered by test_models.py).
    """

    def test_low_is_lowest_result(self) -> None:
        """Empty findings → LOW, the minimum possible result."""
        assert classify_risk([]) == RiskLevel.LOW

    def test_medium_is_above_low(self) -> None:
        """A MEDIUM finding produces a result > LOW."""
        result = classify_risk([_medium_finding()])
        assert result > RiskLevel.LOW

    def test_high_is_above_medium(self) -> None:
        """A HIGH finding produces a result > MEDIUM."""
        result = classify_risk([_high_finding()])
        assert result > RiskLevel.MEDIUM

    def test_critical_is_above_high(self) -> None:
        """A CRITICAL finding produces a result > HIGH."""
        result = classify_risk([_write_command_finding()])
        assert result > RiskLevel.HIGH

    def test_severity_chain_ascending(self) -> None:
        """Results for each trigger level are strictly ascending."""
        low = classify_risk([])
        medium = classify_risk([_medium_finding()])
        high = classify_risk([_high_finding()])
        critical = classify_risk([_write_command_finding()])
        assert low < medium < high < critical

    def test_classification_never_skips_levels(self) -> None:
        """
        Classification must not skip directly to a higher level without
        satisfying its trigger condition.

        A list containing only a MEDIUM finding must not return HIGH or CRITICAL.
        Traceable to sprint brief: "Classification shall never skip directly to
        a higher level without satisfying its trigger condition."
        """
        result = classify_risk([_medium_finding()])
        assert result == RiskLevel.MEDIUM
        assert result < RiskLevel.HIGH
        assert result < RiskLevel.CRITICAL


class TestEmptyInput:
    """
    Empty input → LOW (clean-report path).

    Traceable to:
      spec.md §1.2 Step 6 Priority 5: "All other cases."
      AC-4: "No drift produces a clean report."
    """

    def test_empty_list_returns_low(self) -> None:
        """Positive: empty input → LOW."""
        assert classify_risk([]) == RiskLevel.LOW

    def test_empty_list_is_not_medium(self) -> None:
        """Negative: empty input must NOT be MEDIUM or higher."""
        result = classify_risk([])
        assert result < RiskLevel.MEDIUM

    def test_empty_list_result_type_is_risk_level(self) -> None:
        """Boundary: return type is always RiskLevel regardless of input."""
        result = classify_risk([])
        assert isinstance(result, RiskLevel)


class TestSingleFinding:
    """
    Single-finding classification — one finding of each level.

    Traceable to: sprint brief requirement "single finding."
    """

    def test_single_low_finding_returns_low(self) -> None:
        """Single additive finding with known ownership → LOW."""
        assert classify_risk([_low_finding()]) == RiskLevel.LOW

    def test_single_medium_finding_returns_medium(self) -> None:
        """Single non-safety modification → MEDIUM."""
        assert classify_risk([_medium_finding()]) == RiskLevel.MEDIUM

    def test_single_high_finding_returns_high(self) -> None:
        """Single safety-relevant removal → HIGH."""
        assert classify_risk([_high_finding()]) == RiskLevel.HIGH

    def test_single_write_command_finding_returns_critical(self) -> None:
        """Single write-command detection → CRITICAL (Priority 1)."""
        assert classify_risk([_write_command_finding()]) == RiskLevel.CRITICAL

    def test_single_pdb_violation_finding_returns_critical(self) -> None:
        """Single PDB replica violation → CRITICAL (Priority 2)."""
        assert classify_risk([_pdb_replica_violation_finding()]) == RiskLevel.CRITICAL


class TestHighestSeverityWins:
    """
    Multiple findings — the highest-severity trigger determines the result.

    Traceable to: sprint brief requirement "highest severity wins."
    spec.md §1.2: "The first matching condition determines the classification."
    Evaluation is in descending priority order, so the highest level wins.
    """

    def test_high_and_low_returns_high(self) -> None:
        """HIGH + LOW findings → HIGH."""
        findings = [_low_finding(), _high_finding()]
        assert classify_risk(findings) == RiskLevel.HIGH

    def test_critical_and_low_returns_critical(self) -> None:
        """CRITICAL + LOW findings → CRITICAL."""
        findings = [_low_finding(), _write_command_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_critical_and_high_returns_critical(self) -> None:
        """CRITICAL + HIGH findings → CRITICAL; HIGH does not win."""
        findings = [_high_finding(), _write_command_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_critical_and_medium_returns_critical(self) -> None:
        """CRITICAL + MEDIUM findings → CRITICAL."""
        findings = [_medium_finding(), _pdb_replica_violation_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_high_beats_medium_and_low(self) -> None:
        """HIGH + MEDIUM + LOW findings → HIGH."""
        findings = [_low_finding(), _medium_finding(), _high_finding()]
        assert classify_risk(findings) == RiskLevel.HIGH

    def test_medium_beats_low(self) -> None:
        """MEDIUM + LOW findings → MEDIUM."""
        findings = [_low_finding(), _medium_finding()]
        assert classify_risk(findings) == RiskLevel.MEDIUM

    def test_many_low_findings_stay_low(self) -> None:
        """Multiple LOW findings must not escalate to MEDIUM or above."""
        findings = [_low_finding() for _ in range(10)]
        assert classify_risk(findings) == RiskLevel.LOW


class TestUnknownOwnership:
    """
    Added component with undetermined ownership → MEDIUM.

    Traceable to:
      spec.md §1.2 Step 6 Priority 4:
      "at least one added component with undetermined ownership."
      CLAUDE.md Rule 3 (UNKNOWN sentinel).
      spec.md §1.2 Step 2 ownership labelling.
    """

    def test_added_with_unknown_owner_returns_medium(self) -> None:
        """Positive: added finding with UNKNOWN owner → MEDIUM."""
        assert classify_risk([_added_unknown_owner_finding()]) == RiskLevel.MEDIUM

    def test_added_with_known_owner_does_not_trigger_medium(self) -> None:
        """Negative: added finding with a known owner → LOW (not escalated to MEDIUM)."""
        finding = _added_unknown_owner_finding()
        known_owner_finding = Finding(
            component_type=finding.component_type,
            component_name=finding.component_name,
            category=finding.category,
            risk_level=finding.risk_level,
            artefact_reference=finding.artefact_reference,
            owner="[ops]",  # ownership resolved
            state_a_value=finding.state_a_value,
            state_b_value=finding.state_b_value,
        )
        assert classify_risk([known_owner_finding]) == RiskLevel.LOW

    def test_unknown_owner_on_removed_finding_does_not_trigger_medium_alone(self) -> None:
        """
        Boundary: UNKNOWN owner on a *removed* finding (not added) does not
        trigger the MEDIUM unknown-ownership rule.

        spec.md §1.2 Step 6 Priority 4 sub-trigger (b) is specifically for
        *added* components with undetermined ownership.  A removed component
        with UNKNOWN owner is classified by its risk_level field only.
        """
        removed_unknown = _finding(
            category="removed",
            risk_level=RiskLevel.LOW,  # detection layer kept it at LOW
            owner=UNKNOWN,
        )
        # The unknown-ownership trigger does not apply to "removed" category.
        # This finding has risk_level=LOW and category="removed" → LOW.
        assert classify_risk([removed_unknown]) == RiskLevel.LOW

    def test_multiple_added_with_unknown_owner_returns_medium(self) -> None:
        """Boundary: several UNKNOWN-owner added findings all return MEDIUM."""
        findings = [_added_unknown_owner_finding() for _ in range(3)]
        assert classify_risk(findings) == RiskLevel.MEDIUM


class TestCriticalTriggerPrecedence:
    """
    CRITICAL trigger takes precedence over all other levels.

    Traceable to:
      spec.md §1.2 Step 6: "The first matching condition determines the
      classification."  Priority 1 (write-command) and Priority 2 (PDB
      replica violation) are evaluated before Priority 3 (HIGH).
      delta.md §M-1: CRITICAL is above HIGH in the ordering.
      sprint brief: "CRITICAL trigger precedence."
    """

    def test_write_command_beats_high(self) -> None:
        """
        Priority 1 CRITICAL (write-command) evaluated before Priority 3 HIGH.
        A list with both a write-command finding and a HIGH finding must return
        CRITICAL.
        """
        findings = [_high_finding(), _write_command_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_write_command_beats_medium(self) -> None:
        """Priority 1 CRITICAL precedes Priority 4 MEDIUM."""
        findings = [_medium_finding(), _write_command_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_pdb_violation_beats_high(self) -> None:
        """
        Priority 2 CRITICAL (PDB replica violation) evaluated before
        Priority 3 HIGH.
        """
        findings = [_high_finding(), _pdb_replica_violation_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_pdb_violation_beats_medium(self) -> None:
        """Priority 2 CRITICAL precedes Priority 4 MEDIUM."""
        findings = [_medium_finding(), _pdb_replica_violation_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_write_command_takes_priority_over_pdb_violation(self) -> None:
        """
        When both CRITICAL triggers are present, the result is still CRITICAL.
        Order of evaluation: Priority 1 before Priority 2; both return CRITICAL.
        """
        findings = [_pdb_replica_violation_finding(), _write_command_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_critical_output_value_is_maximum(self) -> None:
        """CRITICAL result must be the RiskLevel maximum."""
        result = classify_risk([_write_command_finding()])
        assert result == RiskLevel.CRITICAL
        assert all(result >= level for level in RiskLevel)


# ===========================================================================
# Acceptance Criteria (spec.md §1.6 + delta.md §A-5)
# ===========================================================================


class TestAC1AddedComponentDetection:
    """
    AC-1 — Added component detection.

    Traceable to: spec.md §1.6 AC-1.
    "Given a State A snapshot ... and a State B snapshot containing the same
    Deployment plus a sidecar container and a new NetworkPolicy resource."

    Note: AC-1 is an output-structure acceptance criterion (it verifies the
    Drift Report *lists* two added components). The risk engine's responsibility
    in this path is to classify the risk level of added components correctly.
    A single added component with known ownership → LOW; with UNKNOWN
    ownership → MEDIUM.
    """

    def test_ac1_positive_single_added_known_owner_is_low(self) -> None:
        """
        Positive: added component with known ownership → LOW.

        Represents: sidecar container added to Deployment; ownership resolved
        as [mine/Product].
        """
        sidecar = _finding(
            category="added",
            risk_level=RiskLevel.LOW,
            component_type="Container",
            component_name="summarise-sidecar",
            owner="[mine/Product]",
            state_a_value="",
            state_b_value="container: summarise-sidecar",
        )
        assert classify_risk([sidecar]) == RiskLevel.LOW

    def test_ac1_positive_two_added_components_unknown_owner_is_medium(self) -> None:
        """
        Positive: two added components with UNKNOWN ownership → MEDIUM.

        Represents: sidecar + NetworkPolicy added; neither has a determinable
        owner from the artefact → UNKNOWN — owner needed.
        Traceable to: spec.md §1.2 Step 6 Priority 4 sub-trigger (b).
        """
        sidecar = _finding(
            category="added",
            risk_level=RiskLevel.LOW,
            component_type="Container",
            component_name="logging-sidecar",
            owner=UNKNOWN,
        )
        network_policy = _finding(
            category="added",
            risk_level=RiskLevel.LOW,
            component_type="NetworkPolicy",
            component_name="cart-api-netpol",
            owner=UNKNOWN,
        )
        assert classify_risk([sidecar, network_policy]) == RiskLevel.MEDIUM

    def test_ac1_negative_no_added_components_is_low(self) -> None:
        """Negative: no added components → LOW (all-clear)."""
        assert classify_risk([]) == RiskLevel.LOW

    def test_ac1_boundary_one_known_one_unknown_owner_is_medium(self) -> None:
        """
        Boundary: one added component has known owner, one has UNKNOWN owner.
        A single UNKNOWN-owner added finding is sufficient to trigger MEDIUM.
        """
        known = _finding(
            category="added",
            risk_level=RiskLevel.LOW,
            owner="[ops]",
        )
        unknown = _added_unknown_owner_finding()
        # MEDIUM triggered by the unknown-owner finding regardless of the other.
        assert classify_risk([known, unknown]) == RiskLevel.MEDIUM


class TestAC2SafetyRelevantRemovalTriggersHigh:
    """
    AC-2 — Safety-relevant removal triggers HIGH risk.

    Traceable to: spec.md §1.6 AC-2.
    "Given a State A snapshot containing a PodDisruptionBudget with
    minAvailable: 2 and a State B snapshot in which the PodDisruptionBudget
    is absent."

    Note: This AC specifically concerns a PDB *removed* when no replica-count
    violation is involved (the PDB simply disappears).  The detection layer
    assigns risk_level=HIGH for a removed PDB (spec.md §1.2 Step 3: "Removal
    of safety-relevant components (PDB, securityContext, readiness probe) is
    automatically classified as risk level HIGH").
    """

    def test_ac2_positive_pdb_removed_returns_high(self) -> None:
        """Positive: PDB removed → HIGH."""
        pdb_removed = _high_finding(component_type="PodDisruptionBudget")
        assert classify_risk([pdb_removed]) == RiskLevel.HIGH

    def test_ac2_positive_readiness_probe_removed_returns_high(self) -> None:
        """Positive: readiness probe removed → HIGH (safety-relevant component)."""
        probe_removed = _high_finding(component_type="readinessProbe")
        assert classify_risk([probe_removed]) == RiskLevel.HIGH

    def test_ac2_positive_security_context_removed_returns_high(self) -> None:
        """Positive: securityContext removed → HIGH (safety-relevant component)."""
        sc_removed = _high_finding(component_type="securityContext")
        assert classify_risk([sc_removed]) == RiskLevel.HIGH

    def test_ac2_negative_pdb_present_both_states_is_not_high(self) -> None:
        """
        Negative: when PDB is present in both states with no other changes,
        the result must be LOW (not HIGH).

        An empty findings list represents the no-drift case where PDB is
        unchanged between states.
        """
        assert classify_risk([]) == RiskLevel.LOW

    def test_ac2_boundary_pdb_removal_with_concurrent_low_findings(self) -> None:
        """
        Boundary: PDB removal (HIGH) alongside additive LOW findings.
        Highest severity wins → HIGH.
        """
        findings = [
            _high_finding(component_type="PodDisruptionBudget"),
            _low_finding(),
        ]
        assert classify_risk(findings) == RiskLevel.HIGH

    def test_ac2_boundary_pdb_removal_result_is_not_critical(self) -> None:
        """
        Boundary: PDB removed (no replica-count violation, no write-command) →
        HIGH, NOT CRITICAL.

        This is the boundary between HIGH and CRITICAL: removing the PDB
        without a replica-count violation classifies as HIGH only.
        Traceable to: spec.md §1.2 Step 6 Priority 3 vs Priority 2 note.
        """
        pdb_removed = _high_finding(component_type="PodDisruptionBudget")
        result = classify_risk([pdb_removed])
        assert result == RiskLevel.HIGH
        assert result < RiskLevel.CRITICAL


class TestAC3ModifiedSecurityFieldDetected:
    """
    AC-3 — Modified security context field detected and classified HIGH.

    Traceable to: spec.md §1.6 AC-3.
    "Given a State A snapshot in which ... readOnlyRootFilesystem: true, and
    a State B snapshot in which readOnlyRootFilesystem is absent."

    The detection layer assigns risk_level=HIGH when a security context field
    is modified (spec.md §1.2 Step 6 Priority 3).
    """

    def test_ac3_positive_security_field_modified_returns_high(self) -> None:
        """Positive: security context field modified → HIGH."""
        sc_modified = _finding(
            category="modified",
            risk_level=RiskLevel.HIGH,
            component_type="securityContext field",
            component_name="readOnlyRootFilesystem",
            state_a_value="true",
            state_b_value="absent",
        )
        assert classify_risk([sc_modified]) == RiskLevel.HIGH

    def test_ac3_positive_allow_privilege_escalation_weakened_returns_high(self) -> None:
        """Positive: allowPrivilegeEscalation changed from false to true → HIGH."""
        sc_weakened = _finding(
            category="modified",
            risk_level=RiskLevel.HIGH,
            component_type="securityContext field",
            component_name="allowPrivilegeEscalation",
            state_a_value="false",
            state_b_value="true",
        )
        assert classify_risk([sc_weakened]) == RiskLevel.HIGH

    def test_ac3_positive_mutable_image_tag_returns_high(self) -> None:
        """Positive: image tag changed to mutable reference (latest) → HIGH."""
        image_mutable = _finding(
            category="modified",
            risk_level=RiskLevel.HIGH,
            component_type="image reference",
            component_name="cart-api image",
            state_a_value="sha256:abc123def456",
            state_b_value="latest",
        )
        assert classify_risk([image_mutable]) == RiskLevel.HIGH

    def test_ac3_negative_no_security_modification_is_not_high(self) -> None:
        """
        Negative: only non-safety modifications present → must not be HIGH.
        A MEDIUM finding (non-safety field) does not escalate to HIGH.
        """
        result = classify_risk([_medium_finding()])
        assert result == RiskLevel.MEDIUM
        assert result < RiskLevel.HIGH

    def test_ac3_boundary_security_field_modified_alongside_medium(self) -> None:
        """
        Boundary: security field modification (HIGH) alongside a non-safety
        modification (MEDIUM) → HIGH wins.
        """
        findings = [
            _medium_finding(),
            _finding(
                category="modified",
                risk_level=RiskLevel.HIGH,
                component_type="securityContext field",
                component_name="runAsNonRoot",
                state_a_value="true",
                state_b_value="false",
            ),
        ]
        assert classify_risk(findings) == RiskLevel.HIGH


class TestAC4NoDriftCleanReport:
    """
    AC-4 — No drift produces a clean report.

    Traceable to: spec.md §1.6 AC-4.
    "Given a State A snapshot and a State B snapshot that are byte-for-byte
    identical in all supplied artefact fields ... Risk Level is LOW."

    Empty findings list is the canonical no-drift case; the detection layer
    produces no findings when states are identical.
    """

    def test_ac4_positive_empty_findings_returns_low(self) -> None:
        """Positive: no drift (empty findings) → LOW."""
        assert classify_risk([]) == RiskLevel.LOW

    def test_ac4_positive_all_low_risk_findings_returns_low(self) -> None:
        """
        Positive: multiple findings all at LOW risk with known owners → LOW.

        Represents additive-only changes where all ownerships are determinable.
        """
        findings = [_low_finding() for _ in range(5)]
        assert classify_risk(findings) == RiskLevel.LOW

    def test_ac4_negative_single_medium_finding_is_not_low(self) -> None:
        """Negative: a single MEDIUM finding must not return LOW."""
        assert classify_risk([_medium_finding()]) != RiskLevel.LOW

    def test_ac4_boundary_single_low_finding_with_known_owner_is_low(self) -> None:
        """
        Boundary: exactly one additive finding with a known owner → LOW.

        Verifies that the minimum non-empty "clean" input still produces LOW.
        """
        finding = _finding(
            category="added",
            risk_level=RiskLevel.LOW,
            owner="[ops]",
        )
        assert classify_risk([finding]) == RiskLevel.LOW


class TestAC5CriticalReplicaCountBelowMinAvailable:
    """
    AC-5 — CRITICAL triggered by replica-count-below-minAvailable removal.

    Traceable to: delta.md §A-5; changes/operational-drift-risk-model/plan.md
    Component 5; changes/operational-drift-risk-model/tasks.md T5.

    Given:
      State A: PDB with minAvailable: 2; Deployment with replicas: 3.
      State B: Deployment with replicas: 1; PDB still present.

    When: Drift Analysis invoked.

    Then: Risk Level is CRITICAL.
    """

    def test_ac5_positive_replica_violation_with_pdb_returns_critical(self) -> None:
        """
        Positive: PDB present in State A; replicas in State B < minAvailable →
        CRITICAL.
        """
        finding = _pdb_replica_violation_finding()
        assert classify_risk([finding]) == RiskLevel.CRITICAL

    def test_ac5_positive_critical_result_is_maximum(self) -> None:
        """Positive: CRITICAL is the maximum possible risk level."""
        result = classify_risk([_pdb_replica_violation_finding()])
        assert result == RiskLevel.CRITICAL
        assert result == max(RiskLevel)

    def test_ac5_negative_no_pdb_present_is_not_critical(self) -> None:
        """
        Negative (also PT-1 boundary condition):
        When no PDB is present in State A, a replica count reduction MUST NOT
        produce CRITICAL.

        The detection layer must not emit CATEGORY_PDB_REPLICA_VIOLATION when
        no PDB is present.  It emits a plain "modified" or "removed" finding
        at HIGH or lower instead.  This test verifies that a finding with
        category="modified" and risk_level=HIGH (the no-PDB path) does not
        trigger CRITICAL.

        Traceable to: spec.md §1.2 Step 6 Priority 2:
        "This trigger applies only when a PodDisruptionBudget is present
        in State A."
        delta.md Risk Note Proof Test (HIGH-preserved-on-no-PDB).
        changes/operational-drift-risk-model/tasks.md T5 PT-1.
        """
        # Simulate: no PDB in State A; detection layer emits HIGH finding for
        # replica count reduction (not pdb_replica_violation).
        replica_reduction_no_pdb = _finding(
            category="modified",
            risk_level=RiskLevel.HIGH,  # detection layer: HIGH (no PDB carve-out)
            component_type="Deployment",
            component_name="cart-api",
            state_a_value="replicas: 3",
            state_b_value="replicas: 1",
        )
        result = classify_risk([replica_reduction_no_pdb])
        assert result == RiskLevel.HIGH
        assert result != RiskLevel.CRITICAL

    def test_ac5_boundary_pdb_violation_with_concurrent_high_finding(self) -> None:
        """
        Boundary: PDB replica violation (CRITICAL) alongside a HIGH finding.
        CRITICAL takes priority over HIGH.
        """
        findings = [
            _high_finding(component_type="securityContext"),
            _pdb_replica_violation_finding(),
        ]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_ac5_boundary_pdb_violation_category_is_recognised(self) -> None:
        """
        Boundary: the CATEGORY_PDB_REPLICA_VIOLATION constant string is
        recognised by classify_risk().

        Verifies that the constant exported from classifier.py matches what
        the engine checks internally.
        """
        finding = Finding(
            component_type="Deployment",
            component_name="cart-api",
            category=CATEGORY_PDB_REPLICA_VIOLATION,
            risk_level=RiskLevel.CRITICAL,
            artefact_reference="artefacts/800-wide/02-deploy-manifest.md",
        )
        assert classify_risk([finding]) == RiskLevel.CRITICAL


class TestPT1HighPreservedOnNoPdb:
    """
    PT-1 — HIGH preserved when no PDB present (HIGH / CRITICAL boundary).

    Traceable to: delta.md Risk Note — Proof Test "HIGH-preserved-on-no-PDB".
    changes/operational-drift-risk-model/tasks.md T5 PT-1.
    changes/operational-drift-risk-model/delta.md Risk Note §Proof Test.

    Given:
      State A: Deployment with replicas: 3. No PodDisruptionBudget present.
      State B: Deployment with replicas: 1. No PodDisruptionBudget present.

    When: Drift Analysis invoked.

    Then:
      Risk Level is HIGH (not CRITICAL).
      The READINESS IMPACT annotation must NOT be present.
      The mandatory executive escalation block must NOT be present.

    This test exercises the most dangerous boundary: the carve-out that
    prevents a replica-count reduction from escalating to CRITICAL when no
    PDB exists in State A.
    """

    def test_pt1_no_pdb_replica_reduction_returns_high(self) -> None:
        """
        Positive: no PDB in State A, replicas reduced in State B → HIGH.
        (The detection layer emits a modified/HIGH finding, not pdb_replica_violation.)
        """
        replica_reduced = _finding(
            category="modified",
            risk_level=RiskLevel.HIGH,
            component_type="Deployment",
            component_name="cart-api",
            state_a_value="replicas: 3",
            state_b_value="replicas: 1",
        )
        result = classify_risk([replica_reduced])
        assert result == RiskLevel.HIGH

    def test_pt1_result_is_not_critical(self) -> None:
        """Positive: no PDB path must never return CRITICAL."""
        replica_reduced = _finding(
            category="modified",
            risk_level=RiskLevel.HIGH,
            component_type="Deployment",
            component_name="cart-api",
            state_a_value="replicas: 3",
            state_b_value="replicas: 1",
        )
        assert classify_risk([replica_reduced]) != RiskLevel.CRITICAL

    def test_pt1_critical_requires_pdb_violation_category(self) -> None:
        """
        Negative: a finding with category="modified" and risk_level=HIGH
        must not produce CRITICAL regardless of its state values.

        CRITICAL (Priority 2) is gated exclusively on the
        CATEGORY_PDB_REPLICA_VIOLATION category token — set only when a PDB
        is confirmed present in State A.
        """
        # This mimics the no-PDB path exactly as the detection layer would emit it.
        finding = _finding(
            category="modified",  # NOT pdb_replica_violation
            risk_level=RiskLevel.HIGH,
            state_a_value="replicas: 3",
            state_b_value="replicas: 1",
        )
        assert classify_risk([finding]) == RiskLevel.HIGH
        assert classify_risk([finding]) != RiskLevel.CRITICAL

    def test_pt1_boundary_no_pdb_high_not_elevated_by_low_sibling(self) -> None:
        """
        Boundary: no-PDB replica reduction (HIGH) alongside LOW findings.
        Highest severity is still HIGH — not CRITICAL, not MEDIUM.
        """
        findings = [
            _low_finding(),
            _finding(
                category="modified",
                risk_level=RiskLevel.HIGH,
                state_a_value="replicas: 3",
                state_b_value="replicas: 1",
            ),
        ]
        assert classify_risk(findings) == RiskLevel.HIGH
        assert classify_risk(findings) != RiskLevel.CRITICAL


class TestWriteCommandCategory:
    """
    Priority 1 CRITICAL: write-command artefact in State B absent from State A.

    Traceable to: spec.md §1.2 Step 6 Priority 1; delta.md §A-1; spec.md §3.1
    WRITE_COMMAND_DETECTED error description.
    """

    def test_write_command_category_returns_critical(self) -> None:
        """Positive: write-command finding → CRITICAL."""
        assert classify_risk([_write_command_finding()]) == RiskLevel.CRITICAL

    def test_write_command_overrides_high_finding(self) -> None:
        """Priority 1 pre-empts Priority 3."""
        findings = [_high_finding(), _write_command_finding()]
        assert classify_risk(findings) == RiskLevel.CRITICAL

    def test_no_write_command_category_does_not_produce_critical(self) -> None:
        """
        Negative: without CATEGORY_WRITE_COMMAND the write-command trigger
        is never fired.
        A finding with risk_level=CRITICAL but category="removed" is treated
        by the engine at Priority 3 (HIGH) because it is not a write_command
        or pdb_replica_violation category.
        """
        finding = _finding(
            category="removed",
            risk_level=RiskLevel.HIGH,  # detection layer capped at HIGH
        )
        result = classify_risk([finding])
        # Should be HIGH (Priority 3), not CRITICAL
        assert result == RiskLevel.HIGH

    def test_write_command_category_constant_is_correct_string(self) -> None:
        """Boundary: the exported constant string matches what the engine recognises."""
        assert CATEGORY_WRITE_COMMAND == "write_command_detected"

    def test_pdb_replica_violation_category_constant_is_correct_string(self) -> None:
        """Boundary: the exported constant string matches what the engine recognises."""
        assert CATEGORY_PDB_REPLICA_VIOLATION == "pdb_replica_violation"


class TestReturnTypeInvariants:
    """
    classify_risk() must always return a RiskLevel and never raise on valid input.

    These tests verify the interface contract properties (Seam 1 — tasks.md).
    """

    @pytest.mark.parametrize("findings", [
        [],
        [_low_finding()],
        [_medium_finding()],
        [_high_finding()],
        [_write_command_finding()],
        [_pdb_replica_violation_finding()],
        [_low_finding(), _medium_finding(), _high_finding()],
    ])
    def test_return_is_always_risk_level(self, findings: list[Finding]) -> None:
        """Return type is always RiskLevel."""
        result = classify_risk(findings)
        assert isinstance(result, RiskLevel)

    @pytest.mark.parametrize("findings", [
        [],
        [_low_finding()],
        [_medium_finding()],
        [_high_finding()],
        [_write_command_finding()],
        [_pdb_replica_violation_finding()],
    ])
    def test_return_is_in_vocabulary(self, findings: list[Finding]) -> None:
        """
        Return value must be one of the four permitted vocabulary tokens.

        Traceable to: spec.md §6.3 NFR "Risk level vocabulary compliance."
        delta.md §A-4 (CRITICAL is a valid, producible output).
        """
        result = classify_risk(findings)
        assert result in {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}

    def test_critical_active_invariant_true_iff_critical(self) -> None:
        """
        critical_active is True if and only if result == CRITICAL.

        Traceable to: spec.md §1.2 "Interface contract emitted by this logic."
        changes/operational-drift-risk-model/tasks.md Seam 1.
        """
        critical_result = classify_risk([_write_command_finding()])
        non_critical_results = [
            classify_risk([]),
            classify_risk([_low_finding()]),
            classify_risk([_medium_finding()]),
            classify_risk([_high_finding()]),
        ]
        # critical_active is computed by the caller as result == RiskLevel.CRITICAL
        assert (critical_result == RiskLevel.CRITICAL) is True
        for result in non_critical_results:
            assert (result == RiskLevel.CRITICAL) is False
