"""
report.py — Output report dataclasses for the Reference Engine v0.1.

Each dataclass represents one of the four output types defined in SKILL.md.
These are data-only structures.  No construction logic lives here.
Future kata implementations will populate these structures from parsed inputs.

Traceability
------------
DiagnosisReport     → SKILL.md §Output Type 1
AuditReport         → SKILL.md §Output Type 2
CostReport          → SKILL.md §Output Type 3
ReadinessReport     → SKILL.md §Output Type 4

All structural invariants (hypothesis count, checklist size, etc.) are
enforced by validator.py, not here.  Report dataclasses are intentionally
permissive to support incremental construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from readiness_engine.models import (
    UNKNOWN,
    AuditStatus,
    ReadinessVerdict,
    RequestType,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


@dataclass
class EscalationBlock:
    """
    A structured escalation record (SKILL.md §Escalation Policy; CLAUDE.md §Escalation Format).

    Every write action recommended by the engine must be surfaced as an
    EscalationBlock rather than embedded in mitigation text.

    Fields
    ------
    action      : The specific write action that must be taken.
    role        : The named human role responsible for this action.
    condition   : The trigger condition or approval gate.
    artefact    : The relevant artefact or document to reference.
    """

    action: str
    role: str
    condition: str
    artefact: str


# ---------------------------------------------------------------------------
# Output Type 1 — Operational Diagnosis
# ---------------------------------------------------------------------------


@dataclass
class Hypothesis:
    """
    A single ranked hypothesis within a DIAGNOSIS output.

    SKILL.md §Output Type 1 requires:
        - confidence level expressed as a percentage (0-100)
        - evidence for
        - evidence against
        - cheapest read-only verification command
    """

    rank: int
    """Rank 1 = most likely."""

    title: str
    """Short descriptive title for the hypothesis."""

    confidence_pct: int
    """Confidence expressed as an integer percentage 0-100."""

    evidence_for: list[str] = field(default_factory=list)
    """Observable facts that support this hypothesis."""

    evidence_against: list[str] = field(default_factory=list)
    """Observable facts that argue against this hypothesis."""

    verification_command: str = ""
    """The cheapest read-only kubectl command to confirm or refute this hypothesis."""


@dataclass
class DiagnosisReport:
    """
    DIAGNOSIS output (SKILL.md §Output Type 1).

    Exactly three hypotheses are required.
    Structural validation is performed by validator.validate_diagnosis_report().
    """

    request_type: RequestType = RequestType.DIAGNOSIS

    incident_summary: str = ""
    """One paragraph of observable facts only.  No inferences."""

    hypotheses: list[Hypothesis] = field(default_factory=list)
    """Exactly three ranked hypotheses (enforced by validator)."""

    immediate_mitigation: list[str] = field(default_factory=list)
    """Read-only diagnostic steps only.  No write commands."""

    escalation: EscalationBlock | None = None
    """Write actions are placed here, not in immediate_mitigation."""


# ---------------------------------------------------------------------------
# Output Type 2 — Deployment and IaC Audit
# ---------------------------------------------------------------------------


@dataclass
class AuditItem:
    """
    A single row in the 12-item audit checklist (SKILL.md §Output Type 2).

    Status must be one of: PASS / FAIL / PARTIAL / NOT APPLICABLE.
    """

    number: int
    """Checklist item number 1-12, evaluated in fixed order."""

    name: str
    """Short name matching the specification table."""

    status: AuditStatus = AuditStatus.FAIL

    priority: RiskLevel = RiskLevel.HIGH

    finding: str = ""
    """What was observed in the manifest or workflow."""

    recommended_fix: str = ""
    """Recommended remediation action.  Write actions are surfaced in escalation."""

    responsible_role: str = UNKNOWN
    """Named human role responsible for implementing the fix."""


@dataclass
class AuditReport:
    """
    AUDIT output (SKILL.md §Output Type 2).

    All 12 checklist items must be present and in order.
    Structural validation is performed by validator.validate_audit_report().
    """

    request_type: RequestType = RequestType.AUDIT

    audit_summary: str = ""
    """Pass/fail counts and overall assessment."""

    checklist: list[AuditItem] = field(default_factory=list)
    """Exactly 12 items evaluated in fixed order (enforced by validator)."""

    production_blockers: list[AuditItem] = field(default_factory=list)
    """Critical items only; must be resolved before deployment."""

    recommended_before_prod: list[AuditItem] = field(default_factory=list)
    """High-priority items; strong recommendation to resolve."""

    positive_findings: list[AuditItem] = field(default_factory=list)
    """Items already correctly implemented."""

    escalations: list[EscalationBlock] = field(default_factory=list)
    """One EscalationBlock per critical finding."""


# ---------------------------------------------------------------------------
# Output Type 3 — Cloud Cost Review
# ---------------------------------------------------------------------------


@dataclass
class CostLineItem:
    """A single line item in the cost report arithmetic."""

    description: str
    amount: float
    owner: str
    """Platform/ops team or product/feature team."""

    notes: str = ""


@dataclass
class CostReport:
    """
    COST output (SKILL.md §Output Type 3).

    Cloud rent and AI meter are always separate.
    Cap and threshold rules are enforced by validator.validate_cost_report().
    """

    request_type: RequestType = RequestType.COST

    cost_inputs: list[dict[str, object]] = field(default_factory=list)
    """Table of all input values with sources."""

    line_items: list[CostLineItem] = field(default_factory=list)
    """Each line shown explicitly; no black-box totals."""

    cloud_rent: float = 0.0
    """Infrastructure cost: flat — scales with capacity, not requests."""

    ai_meter: float = 0.0
    """AI token cost: variable — scales with feature usage."""

    monthly_total: float = 0.0
    """cloud_rent + ai_meter.  Must equal the sum of line items."""

    cloud_rent_owner: str = UNKNOWN
    """Platform / ops team."""

    ai_meter_owner: str = UNKNOWN
    """Product / feature team."""

    hard_cap: float = 0.0
    """Gateway hard cap value.  Must be >= 120% of monthly_total."""

    alert_threshold: float = 0.0
    """Alert threshold.  Must be <= 75% of hard_cap."""

    enforcement_action: str = "HTTP 429 Too Many Requests"
    """Action taken on cap breach (REFERENCE.md §Cost Cap Design)."""

    ship_recommendation: str = UNKNOWN
    """One of: Ship / Ship with Mitigation / Reject."""


# ---------------------------------------------------------------------------
# Output Type 4 — Operational Readiness Review
# ---------------------------------------------------------------------------


@dataclass
class ReadinessAnswer:
    """The answer to one of the six fixed readiness questions."""

    number: int
    """Question number 1-6."""

    question: str
    """Verbatim question text."""

    answer: str = UNKNOWN
    """
    The answer.  If information is absent the exact sentinel string UNKNOWN is used.
    Never infer, estimate, or fabricate.
    """

    status: str = "UNKNOWN"
    """ANSWERED | UNKNOWN.  UNKNOWN is acceptable only if tracked with a named owner."""

    owner: str | None = None
    """Named owner required when status is UNKNOWN."""


@dataclass
class SupportTier:
    """One row in the L1/L2/L3 support ownership table."""

    tier: str
    """L1 | L2 | L3"""

    ticket_type: str
    runbook_reference: str
    escalation_path: str


@dataclass
class ReadinessReport:
    """
    READINESS output (SKILL.md §Output Type 4).

    All six questions must be answered or explicitly marked UNKNOWN.
    Verdict must be one of three named values.
    Structural validation is performed by validator.validate_readiness_report().
    """

    request_type: RequestType = RequestType.READINESS

    operational_summary: str = ""
    """One sentence per: architecture / deployment / rollback / monitoring /
    incident response / cost / cost guardrails."""

    answers: list[ReadinessAnswer] = field(default_factory=list)
    """Six answers in fixed order (enforced by validator)."""

    support_ownership: list[SupportTier] = field(default_factory=list)
    """L1/L2/L3 table."""

    maturity_gaps: list[str] = field(default_factory=list)
    """Bulleted list; each gap includes a recommended next action."""

    verdict: str = ReadinessVerdict.NOT_READY.value
    """
    Exactly one of: Ready / Ready with Mitigations / Not Ready.
    No gradational language.
    """

    next_actions: list[str] = field(default_factory=list)
    """Maximum five bullets; each actionable and owner-named."""
