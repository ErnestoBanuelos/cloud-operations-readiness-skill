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
