"""
classifier.py — Request classification engine.

Classifies a free-text input string into one of the four RequestType values
defined in SKILL.md §Outputs.

Design constraints
------------------
- This module contains NO I/O.
- Classification is based purely on keyword heuristics in v0.1.
  Future katas may introduce model-based classification without changing
  the public contract (classify() always returns RequestType | None).
- No business logic is implemented here beyond classification.
  The caller is responsible for routing to the appropriate handler.

Classification rules (v0.1 — keyword heuristics)
-------------------------------------------------
DIAGNOSIS   : input contains log / kubectl signals (OOMKill, CrashLoopBackOff,
              Error, Warning, "kubectl describe", "kubectl get events", etc.)
AUDIT       : input contains manifest signals (YAML Kubernetes kinds:
              Deployment, Service, apiVersion, image:, securityContext, etc.)
COST        : input contains cost signals (token, cost, $, price, cap, meter, LLM)
READINESS   : input contains readiness signals ("readiness review", "go/no-go",
              "operational readiness", "artefact set", "01-stack-map", etc.)

When signals from multiple categories appear, DIAGNOSIS takes precedence over
AUDIT, which takes precedence over COST, which takes precedence over READINESS.
This priority order reflects the most common multi-signal ambiguity in practice.

If no signal is detected the function returns None and the caller must handle
the ambiguous case explicitly.
"""

from __future__ import annotations

import re

from readiness_engine.models import RequestType

# ---------------------------------------------------------------------------
# Signal pattern tables
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

    return None
