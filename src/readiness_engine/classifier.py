"""
classifier.py — Request classification and risk classification engine.

This module contains two public entry points:

1. ``classify(text)`` — Classifies a free-text input string into one of the
   four RequestType values defined in SKILL.md §Outputs.

2. ``classify_risk(findings)`` — Classifies a list of drift Findings into a
   single RiskLevel value.  This is the Risk Classification Engine required by
   Sprint 2 of the Reference Engine implementation.

Design constraints
------------------
- This module contains NO I/O.
- No parsing, no report generation.
- No file I/O, no kubectl, no subprocess, no networking, no AI calls.
- Every rule is evaluated in deterministic order.
- Every decision point includes a traceability comment.
- If the Specification is ambiguous the function raises NotImplementedError
  with a TODO comment referencing the missing requirement.

=============================================================================
classify() — Request classification (v0.1 keyword heuristics)
=============================================================================

Classification rules:
DIAGNOSIS   : log / kubectl signals (OOMKill, CrashLoopBackOff, etc.)
AUDIT       : manifest signals (Deployment, Service, securityContext, etc.)
COST        : cost signals (token, $, price, hard cap, AI meter, etc.)
READINESS   : readiness signals ("readiness review", "go/no-go", etc.)

When signals from multiple categories appear, DIAGNOSIS takes precedence over
AUDIT, which takes precedence over COST, which takes precedence over READINESS.

If no signal is detected the function returns None.

=============================================================================
classify_risk() — Risk Classification Engine
=============================================================================

Implements the five-priority evaluation table from:
  specs/operational-drift-analysis/spec.md §1.2 Step 6
  "Risk Classification Logic — Evaluation Order and Interface Contract"
  changes/operational-drift-risk-model/delta.md §A-1 / M-1

Evaluation order (highest priority first — first match wins):

  Priority 1 (CRITICAL): A write-command artefact is detected in State B
      that was absent in State A.
      Traceable to: spec.md §1.2 Step 6, Priority 1 row; delta.md §A-1.

  Priority 2 (CRITICAL): The Deployment replicas value in State B is less
      than the minAvailable value declared in the PodDisruptionBudget in
      State A.  Applies ONLY when a PDB is present in State A.  When no PDB
      is present in State A this condition falls through to the HIGH
      evaluation.
      Traceable to: spec.md §1.2 Step 6, Priority 2 row; delta.md §A-1;
      AUDIT-ODA-01 INCORPORATE.

  Priority 3 (HIGH): Removal of a safety-relevant component (PDB,
      securityContext, readiness probe); any security context field modified;
      image tag changed to a mutable reference.
      Traceable to: spec.md §1.2 Step 6, Priority 3 row.

  Priority 4 (MEDIUM): At least one modification to a non-safety field; or
      at least one added component with undetermined ownership.
      Traceable to: spec.md §1.2 Step 6, Priority 4 row.

  Priority 5 (LOW): All other cases.
      Traceable to: spec.md §1.2 Step 6, Priority 5 row.

Severity ordering: LOW < MEDIUM < HIGH < CRITICAL
  Traceable to: spec.md §1.2 "Severity ordering" note; delta.md §M-1.

Interface contract (Seam 1 from tasks.md):
  risk_level:      RiskLevel  — exactly one of LOW / MEDIUM / HIGH / CRITICAL
  critical_active: bool       — True if and only if risk_level == CRITICAL
  (The caller may compute critical_active as ``result == RiskLevel.CRITICAL``.)
  Traceable to: spec.md §1.2 "Interface contract emitted by this logic";
  changes/operational-drift-risk-model/plan.md — Component 1.

Finding category and risk_level interpretation
----------------------------------------------
The Risk Classification Engine reads Finding.category and Finding.risk_level
directly.  It does NOT re-evaluate artefact text.  The detection layer
(spec.md §1.2 Steps 2-4) is responsible for populating those fields; this
engine only aggregates them.
  Traceable to: spec.md §1.2 "All downstream output sections … consume only
  risk_level, critical_active, and rationale.  No downstream section
  re-evaluates artefacts or findings independently."

Write-command detection signal
-------------------------------
A Finding is treated as a write-command finding when its ``category`` field is
``"write_command_detected"``.  This category is set by the detection layer when
it identifies a write-command artefact in State B that was absent in State A
(spec.md §3.1 error WRITE_COMMAND_DETECTED; delta.md §A-1 Priority 1 trigger).
  Traceable to: spec.md §1.2 Step 6, Priority 1; spec.md §3.1.

PDB / replica-count signal
---------------------------
A Finding triggers Priority 2 (CRITICAL) when:
  - Its ``category`` is ``"pdb_replica_violation"``
This category is set by the detection layer when:
  - A PDB is present in State A (artefact read by the detection layer), AND
  - The Deployment replicas value in State B < minAvailable from that PDB.
When no PDB is present in State A the detection layer MUST NOT emit a
``pdb_replica_violation`` finding; a plain ``"modified"`` or ``"removed"``
finding for the replica count is emitted instead (classifies as HIGH or lower).
  Traceable to: spec.md §1.2 Step 6, Priority 2; delta.md §A-1; AUDIT-ODA-01.

Safety-relevant component signal (HIGH)
----------------------------------------
A Finding triggers HIGH (Priority 3) when its ``risk_level`` field is already
set to ``RiskLevel.HIGH`` by the detection layer.  The detection layer assigns
HIGH to:
  - Removal of a safety-relevant component (PDB, securityContext, readiness
    probe).
  - Any security context field modified.
  - Image tag changed to a mutable reference (e.g. "latest").
  Traceable to: spec.md §1.2 Step 6, Priority 3.

MEDIUM signal
-------------
A Finding triggers MEDIUM (Priority 4) when its ``risk_level`` field is set to
``RiskLevel.MEDIUM`` by the detection layer.  The detection layer assigns MEDIUM
to:
  - Modification to a non-safety field.
  - Added component with undetermined ownership (``owner == UNKNOWN``).
  Traceable to: spec.md §1.2 Step 6, Priority 4.

LOW (default)
-------------
When no finding meets any of the above trigger conditions the result is LOW.
  Traceable to: spec.md §1.2 Step 6, Priority 5.
"""

from __future__ import annotations

import re

from readiness_engine.models import UNKNOWN, Finding, RequestType, RiskLevel

# ---------------------------------------------------------------------------
# Signal pattern tables (classify — request type classification)
# ---------------------------------------------------------------------------

_DIAGNOSIS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bOOMKill(ed)?\b",
        r"\bCrashLoopBackOff\b",
        r"\bkubectl\s+(describe|get\s+events|logs|top)\b",
        r"\bpod\s+(restarted|failed|terminated|evicted)\b",
        r"\bBack-off\s+restarting\b",
        r"\bcontainer\s+died\b",
        r"\bkubectl\s+get\s+pods\b",
        r"\bkubectl\s+describe\s+pod\b",
        r"\bError\s+from\s+server\b",
        r"\bWarning\s+\w+\b",
        r"\bincident\b",
        r"\broot\s+cause\b",
        r"\bhypothes(is|es)\b",
        r"\blog\s+output\b",
        r"\bpod\s+output\b",
        r"\bcrash\b",
    ]
)

_AUDIT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bapiVersion:\s*apps/v1\b",
        r"\bkind:\s*(Deployment|Service|ServiceAccount|PodDisruptionBudget|NetworkPolicy)\b",
        r"\bsecurityContext:\b",
        r"\breadinessProbe:\b",
        r"\blivenessProbe:\b",
        r"\bstartupProbe:\b",
        r"\bresources:\s*\n",
        r"\bimage:\s*\S+",
        r"\baudit\s+(this|the|manifest|yaml|deployment|workflow)\b",
        r"\bmanifest\b",
        r"\bkubernetes\s+manifest\b",
        r"\bIaC\b",
        r"\bGitHub\s+Actions\s+(workflow|pipeline)\b",
        r"\bchecklist\b",
        r"\bproduction\s+readiness\s+audit\b",
    ]
)

_COST_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\btoken\s+(volume|count|cost|price)\b",
        r"\$[\d,]+",
        r"\bcost\s+(estimate|review|split|cap|report)\b",
        r"\bAI\s+meter\b",
        r"\bcloud\s+rent\b",
        r"\bhard\s+cap\b",
        r"\balert\s+threshold\b",
        r"\bLLM\s+cost\b",
        r"\bprice\s+per\s+1M\b",
        r"\bmonthly\s+(cost|spend|total)\b",
        r"\bgateway\s+cap\b",
        r"\bFinOps\b",
    ]
)

_READINESS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\boperational\s+readiness\s+review\b",
        r"\bgo\s*/\s*no.?go\b",
        r"\breadiness\s+review\b",
        r"\b01.stack.map\b",
        r"\bartefact\s+set\b",
        r"\bsix\s+(artefacts?|documents?|files?)\b",
        r"\bready\s+to\s+ship\b",
        r"\breadiness\s+verdict\b",
        r"\bReadiness\s+Questions?\b",
        r"\bmaturity\s+gaps?\b",
        r"\bORR\b",
    ]
)


# Priority order: later entries override earlier.  Highest priority = first evaluated.
_PRIORITY_TABLE: tuple[tuple[RequestType, tuple[re.Pattern[str], ...]], ...] = (
    (RequestType.DIAGNOSIS, _DIAGNOSIS_PATTERNS),
    (RequestType.AUDIT, _AUDIT_PATTERNS),
    (RequestType.COST, _COST_PATTERNS),
    (RequestType.READINESS, _READINESS_PATTERNS),
)


def _count_matches(text: str, patterns: tuple[re.Pattern[str], ...]) -> int:
    """Return the number of distinct patterns that match anywhere in *text*."""
    return sum(1 for p in patterns if p.search(text))


def classify(text: str) -> RequestType | None:
    """
    Classify *text* into one of the four RequestType values.

    Returns None when no signal is detected with sufficient confidence.
    The caller must handle the None case explicitly (e.g. ask for clarification).

    Parameters
    ----------
    text:
        Raw input text from the engineer.

    Returns
    -------
    RequestType | None
        The classified request type, or None if classification is ambiguous.
    """
    if not text or not text.strip():
        return None

    scores: dict[RequestType, int] = {}
    for request_type, patterns in _PRIORITY_TABLE:
        count = _count_matches(text, patterns)
        if count > 0:
            scores[request_type] = count

    if not scores:
        return None

    # Return the highest-priority type that has any signal match.
    # Priority order is the primary key (DIAGNOSIS > AUDIT > COST > READINESS).
    # Match count is used only as a secondary tie-breaker between types at the
    # same priority level (which cannot happen in the current table, but is
    # kept here for correctness if the table is extended).
    priority_order = [rt for rt, _ in _PRIORITY_TABLE]
    for request_type in priority_order:
        if request_type in scores:
            return request_type

    return None  # pragma: no cover


# ---------------------------------------------------------------------------
# Risk Classification Engine
# ---------------------------------------------------------------------------
# Traceable to: specs/operational-drift-analysis/spec.md §1.2 Step 6
# "Risk Classification Logic — Evaluation Order and Interface Contract"
# and changes/operational-drift-risk-model/delta.md §A-1 / M-1.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Special category tokens
#
# These category strings are set by the detection layer (spec.md §1.2
# Steps 2-4) to signal conditions that the risk engine must evaluate at
# Priority 1 and Priority 2.  Using named constants avoids silent string
# typos and makes the traceability comment reviewable.
# ---------------------------------------------------------------------------

#: Category token for Priority 1 (CRITICAL) trigger.
#: Set by the detection layer when a write-command artefact is found in
#: State B that was absent in State A.
#: Traceable to: spec.md §1.2 Step 6 Priority 1; spec.md §3.1
#: WRITE_COMMAND_DETECTED error; delta.md §A-1.
CATEGORY_WRITE_COMMAND: str = "write_command_detected"

#: Category token for Priority 2 (CRITICAL) trigger.
#: Set by the detection layer ONLY when a PDB is present in State A AND
#: the Deployment replica count in State B is less than the PDB's
#: minAvailable value.  MUST NOT be set when no PDB is present in State A.
#: Traceable to: spec.md §1.2 Step 6 Priority 2; AUDIT-ODA-01 INCORPORATE;
#: delta.md §A-1; changes/operational-drift-risk-model/plan.md Component 1.
CATEGORY_PDB_REPLICA_VIOLATION: str = "pdb_replica_violation"


def classify_risk(findings: list[Finding]) -> RiskLevel:
    """
    Classify a list of drift findings into a single RiskLevel.

    This is the Risk Classification Engine for the Operational Drift Analysis
    capability.  It implements the five-priority ordered evaluation table
    defined in the specification.

    The first matching condition determines the classification.  No lower-
    priority condition is evaluated once a match is found.  Rules are evaluated
    in deterministic, descending priority order.

    Parameters
    ----------
    findings:
        The complete list of drift findings produced by the detection layer
        (spec.md §1.2 Steps 2-4).  May be empty (produces LOW — all-clear).

    Returns
    -------
    RiskLevel
        Exactly one of: LOW, MEDIUM, HIGH, CRITICAL.

    Raises
    ------
    NotImplementedError
        # TODO: If a future spec version introduces a fifth risk level or a
        # new trigger condition not covered by the current five-priority table,
        # this function must be updated.  Any ambiguity in spec §1.2 Step 6
        # that cannot be resolved from the current text should be raised here
        # with a reference to the missing requirement.

    Notes
    -----
    Interface contract (Seam 1 — tasks.md):
        risk_level:      one of LOW / MEDIUM / HIGH / CRITICAL
        critical_active: caller computes as ``result == RiskLevel.CRITICAL``
        rationale:       not returned here; the caller's output formatter
                         is responsible for composing the one-sentence
                         rationale string (spec.md §1.2 interface contract).
    Traceable to:
        specs/operational-drift-analysis/spec.md §1.2 Step 6
        changes/operational-drift-risk-model/delta.md §A-1 / M-1
        changes/operational-drift-risk-model/plan.md — Component 1
        changes/operational-drift-risk-model/tasks.md — T1
    """
    # -----------------------------------------------------------------------
    # Empty input: no findings → no drift → LOW
    # Traceable to: spec.md §1.2 Step 6 Priority 5 "All other cases."
    # A drift set with zero findings produces the clean-report path (AC-4).
    # -----------------------------------------------------------------------
    if not findings:
        return RiskLevel.LOW

    # -----------------------------------------------------------------------
    # Priority 1 — CRITICAL: write-command artefact detected in State B
    # absent from State A.
    #
    # Trigger condition: any Finding whose category is CATEGORY_WRITE_COMMAND.
    # The detection layer sets this category when it encounters a write command
    # (kubectl apply, kubectl delete, terraform apply, etc.) in a State B
    # artefact that was not present in State A.
    #
    # First matching condition wins; evaluation stops here on a match.
    #
    # Traceable to:
    #   spec.md §1.2 Step 6, Priority 1 row:
    #   "A write-command artefact is detected in State B that was absent
    #   in State A."
    #   delta.md §A-1 (CRITICAL severity formalised).
    #   spec.md §3.1 WRITE_COMMAND_DETECTED error description.
    # -----------------------------------------------------------------------
    for finding in findings:
        if finding.category == CATEGORY_WRITE_COMMAND:
            return RiskLevel.CRITICAL

    # -----------------------------------------------------------------------
    # Priority 2 — CRITICAL: replica count in State B < minAvailable from
    # PDB in State A.
    #
    # Trigger condition: any Finding whose category is
    # CATEGORY_PDB_REPLICA_VIOLATION.
    #
    # IMPORTANT boundary condition (PDB-presence carve-out):
    # This trigger ONLY applies when a PDB is present in State A.  When no
    # PDB is present in State A, the detection layer MUST NOT emit a
    # pdb_replica_violation finding — it emits a plain modified/removed
    # finding instead, which routes to Priority 3 (HIGH) or lower.
    # The risk engine itself does not query live state; it trusts the
    # detection layer to honour this carve-out.
    #
    # Traceable to:
    #   spec.md §1.2 Step 6, Priority 2 row:
    #   "The Deployment replicas value in State B is less than the
    #   minAvailable value declared in the PodDisruptionBudget in State A.
    #   This trigger applies only when a PodDisruptionBudget is present in
    #   State A."
    #   AUDIT-ODA-01 INCORPORATE (spec.md §1.2 Step 6 CRITICAL row update).
    #   delta.md §A-1; changes/operational-drift-risk-model/plan.md
    #   Component 1 — "guarded by PDB-presence check (no PDB → HIGH)".
    # -----------------------------------------------------------------------
    for finding in findings:
        if finding.category == CATEGORY_PDB_REPLICA_VIOLATION:
            return RiskLevel.CRITICAL

    # -----------------------------------------------------------------------
    # Priority 3 — HIGH: safety-relevant removal, security context
    # modification, or image tag changed to mutable reference.
    #
    # Trigger condition: any Finding whose risk_level is RiskLevel.HIGH.
    # The detection layer assigns HIGH to:
    #   - Removal of a safety-relevant component (PDB, securityContext,
    #     readiness probe).
    #   - Any security context field modified.
    #   - Image tag changed to a mutable reference (e.g. "latest").
    #
    # Traceable to:
    #   spec.md §1.2 Step 6, Priority 3 row:
    #   "Removal of a safety-relevant component (PDB, securityContext,
    #   readiness probe); any security context field modified; image tag
    #   changed to a mutable reference."
    #   REFERENCE.md §Critical Findings (production blockers).
    # -----------------------------------------------------------------------
    for finding in findings:
        if finding.risk_level == RiskLevel.HIGH:
            return RiskLevel.HIGH

    # -----------------------------------------------------------------------
    # Priority 4 — MEDIUM: non-safety field modification or added component
    # with undetermined ownership.
    #
    # Trigger condition: any Finding whose risk_level is RiskLevel.MEDIUM,
    # OR any Finding that was added (category == "added") and has
    # undetermined ownership (owner == UNKNOWN sentinel).
    #
    # The spec defines two distinct MEDIUM sub-triggers:
    #   a) At least one modification to a non-safety field.
    #   b) At least one added component with undetermined ownership.
    # Both are captured here: sub-trigger (a) is covered by risk_level ==
    # MEDIUM; sub-trigger (b) is evaluated explicitly to catch "added"
    # findings that the detection layer may have assigned a lower risk_level
    # before the ownership is resolved.
    #
    # Traceable to:
    #   spec.md §1.2 Step 6, Priority 4 row:
    #   "At least one modification to a non-safety field; or at least one
    #   added component with undetermined ownership."
    #   spec.md §1.2 Step 2 (added component ownership labelling).
    #   CLAUDE.md Rule 3 (UNKNOWN sentinel).
    # -----------------------------------------------------------------------
    for finding in findings:
        # Sub-trigger (a): detection layer classified as MEDIUM
        if finding.risk_level == RiskLevel.MEDIUM:
            return RiskLevel.MEDIUM
        # Sub-trigger (b): added component with undetermined ownership
        if finding.category == "added" and finding.owner == UNKNOWN:
            return RiskLevel.MEDIUM

    # -----------------------------------------------------------------------
    # Priority 5 — LOW: all other cases.
    #
    # Reached when no finding matched Priorities 1-4.
    # This is the clean-report path: all changes are additive with no
    # safety-relevant removals and no modified security fields (AC-4).
    #
    # Traceable to:
    #   spec.md §1.2 Step 6, Priority 5 row: "All other cases."
    # -----------------------------------------------------------------------
    return RiskLevel.LOW
