"""
validator.py — Structural validation of report outputs.

Validates that a produced report satisfies the invariants defined in SKILL.md
and enforced by CLAUDE.md.  Every rule here is traceable to an explicit
specification requirement.

Validation is intentionally separate from report construction so that:
  1. Tests can validate reports independently of the builders that produce them.
  2. Future kata implementations can be validated against the same rules.
  3. CI can run validate() against any report object without knowing how it was built.

All validators return a ValidationResult.  The caller decides whether to
raise, log, or surface the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from readiness_engine.models import (
    ALERT_THRESHOLD_CEILING_MULTIPLIER,
    AUDIT_CHECKLIST_SIZE,
    HARD_CAP_FLOOR_MULTIPLIER,
    HYPOTHESIS_COUNT,
    READINESS_QUESTION_COUNT,
    UNKNOWN,
    AuditStatus,
    ReadinessVerdict,
)

# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """The outcome of a single validation pass."""

    passed: bool = True
    violations: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        """Record a violation and mark this result as failed."""
        self.passed = False
        self.violations.append(message)

    def merge(self, other: ValidationResult) -> None:
        """Merge *other* into this result."""
        if not other.passed:
            self.passed = False
        self.violations.extend(other.violations)

    def __bool__(self) -> bool:
        return self.passed


# ---------------------------------------------------------------------------
# Diagnosis validators
# ---------------------------------------------------------------------------


def validate_hypothesis_count(hypotheses: list[Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 1: Produce exactly three hypotheses.

    Traceable to: SKILL.md Rule "Produce exactly three hypotheses. Never fewer, never more."
    """
    result = ValidationResult()
    count = len(hypotheses)
    if count != HYPOTHESIS_COUNT:
        result.fail(f"Diagnosis must contain exactly {HYPOTHESIS_COUNT} hypotheses; found {count}.")
    return result


def validate_hypothesis_structure(hypothesis: dict[str, Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 1: Each hypothesis must contain:
        - confidence level (%)
        - evidence for
        - evidence against
        - one read-only verification command
    """
    result = ValidationResult()
    required_keys = {
        "rank",
        "confidence_pct",
        "evidence_for",
        "evidence_against",
        "verification_command",
    }
    missing = required_keys - hypothesis.keys()
    if missing:
        result.fail(f"Hypothesis is missing required fields: {sorted(missing)}.")
    # Confidence must be a number in range 0-100
    confidence = hypothesis.get("confidence_pct")
    if confidence is not None:
        if not isinstance(confidence, (int, float)):
            result.fail("Hypothesis confidence_pct must be a number.")
        elif not (0 <= float(confidence) <= 100):
            result.fail(f"Hypothesis confidence_pct must be in range [0, 100]; got {confidence}.")
    return result


# ---------------------------------------------------------------------------
# Audit validators
# ---------------------------------------------------------------------------


def validate_audit_checklist_completeness(items: list[Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 2: All 12 checklist items must be evaluated.

    Traceable to: CLAUDE.md Rule 5 "Audit checklist is fixed at 12 items.
    Evaluate all 12. Never skip or reorder."
    """
    result = ValidationResult()
    count = len(items)
    if count != AUDIT_CHECKLIST_SIZE:
        result.fail(
            f"Audit must evaluate exactly {AUDIT_CHECKLIST_SIZE} checklist items; found {count}."
        )
    # Verify items are in order
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        expected_number = idx + 1
        actual_number = item.get("number")
        if actual_number != expected_number:
            result.fail(
                f"Checklist item at position {idx} has number {actual_number!r}; "
                f"expected {expected_number}. Items must not be reordered."
            )
    return result


def validate_audit_item_status(item: dict[str, Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 2: Status must be PASS / FAIL / PARTIAL / NOT APPLICABLE.

    No gradational language.  No other values are permitted.
    """
    result = ValidationResult()
    status = item.get("status")
    valid_statuses = {s.value for s in AuditStatus}
    if status not in valid_statuses:
        result.fail(
            f"Audit item {item.get('number', '?')!r} has invalid status {status!r}. "
            f"Permitted values: {sorted(valid_statuses)}."
        )
    return result


# ---------------------------------------------------------------------------
# Cost validators
# ---------------------------------------------------------------------------


def validate_cost_line_items(cost_report: dict[str, Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 3: Cloud rent and AI meter must always be reported
    as separate line items with distinct owners.

    Traceable to: CLAUDE.md Rule 6.
    """
    result = ValidationResult()
    if "cloud_rent" not in cost_report:
        result.fail("Cost report is missing 'cloud_rent' line item.")
    if "ai_meter" not in cost_report:
        result.fail("Cost report is missing 'ai_meter' line item.")
    return result


def validate_cost_cap(cost_report: dict[str, Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 3:
        - Hard cap >= 120% of baseline monthly spend.
        - Alert threshold <= 75% of hard cap.

    Traceable to: CLAUDE.md Rule 6; SKILL.md §Output Type 3 Rules.
    """
    result = ValidationResult()

    baseline: Any = cost_report.get("monthly_total")
    hard_cap: Any = cost_report.get("hard_cap")
    alert_threshold: Any = cost_report.get("alert_threshold")

    if baseline is None:
        result.fail("Cost report is missing 'monthly_total'.")
        return result  # Cannot validate cap without baseline

    if hard_cap is None:
        result.fail("Cost report is missing 'hard_cap'.")
    else:
        floor = float(baseline) * HARD_CAP_FLOOR_MULTIPLIER
        if float(hard_cap) < floor:
            result.fail(
                f"Hard cap ({hard_cap}) must be >= {HARD_CAP_FLOOR_MULTIPLIER * 100:.0f}% "
                f"of monthly_total ({baseline}); minimum value is {floor:.2f}."
            )

    if alert_threshold is None:
        result.fail("Cost report is missing 'alert_threshold'.")
    elif hard_cap is not None:
        ceiling = float(hard_cap) * ALERT_THRESHOLD_CEILING_MULTIPLIER
        if float(alert_threshold) > ceiling:
            result.fail(
                f"Alert threshold ({alert_threshold}) must be <= "
                f"{ALERT_THRESHOLD_CEILING_MULTIPLIER * 100:.0f}% of hard_cap ({hard_cap}); "
                f"maximum value is {ceiling:.2f}."
            )

    return result


# ---------------------------------------------------------------------------
# Readiness validators
# ---------------------------------------------------------------------------


def validate_readiness_question_count(answers: list[Any]) -> ValidationResult:
    """
    SKILL.md §Output Type 4: All six readiness questions must be answered.

    Traceable to: CLAUDE.md Rule 8 "Six readiness questions are fixed and evaluated in order."
    """
    result = ValidationResult()
    count = len(answers)
    if count != READINESS_QUESTION_COUNT:
        result.fail(
            f"Readiness review must answer exactly {READINESS_QUESTION_COUNT} questions; "
            f"found {count}."
        )
    return result


def validate_readiness_verdict(verdict: str | None) -> ValidationResult:
    """
    SKILL.md §Output Type 4: Verdict must be exactly one of the three named values.

    Traceable to: CLAUDE.md Rule 7 "Readiness verdicts are one of three named values."
    """
    result = ValidationResult()
    valid_verdicts = {v.value for v in ReadinessVerdict}
    if verdict not in valid_verdicts:
        result.fail(
            f"Readiness verdict {verdict!r} is not a permitted value. "
            f"Permitted values: {sorted(valid_verdicts)}."
        )
    return result


def validate_unknown_not_fabricated(answers: list[dict[str, Any]]) -> ValidationResult:
    """
    SKILL.md §Inputs; CLAUDE.md Rule 3:
    When information is absent the exact string UNKNOWN must be used.
    Fabricated values are a specification violation.

    Checks that answers with status="UNKNOWN" also set answer to the UNKNOWN sentinel.
    """
    result = ValidationResult()
    for idx, answer in enumerate(answers):
        status = answer.get("status")
        answer_text = answer.get("answer", "")
        if status == "UNKNOWN" and answer_text != UNKNOWN:
            result.fail(
                f"Readiness answer at position {idx} has status=UNKNOWN but "
                f"answer text is {answer_text!r}; expected {UNKNOWN!r}."
            )
    return result


# ---------------------------------------------------------------------------
# Aggregate validators
# ---------------------------------------------------------------------------


def validate_diagnosis_report(report: dict[str, Any]) -> ValidationResult:
    """Run all diagnosis validators against *report*."""
    result = ValidationResult()
    hypotheses: list[Any] = report.get("hypotheses") or []
    result.merge(validate_hypothesis_count(hypotheses))
    for hyp in hypotheses:
        if isinstance(hyp, dict):
            result.merge(validate_hypothesis_structure(hyp))
    return result


def validate_audit_report(report: dict[str, Any]) -> ValidationResult:
    """Run all audit validators against *report*."""
    result = ValidationResult()
    items: list[Any] = report.get("checklist") or []
    result.merge(validate_audit_checklist_completeness(items))
    for item in items:
        if isinstance(item, dict):
            result.merge(validate_audit_item_status(item))
    return result


def validate_cost_report(report: dict[str, Any]) -> ValidationResult:
    """Run all cost validators against *report*."""
    result = ValidationResult()
    result.merge(validate_cost_line_items(report))
    result.merge(validate_cost_cap(report))
    return result


def validate_readiness_report(report: dict[str, Any]) -> ValidationResult:
    """Run all readiness validators against *report*."""
    result = ValidationResult()
    answers: list[Any] = report.get("answers") or []
    result.merge(validate_readiness_question_count(answers))
    verdict = report.get("verdict")
    result.merge(validate_readiness_verdict(verdict if isinstance(verdict, str) else None))
    result.merge(validate_unknown_not_fabricated([a for a in answers if isinstance(a, dict)]))
    return result
