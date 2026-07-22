"""
models.py — Domain model for the Cloud Operations Readiness Reference Engine.

This module defines the canonical enumerations and value types that the
specification requires.  It contains NO logic — only type definitions.

Rules enforced (traceable to SKILL.md):
    - Exactly four request types (SKILL.md §Outputs).
    - Exactly three verdict values (SKILL.md §Output Type 4).
    - Exactly four audit-item statuses (SKILL.md §Output Type 2).
    - Audit checklist is fixed at AUDIT_CHECKLIST_SIZE = 12 items.
    - Hypothesis count is fixed at HYPOTHESIS_COUNT = 3.
    - Readiness question count is fixed at READINESS_QUESTION_COUNT = 6.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum, unique

# ---------------------------------------------------------------------------
# Specification constants
# These are the only values permitted by SKILL.md.  Any change requires a
# corresponding specification update first.
# ---------------------------------------------------------------------------

HYPOTHESIS_COUNT: int = 3
"""Exactly three hypotheses are required for every DIAGNOSIS output."""

AUDIT_CHECKLIST_SIZE: int = 12
"""The audit checklist is fixed at twelve items.  All must be evaluated."""

READINESS_QUESTION_COUNT: int = 6
"""Six readiness questions are evaluated in fixed order."""

HARD_CAP_FLOOR_MULTIPLIER: float = 1.20
"""Hard cap must be set at >= 120 % of the current monthly baseline (SKILL.md §Output Type 3)."""

ALERT_THRESHOLD_CEILING_MULTIPLIER: float = 0.75
"""Alert threshold must be set at <= 75 % of the hard cap (SKILL.md §Output Type 3)."""


# ---------------------------------------------------------------------------
# Request classification
# ---------------------------------------------------------------------------


@unique
class RequestType(StrEnum):
    """The four output types supported by the Skill (SKILL.md §Outputs)."""

    DIAGNOSIS = "DIAGNOSIS"
    """Ranked hypotheses from logs, events, or pod output."""

    AUDIT = "AUDIT"
    """12-item deployment and IaC checklist."""

    COST = "COST"
    """Cloud rent vs AI meter split with gateway cap validation."""

    READINESS = "READINESS"
    """Six-question go/no-go operational readiness review."""


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@unique
class AuditStatus(StrEnum):
    """
    The only four values permitted for an audit checklist item (SKILL.md §Output Type 2).

    No gradational language.  Status must be one of these four values.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT APPLICABLE"


@dataclass(frozen=True)
class AuditChecklistItem:
    """A single item in the 12-item audit checklist."""

    number: int
    """Checklist item number, 1-12, evaluated in fixed order."""

    name: str
    """Short name matching the specification table."""

    evaluation_criteria: str
    """Verbatim evaluation criteria from SKILL.md §Output Type 2."""


# Specification table — order is normative (SKILL.md §Output Type 2).
AUDIT_CHECKLIST: tuple[AuditChecklistItem, ...] = (
    AuditChecklistItem(1, "Resource limits", "`requests` and `limits` defined for CPU and memory"),
    AuditChecklistItem(
        2, "Liveness probe", "`httpGet` or `exec` probe with explicit path and port"
    ),
    AuditChecklistItem(3, "Readiness probe", "Separate from liveness; distinct health semantics"),
    AuditChecklistItem(4, "Startup probe", "Present for services with slow initialisation"),
    AuditChecklistItem(
        5,
        "Security context",
        "`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`",
    ),
    AuditChecklistItem(
        6, "Immutable image reference", "Tag is not `latest`; digest (`sha256:`) preferred"
    ),
    AuditChecklistItem(
        7,
        "Rolling update strategy",
        "`type: RollingUpdate` with explicit `maxUnavailable` and `maxSurge`",
    ),
    AuditChecklistItem(8, "Pod disruption budget", "`PodDisruptionBudget` resource present"),
    AuditChecklistItem(
        9,
        "Dedicated service account",
        "Named `ServiceAccount`; `automountServiceAccountToken: false`",
    ),
    AuditChecklistItem(
        10,
        "OIDC / Workload Identity",
        "CI/CD uses short-lived credentials; no static secrets for cluster auth",
    ),
    AuditChecklistItem(
        11, "Supply-chain security", "Image scanning present; dependency scanning present"
    ),
    AuditChecklistItem(
        12,
        "Anti-affinity / topology spread",
        "Pod spread constraints or anti-affinity rules defined",
    ),
)

assert len(AUDIT_CHECKLIST) == AUDIT_CHECKLIST_SIZE, (
    f"AUDIT_CHECKLIST must contain exactly {AUDIT_CHECKLIST_SIZE} items; "
    f"found {len(AUDIT_CHECKLIST)}"
)


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


@unique
class ReadinessVerdict(StrEnum):
    """
    The three permitted readiness verdicts (SKILL.md §Output Type 4).

    No gradational language.  The verdict MUST be one of these three values.
    """

    READY = "Ready"
    READY_WITH_MITIGATIONS = "Ready with Mitigations"
    NOT_READY = "Not Ready"


@dataclass(frozen=True)
class ReadinessQuestion:
    """One of the six fixed readiness questions."""

    number: int
    """Question number, 1-6, evaluated in fixed order."""

    question: str
    """Verbatim question text from SKILL.md §Output Type 4."""

    what_a_complete_answer_contains: str
    """Guidance on what constitutes a complete answer.

    See REFERENCE.md §Six Standard Readiness Questions.
    """


# Specification table — order is normative (SKILL.md §Output Type 4).
READINESS_QUESTIONS: tuple[ReadinessQuestion, ...] = (
    ReadinessQuestion(
        1, "How does the application deploy?", "Tool, trigger, steps, verification mechanism"
    ),
    ReadinessQuestion(
        2, "How does rollback work?", "Command or procedure, verification step, time estimate"
    ),
    ReadinessQuestion(
        3, "Who is paged during incidents?", "Role name, escalation path, pager tool (or UNKNOWN)"
    ),
    ReadinessQuestion(
        4,
        "What is monitored?",
        "Named components, signal types (metrics/logs/traces), alert definitions",
    ),
    ReadinessQuestion(
        5,
        "What is the estimated monthly cost and cost cap?",
        "Split total, hard cap value, alert threshold",
    ),
    ReadinessQuestion(
        6,
        "What is the operational kill switch?",
        "Feature flag, circuit breaker, or rollback procedure",
    ),
)

assert len(READINESS_QUESTIONS) == READINESS_QUESTION_COUNT, (
    f"READINESS_QUESTIONS must contain exactly {READINESS_QUESTION_COUNT} items; "
    f"found {len(READINESS_QUESTIONS)}"
)


# ---------------------------------------------------------------------------
# Risk level
# ---------------------------------------------------------------------------
# Traceable to: spec.md §1.2 — "Severity ordering: LOW < MEDIUM < HIGH < CRITICAL"
# and delta.md §M-1 — "The ordering of severity from lowest to highest is:
#   LOW < MEDIUM < HIGH < CRITICAL."
#
# IntEnum is used so that comparison operators (<, >, <=, >=) express severity
# ordering directly: RiskLevel.LOW < RiskLevel.HIGH is True.  StrEnum does not
# provide ordered comparison; it inherits str.__lt__ which is lexicographic and
# would place CRITICAL < HIGH (C < H alphabetically), violating the spec.
#
# The integer values are the severity weights.  They are not exposed in output;
# __str__ returns the label string so serialisation is unchanged.
# ---------------------------------------------------------------------------


@unique
class RiskLevel(IntEnum):
    """
    Risk severity for drift findings.

    Traceable to: specs/operational-drift-analysis/spec.md §1.2 Step 6 and
    changes/operational-drift-risk-model/delta.md §A-1 / M-1.

    Severity ordering (ascending): LOW < MEDIUM < HIGH < CRITICAL.
    This ordering is enforced by IntEnum; comparison operators work correctly.

    String representation returns the label (e.g. "LOW") so that downstream
    output formatters and validators receive the string the spec requires.
    """

    LOW = 1
    """All changes are additive with no safety-relevant removals; no modified security fields."""

    MEDIUM = 2
    """At least one modification to a non-safety field; or at least one added component
    with undetermined ownership."""

    HIGH = 3
    """At least one removal of a safety-relevant component; or any security context field
    modified; or image tag changed to mutable reference."""

    CRITICAL = 4
    """Any write-command artefact detected in State B absent from State A; or any component
    whose removal causes effective replica count in State B to fall below the minAvailable
    value declared in the PodDisruptionBudget present in State A."""

    def __str__(self) -> str:
        """Return the label string (e.g. 'LOW'), not the integer value."""
        return self.name


# ---------------------------------------------------------------------------
# Unknown sentinel
# ---------------------------------------------------------------------------

UNKNOWN: str = "UNKNOWN — owner needed"
"""
The exact string to emit when a required fact cannot be determined from
available evidence (SKILL.md §Inputs; CLAUDE.md Rule 3).

Never infer, estimate, or fabricate missing values.
"""


# ---------------------------------------------------------------------------
# Drift Analysis domain models
# ---------------------------------------------------------------------------
# Traceable to: specs/operational-drift-analysis/spec.md §1.2 (Drift Detection
# Logic) and §1.3 (Output Structure).
#
# These are immutable value objects.  They carry no logic — they record a
# single finding or recommendation produced by the classification layer.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """
    A single drift finding produced during state comparison.

    Traceable to: specs/operational-drift-analysis/spec.md §1.2 Steps 2-4
    (Added, Removed, and Modified component detection).

    Each finding represents one discrete observable delta between State A and
    State B.  Findings are immutable; they are never mutated after creation.

    Attributes
    ----------
    component_type : str
        The type of the component that changed (e.g. "Deployment", "Service",
        "PodDisruptionBudget", "securityContext field").
    component_name : str
        The name of the component as it appears in the artefact.
    category : str
        One of ``"added"``, ``"removed"``, or ``"modified"``.  These map
        directly to the three detection categories in spec §1.2.
    risk_level : RiskLevel
        The initial risk classification for this individual finding, evaluated
        against the trigger conditions in spec §1.2 Step 6.
    artefact_reference : str
        The artefact file and field from which the finding was derived.
        Traceable to spec §1.4: "Every finding must cite the artefact and
        field from which it was derived."
    state_a_value : str
        The value present in State A for this field.  Empty string when the
        component is newly added (category == "added").
    state_b_value : str
        The value present in State B for this field.  Empty string when the
        component is absent in State B (category == "removed").
    owner : str
        Ownership label: ``"[ops]"``, ``"[mine/Product]"``, or the UNKNOWN
        sentinel when ownership cannot be determined (CLAUDE.md Rule 3;
        spec §1.2 Step 2).
    """

    component_type: str
    component_name: str
    category: str
    risk_level: RiskLevel
    artefact_reference: str
    state_a_value: str = ""
    state_b_value: str = ""
    owner: str = UNKNOWN


@dataclass(frozen=True)
class Recommendation:
    """
    A single recommended engineering review action.

    Traceable to: specs/operational-drift-analysis/spec.md §1.2 Step 7
    ("Recommended engineering review — a list of up to five named,
    role-attributed actions using the standard escalation block format.")
    and SKILL.md §Escalation Policy / CLAUDE.md §Escalation Format.

    Recommendations are immutable value objects.  They carry no execution
    logic — they surface an action for human review and approval.

    Attributes
    ----------
    action : str
        The specific action that must be taken.  Never a write command;
        write commands are surfaced in escalation sections only (SKILL.md
        §Tool Allowlist; CLAUDE.md Rule 1).
    role : str
        The named human role responsible for executing the action.
    condition : str
        The trigger condition or approval gate that makes this action necessary.
    artefact : str
        The relevant artefact or document to reference.
    risk_level : RiskLevel
        The severity level of the finding that triggered this recommendation.
        Used to rank recommendations in descending priority order (spec §1.2
        Step 7: "Actions are ranked by risk level descending.").
    """

    action: str
    role: str
    condition: str
    artefact: str
    risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass(frozen=True)
class ReadinessReport:
    """
    Immutable summary of an operational readiness assessment.

    Traceable to: SKILL.md §Output Type 4 and REFERENCE.md §Readiness Reviews.

    This model captures the verdict, the gap inventory, and the artefact
    reference for a single readiness evaluation.  It is a data-only value
    object; all construction and validation logic lives in other modules.

    Note: The full mutable output dataclass (with all six question answers,
    support tiers, and next actions) lives in ``report.py``.  This model
    captures the minimal immutable summary required by the domain layer.

    Attributes
    ----------
    verdict : ReadinessVerdict
        The final go/no-go verdict.  Must be one of the three named values
        defined by SKILL.md §Output Type 4 and CLAUDE.md Rule 7.
        No gradational language is permitted.
    maturity_gaps : tuple[str, ...]
        An immutable sequence of gap descriptions.  Each entry includes a
        recommended next action and a named owner.  An empty tuple means no
        gaps were identified (verdict will be READY in this case).
        Traceable to SKILL.md §Output Type 4: "Maturity Gaps — bulleted list;
        each gap includes recommended next action."
    artefact_reference : str
        The artefact set identifier that was evaluated (e.g. ``"artefacts/
        800-wide/ 01-06"``).  Traceable to spec §1.4: findings must cite
        their evidence source.
    critical_drift_active : bool
        ``True`` when a CRITICAL drift risk level is propagated into this
        readiness assessment.  A CRITICAL drift level is a hard block:
        the verdict cannot be ``Ready`` when this flag is ``True``.
        Traceable to specs/operational-drift-analysis/spec.md §5.2 and
        changes/operational-drift-risk-model/delta.md §A-3.
    """

    verdict: ReadinessVerdict
    maturity_gaps: tuple[str, ...] = ()
    artefact_reference: str = UNKNOWN
    critical_drift_active: bool = False
