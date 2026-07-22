"""
readiness_engine — Reference Implementation v0.1

A canonical implementation of the Cloud Operations Readiness Skill specification.

This package demonstrates one correct implementation of the four output types
defined in SKILL.md:

    DIAGNOSIS   — three ranked hypotheses from logs / kubectl output
    AUDIT       — 12-item deployment and IaC checklist
    COST        — cloud rent vs AI meter split with cap validation
    READINESS   — six-question go/no-go review

The specification (SKILL.md) is the single source of truth.
This implementation must never introduce behaviour absent from the specification.

Module responsibilities
-----------------------
models      — Domain types (enumerations, dataclasses).  No logic.
classifier  — Classify a free-text input into one of the four request types.
validator   — Validate that a report satisfies the structural rules in SKILL.md.
report      — Dataclasses that represent each of the four output types.
parser      — Parse raw text / dict inputs into structured input objects.
"""

__version__ = "0.1.0"
__spec_version__ = "1.0.0"  # SKILL.md version this release targets

# Public surface — intentionally minimal for v0.1
from readiness_engine.models import (
    AuditStatus,
    ReadinessVerdict,
    RequestType,
    RiskLevel,
)

__all__ = [
    "AuditStatus",
    "ReadinessVerdict",
    "RequestType",
    "RiskLevel",
    "__spec_version__",
    "__version__",
]
