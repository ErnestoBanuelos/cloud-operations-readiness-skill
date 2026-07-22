"""
parser.py — Input parsing for the Reference Engine v0.1.

Parses raw text and dictionary inputs into lightweight input objects that
the engine (future katas) can process.

Design constraints
------------------
- This module contains NO analysis logic.
- Parsers extract structure from raw input; they do not interpret it.
- All parsers are pure functions (no I/O, no side effects).
- When a required field cannot be extracted, the parser returns None or
  the UNKNOWN sentinel.  It never fabricates values.

v0.1 scope
----------
In v0.1 only structural scaffolding is implemented.  Parse functions
accept raw text and return typed containers.  The containers are empty
or minimally populated; full extraction is a future kata concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from readiness_engine.models import UNKNOWN

# ---------------------------------------------------------------------------
# Input containers
# ---------------------------------------------------------------------------


@dataclass
class RawDiagnosisInput:
    """
    Structured container for diagnosis input (SKILL.md §Inputs).

    Fields populated by parse_diagnosis_input().
    """

    raw_text: str
    """The original unmodified input text."""

    pod_name: str = UNKNOWN
    """Pod name extracted from kubectl output, if detectable."""

    namespace: str = UNKNOWN
    """Kubernetes namespace, if detectable."""

    restart_count: int | None = None
    """Number of container restarts, if present in describe output."""

    termination_reason: str = UNKNOWN
    """Last termination reason (e.g. OOMKilled), if present."""

    events: list[str] = field(default_factory=list)
    """Raw event lines extracted from kubectl get events output."""

    log_lines: list[str] = field(default_factory=list)
    """Raw log lines from kubectl logs output."""


@dataclass
class RawAuditInput:
    """
    Structured container for audit input (SKILL.md §Inputs).

    Fields populated by parse_audit_input().
    """

    raw_text: str
    """The original unmodified input text (YAML manifest or workflow)."""

    input_kind: str = UNKNOWN
    """Kubernetes resource kind detected in the manifest, if any."""

    has_image_tag_latest: bool = False
    """True if the manifest contains an image reference ending in ':latest'."""

    has_security_context: bool = False
    """True if a securityContext block is detected."""

    has_resource_limits: bool = False
    """True if resources.limits is detected."""

    has_liveness_probe: bool = False
    """True if livenessProbe is detected."""

    has_readiness_probe: bool = False
    """True if readinessProbe is detected."""


@dataclass
class RawCostInput:
    """
    Structured container for cost input (SKILL.md §Inputs).

    Fields populated by parse_cost_input().
    """

    raw_text: str
    """The original unmodified input text."""

    cloud_rent: float | None = None
    """Cloud infrastructure monthly cost, if provided."""

    ai_calls_per_month: int | None = None
    """Number of AI API calls per month, if provided."""

    input_tokens_per_call: int | None = None
    """Average input tokens per AI call, if provided."""

    output_tokens_per_call: int | None = None
    """Average output tokens per AI call, if provided."""

    price_per_1m_input: float | None = None
    """Price per 1M input tokens, if provided."""

    price_per_1m_output: float | None = None
    """Price per 1M output tokens, if provided."""


@dataclass
class RawReadinessInput:
    """
    Structured container for readiness review input (SKILL.md §Inputs).

    Fields populated by parse_readiness_input().
    """

    raw_text: str
    """The original unmodified input text."""

    artefact_files: list[str] = field(default_factory=list)
    """Paths or names of provided artefact files (01-06)."""

    service_name: str = UNKNOWN
    """Service name extracted from artefacts, if detectable."""


# ---------------------------------------------------------------------------
# Parse functions
# ---------------------------------------------------------------------------


def parse_diagnosis_input(text: str) -> RawDiagnosisInput:
    """
    Parse raw kubectl / log / incident text into a RawDiagnosisInput.

    v0.1: Returns a container with raw_text populated.
    Extraction of individual fields is implemented in future katas.
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_diagnosis_input expects str; got {type(text).__name__}")
    return RawDiagnosisInput(raw_text=text.strip())


def parse_audit_input(text: str) -> RawAuditInput:
    """
    Parse a raw Kubernetes manifest or GitHub Actions workflow into RawAuditInput.

    v0.1: Detects a small number of surface-level signals as a structural
    scaffold.  Full field extraction is a future kata concern.
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_audit_input expects str; got {type(text).__name__}")

    stripped = text.strip()
    result = RawAuditInput(raw_text=stripped)

    # Minimal surface extraction — no logic, just presence detection.
    lower = stripped.lower()
    result.has_image_tag_latest = ":latest" in lower
    result.has_security_context = "securitycontext:" in lower
    result.has_resource_limits = "limits:" in lower
    result.has_liveness_probe = "livenessprobe:" in lower
    result.has_readiness_probe = "readinessprobe:" in lower

    # Detect resource kind
    for kind in (
        "Deployment",
        "Service",
        "ServiceAccount",
        "PodDisruptionBudget",
        "NetworkPolicy",
        "Workflow",
    ):
        if f"kind: {kind}" in stripped or f"kind: {kind.lower()}" in lower:
            result.input_kind = kind
            break

    return result


def parse_cost_input(data: dict[str, Any] | str) -> RawCostInput:
    """
    Parse a cost input dictionary or text into RawCostInput.

    Accepts either:
    - A dictionary with named keys (preferred for programmatic use).
    - A raw text string (future kata will extract numbers from prose).

    v0.1: When *data* is a dict, known keys are extracted directly.
    When *data* is a string, returns a container with only raw_text populated.
    """
    if isinstance(data, str):
        return RawCostInput(raw_text=data.strip())

    if not isinstance(data, dict):
        raise TypeError(f"parse_cost_input expects dict or str; got {type(data).__name__}")

    def _float_or_none(key: str) -> float | None:
        val = data.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    def _int_or_none(key: str) -> int | None:
        val = data.get(key)
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    raw_text = str(data)
    return RawCostInput(
        raw_text=raw_text,
        cloud_rent=_float_or_none("cloud_rent"),
        ai_calls_per_month=_int_or_none("ai_calls_per_month"),
        input_tokens_per_call=_int_or_none("input_tokens_per_call"),
        output_tokens_per_call=_int_or_none("output_tokens_per_call"),
        price_per_1m_input=_float_or_none("price_per_1m_input"),
        price_per_1m_output=_float_or_none("price_per_1m_output"),
    )


def parse_readiness_input(text: str) -> RawReadinessInput:
    """
    Parse a readiness review input into RawReadinessInput.

    v0.1: Returns a container with raw_text populated.
    Extraction of individual artefact references is a future kata concern.
    """
    if not isinstance(text, str):
        raise TypeError(f"parse_readiness_input expects str; got {type(text).__name__}")
    return RawReadinessInput(raw_text=text.strip())
