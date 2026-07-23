# Seven-Lens Engineering Review

**Review ID:** T1  
**Kata:** K 5.D.9  
**Date:** 2026-07-22  
**Reviewer role:** Engineering Reviewer (Deep Engineering)  
**Review scope:** Sprint 1 + Sprint 2 implementation  
**Files under review:** `models.py`, `classifier.py`, `report.py`, `validator.py`, `tests/`  
**Review inputs:** `specs/operational-drift-analysis/spec.md` v1.0.1, `changes/operational-drift-risk-model/delta.md` v1.0.0, `changes/operational-drift-risk-model/plan.md` v1.0.0, `changes/operational-drift-risk-model/tasks.md` v1.0.0, `sessions/T1/session-log.md`, `specs/operational-drift-analysis/audit.md`

---

## Isolation Tier

**Tier C — Limited**

Implementation and review occurred inside the same engineering effort. The reviewer
has full knowledge of all design decisions made during Sprint 1 and Sprint 2. The
session log (`sessions/T1/session-log.md`) explicitly records this limitation:

> "This verification corresponds to Isolation Tier C because the implementation and
> verification occurred within the same engineering effort."

No claim of Tier A or Tier B isolation is made. A Tier A review would require a
reviewer who had no prior exposure to the implementation. That condition is not
satisfied here. This limitation is recorded honestly.

---

## Review Baseline

All three verification gates passed before this review was conducted:

| Gate | Tool | Result |
|---|---|---|
| Linting | `ruff check .` | PASS — 0 errors, 0 warnings |
| Type checking | `mypy src` | PASS — 0 issues in 6 source files |
| Unit tests | `pytest` | PASS — 242/242 passed |
| Coverage | `pytest --cov` | PASS — 97.08% (threshold: 90%) |

The review proceeds from a passing baseline. No defects were pre-existing in the
verification suite.

---

## Lens 1 — Behaviour Preservation

**Question:** Does the implementation preserve all behaviour required by the specification,
the brownfield delta, and the brownfield rules that existed before Sprint 2?

---

### Finding 1.1

**Severity:** major  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 317  
**Finding:** `classify_risk()` returns only `RiskLevel`. The specification interface
contract (`spec.md §1.2 Step 6`) defines three emitted fields:

```
risk_level:      "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
critical_active: boolean  — true if and only if risk_level == "CRITICAL"
rationale:       string   — one sentence citing the trigger condition
```

The function returns one field (`risk_level`). The `critical_active` boolean is
deferred to the caller. The `rationale` string is never produced by any code in this
module. The docstring acknowledges this:

> "rationale: not returned here; the caller's output formatter is responsible for
> composing the one-sentence rationale string."

The `tasks.md` Seam 1 contract explicitly includes `rationale`. `plan.md` Component 1
also lists `rationale` as a required output. Components 2 (Risk Level section
formatter) and 3 (Escalation Block Builder) are specified to consume `rationale`
from Component 1. Neither Component 2 nor Component 3 is implemented; this
limitation is acknowledged in the session log (T1 is the FIRST SLICE). However, the
interface contract is incomplete at the seam boundary even for T1 purposes. A
downstream implementation of Components 2 or 3 that consumes `classify_risk()` and
expects a `rationale` field would find none.

**Suggested fix:** Return a named tuple or small dataclass from `classify_risk()` that
bundles `risk_level`, `critical_active`, and `rationale`. Alternatively, document
explicitly in `tasks.md` that rationale production is deferred to a future task and
update Seam 1's contract to reflect the T1 scope. The current state leaves the seam
partially implemented without making the omission visible at the call site.

---

### Finding 1.2

**Severity:** minor  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 228  
**Finding:** The comment at line 228 reads:

```python
# Priority order: later entries override earlier.  Highest priority = first evaluated.
```

These two sub-clauses contradict each other. "Later entries override earlier" implies
that READINESS (last in the table) would be the highest priority. "Highest priority =
first evaluated" implies that DIAGNOSIS (first in the table) is the highest priority.
The implementation is correct — the `for request_type in priority_order` loop returns
the first matching type, making DIAGNOSIS the highest priority. The first sub-clause
is therefore incorrect.

**Suggested fix:** Replace with a single, unambiguous statement:

```python
# Evaluation order: DIAGNOSIS first (highest priority), READINESS last (lowest).
# The first type with any signal match is returned.
```

---

### Finding 1.3

**Severity:** nit  
**File:** `src/readiness_engine/__init__.py`  
**Line:** 30  
**Finding:** `__spec_version__ = "1.0.0"` does not match the current specification
version. The spec file header reads `Spec version: 1.0.1` (amended by AUDIT-ODA-01
and AUDIT-ODA-02). The delta targets version 1.1.0. The package tracks an outdated
version string.

**Suggested fix:** Update to `__spec_version__ = "1.0.1"` to match the current spec.
When spec v1.1.0 is issued (after approval gate T6), update to `"1.1.0"`.

---

**Lens 1 verdict:** Two substantive findings (1.1 major, 1.2 minor) and one tracking
nit. The core CRITICAL classification logic preserves all required behaviours. The
HIGH/CRITICAL boundary condition and PDB-presence carve-out are correctly implemented.
No regression on LOW, MEDIUM, or HIGH trigger paths was found.

---

## Lens 2 — Hidden Assumptions

**Question:** What assumptions are embedded in the implementation that are not
documented in the specification or visible at the module boundary?

---

### Finding 2.1

**Severity:** major  
**File:** `src/readiness_engine/validator.py`  
**Line:** 197  
**Finding:** `validate_cost_cap()` uses `monthly_total` (cloud rent + AI meter) as the
"baseline" for the 120% hard cap rule. The SKILL.md rule is:

> "Hard cap ≥ 120% of baseline."

The `artefacts/800-wide/05-cost-estimate.md` reference artefact defines "baseline" as
the AI meter spend alone ($15,000), not the grand total ($16,500). CLAUDE.md's
reference cost table annotates the $18,000 cap as "120% of baseline" where
baseline = $15,000 (AI meter).

Using `monthly_total` as baseline means the reference artefact's cost figures ($18,000
cap against $16,500 total) would fail the validator with:

```
Hard cap (18000.0) must be >= 120% of monthly_total (16500.0); minimum value is 19800.00.
```

This inconsistency was noted in the `test_validator.py` test comment at line 269–280,
which explicitly states "Per SKILL.md, hard cap >= 120% of 'current baseline spend'
(the monthly total)." The test acknowledges the discrepancy but treats the validator
implementation as authoritative rather than flagging the ambiguity for resolution.

The assumption that `baseline = monthly_total` is embedded in the validator without
any traceability comment to a specification decision. `run-log.md` RUN-005 and the
reference artefact both use `baseline = AI meter only`, which would fail the validator.

**Suggested fix:** Add a traceability comment to `validate_cost_cap()` that documents
the explicit definition of "baseline" used here. Raise the ambiguity with the product
owner for resolution before spec v1.1.0 is issued. The reference artefact and the
validator are currently inconsistent.

---

### Finding 2.2

**Severity:** major  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 467–473  
**Finding:** The Priority 4 MEDIUM check for `added` components with `UNKNOWN` owner
iterates the same `findings` list a third time (after Priority 1 and Priority 2 checks
have already iterated it). The combined Priority 3+4 loop structure hides an
assumption: a `Finding` with `risk_level=CRITICAL` but `category="removed"` (a
plain removed finding) will produce `RiskLevel.LOW`, not `RiskLevel.HIGH` or
`RiskLevel.CRITICAL`.

This occurs because:
- Priority 1: category is not `write_command_detected` → no match.
- Priority 2: category is not `pdb_replica_violation` → no match.
- Priority 3: `risk_level == RiskLevel.HIGH` → False (it's CRITICAL) → no match.
- Priority 4: `risk_level == RiskLevel.MEDIUM` → False → no match; category is
  `removed` not `added` → no match.
- Priority 5: returns `RiskLevel.LOW`.

The hidden assumption is that the detection layer will **never** produce a `Finding`
with `risk_level=CRITICAL` using a non-special category. This is documented in
comments but is not enforced by any type guard, assertion, or validation at the
`Finding` constructor. A future detection layer implementation that assigns
`risk_level=CRITICAL` to a plain `"removed"` finding would silently produce `LOW`.

**Suggested fix:** Either add a runtime assertion in `classify_risk()` that raises if
`risk_level == RiskLevel.CRITICAL` and the category is neither
`CATEGORY_WRITE_COMMAND` nor `CATEGORY_PDB_REPLICA_VIOLATION`, or add a validator
that checks this precondition. Alternatively, document this constraint explicitly in
`Finding`'s docstring as a class invariant.

---

### Finding 2.3

**Severity:** minor  
**File:** `src/readiness_engine/validator.py`  
**Line:** 126–128  
**Finding:** `validate_audit_checklist_completeness()` counts the number of items in
the list before checking their types. A list of 12 non-dict items passes the count
check and silently skips all ordering checks (the `if not isinstance(item, dict):
continue` guard). The function returns `passed=True` for a list of 12 arbitrary
non-dict objects.

This is an undocumented permissiveness: the function name and docstring claim to
validate "completeness" but it accepts structurally invalid input without error.

**Suggested fix:** Consider failing explicitly when non-dict items are encountered, or
document the permissive behaviour and its intended use case (e.g., "accepts any
sequence of 12 items; type checking is the caller's responsibility").

---

### Finding 2.4

**Severity:** nit  
**File:** `src/readiness_engine/models.py`  
**Line:** 408  
**Finding:** The `ReadinessReport.artefact_reference` docstring example contains a
spurious space in the path string: `"artefacts/\n800-wide/ 01-06"` (the docstring
wraps across a line). The example path `"artefacts/ 800-wide/ 01-06"` has a space
after the slash, which is not a valid path. This is a docstring rendering artefact,
not a runtime defect, but it could confuse implementors reading the generated API docs.

**Suggested fix:** Rewrite the example as a single-line string:
`"artefacts/800-wide/01-06"`.

---

**Lens 2 verdict:** Two major hidden assumptions found (cost baseline definition
ambiguity; CRITICAL risk_level on plain category produces LOW silently). Both require
clarification before Component 2/3/4/5 implementations consume this module.

---

## Lens 3 — Specification / ADR Drift

**Question:** Does the implementation match the specification exactly? Are there
divergences from the spec, the delta, or the architecture decisions recorded in
planning artefacts?

---

### Finding 3.1

**Severity:** major  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 317 (return type)  
**Finding:** `classify_risk()` returns `RiskLevel` (a single value). The specification
interface contract (`spec.md §1.2 Step 6`) and Seam 1 (`tasks.md`) define a
three-field contract:

```
risk_level:      one of LOW / MEDIUM / HIGH / CRITICAL
critical_active: boolean  (true iff risk_level == "CRITICAL")
rationale:       string   (one sentence citing the trigger condition)
```

The function emits only `risk_level`. This is the same finding as 1.1 but examined
from the spec/ADR perspective: it is a documented divergence, but the divergence is
not recorded in a decision log (ADR), only in a docstring. The seam contract in
`tasks.md` remains unchanged and still specifies all three fields.

**Suggested fix:** As in 1.1. Additionally, record the scope decision ("rationale
deferred to future task") as an ADR or a task comment in `tasks.md` so Seam 1's
contract is not misleading for reviewers of T2/T3.

---

### Finding 3.2

**Severity:** minor  
**File:** `src/readiness_engine/report.py`  
**Line:** 309  
**Finding:** `ReadinessReport.verdict` is typed as `str` with default
`ReadinessVerdict.NOT_READY.value`. The domain model `models.ReadinessReport.verdict`
is typed as `ReadinessVerdict` (the enum). This creates a type divergence between the
two `ReadinessReport` classes in the same package. The mutable output type (report.py)
uses a raw `str` while the immutable domain model (models.py) uses the type-safe enum.

Downstream code that constructs a `report.ReadinessReport` can set `verdict` to any
string, bypassing the controlled vocabulary enforced by `ReadinessVerdict`. The
validator catches this at validation time, but the type system does not prevent it at
construction time.

**Suggested fix:** Change `report.ReadinessReport.verdict` to `ReadinessVerdict` with
default `ReadinessVerdict.NOT_READY`. This aligns the output dataclass with the domain
model and provides type-system enforcement of the controlled vocabulary.

---

### Finding 3.3

**Severity:** nit  
**File:** `src/readiness_engine/report.py`  
**Line:** 285  
**Finding:** Both `models.py` and `report.py` export a class named `ReadinessReport`.
They are structurally different: `models.ReadinessReport` is immutable, carries
`critical_drift_active`, and uses `ReadinessVerdict` for `verdict`. `report.ReadinessReport`
is mutable, carries `answers`, `support_ownership`, and `next_actions`, and uses `str`
for `verdict`.

The name collision requires callers to use qualified imports (`from readiness_engine.models
import ReadinessReport as ModelReadinessReport`). This is a brownfield naming debt.
The session log does not record a rationale for keeping both names identical.

**Suggested fix:** Rename one class to reduce ambiguity. For example, rename
`models.ReadinessReport` to `ReadinessSummary` (it is a minimal summary, not the full
output) or rename `report.ReadinessReport` to `ReadinessOutputReport` to distinguish
the full output report from the domain summary.

---

**Lens 3 verdict:** The CRITICAL classification logic, priority ordering, PDB guard,
and write-command detection all conform to the specification. The main drift points are
the partial Seam 1 implementation (rationale absent) and the verdict type divergence
between the two ReadinessReport classes.

---

## Lens 4 — Independent Test Coverage

**Question:** Are the tests sufficient to verify the specification claims independently?
Do tests cover positive, negative, and boundary cases for each acceptance criterion?

---

### Finding 4.1

**Severity:** minor  
**File:** `tests/test_validator.py`  
**Line:** 303 (missing test)  
**Finding:** There is no test for the case where `alert_threshold` is missing from a
cost report that otherwise has a valid `monthly_total` and `hard_cap`. The branch at
`validator.py:205` (`result.fail("Cost report is missing 'alert_threshold'.")`) is
not covered by any test. This is confirmed by the coverage report:

```
validator.py   96%   Missing: 101, 128, 205
```

Line 205 is precisely the `alert_threshold is None` branch. A cost report with a valid
cap but no alert threshold would pass `validate_cost_line_items()` and fail silently
at the cap section.

**Suggested fix:** Add `test_missing_alert_threshold_fails` to `TestValidateCostCap`:

```python
def test_missing_alert_threshold_fails(self) -> None:
    report = _make_cost_report(monthly_total=16500.0, hard_cap=19800.0, alert_threshold=14850.0)
    del report["alert_threshold"]
    result = validate_cost_cap(report)
    assert not result.passed
```

---

### Finding 4.2

**Severity:** minor  
**File:** `tests/test_validator.py`  
**Line:** 196 (missing test)  
**Finding:** There is no test for `validate_audit_checklist_completeness()` receiving
a list of non-dict items. Line 128 (`if not isinstance(item, dict): continue`) is
uncovered. The current tests only pass lists of dicts or lists of the wrong length.
The permissive behaviour described in Finding 2.3 is therefore untested.

**Suggested fix:** Add a test exercising a non-dict item in the checklist list to
verify the function's behaviour (and document whether this is intended to pass or fail).

---

### Finding 4.3

**Severity:** minor  
**File:** `tests/test_validator.py`  
**Line:** 154 (missing test)  
**Finding:** There is no test for `validate_hypothesis_structure()` receiving a
`confidence_pct` that is a non-numeric type (e.g., a string). Line 101
(`result.fail("Hypothesis confidence_pct must be a number.")`) is uncovered. The
existing tests cover out-of-range numeric values (101, -1) and missing keys, but not
a string value like `"high"`.

**Suggested fix:** Add `test_non_numeric_confidence_pct_fails`:

```python
def test_non_numeric_confidence_pct_fails(self) -> None:
    h = _make_hypothesis()
    h["confidence_pct"] = "high"
    result = validate_hypothesis_structure(h)
    assert not result.passed
```

---

### Finding 4.4

**Severity:** minor  
**File:** `tests/test_classifier.py`  
**Line:** 494 (existing test note)  
**Finding:** `test_unknown_owner_on_removed_finding_does_not_trigger_medium_alone` at
line 494 correctly verifies that a `removed` finding with `UNKNOWN` owner and
`risk_level=LOW` produces `LOW`. However, there is no test for `classify_risk()` when
given a `Finding` with `risk_level=CRITICAL` and a plain (non-special) `category`. As
documented in Finding 2.2, this produces `LOW` rather than `CRITICAL`. This silent
downgrade is not exercised by any test.

**Suggested fix:** Add a test:

```python
def test_critical_risk_level_with_non_special_category_does_not_produce_critical(self) -> None:
    """
    A Finding with risk_level=CRITICAL but category not in {write_command_detected,
    pdb_replica_violation} produces LOW — the category gates CRITICAL, not risk_level.
    """
    finding = Finding(
        component_type="Test", component_name="test",
        category="removed", risk_level=RiskLevel.CRITICAL,
        artefact_reference="test"
    )
    assert classify_risk([finding]) == RiskLevel.LOW
```

This documents the hidden assumption in the test suite and makes the downgrade
behaviour explicit and intentional.

---

### Finding 4.5

**Severity:** minor  
**File:** `tests/test_parser.py`  
**Line:** 93 (missing test)  
**Finding:** All audit parser tests use manifests with `kind: Deployment` as the
first kind in the detection loop. No test exercises:
- A manifest with `kind: Service` (second in the loop).
- A manifest with no recognised kind (returns `UNKNOWN`).
- A manifest with a kind appearing after the first in the loop (to cover the
  `181->193` and `189->181` branch misses in the coverage report).

The coverage report confirms: `parser.py` has two branch misses at `181->193`
(no-kind-match path) and `189->181` (loop-continues-past-first-kind path).

**Suggested fix:** Add two tests to `TestParseAuditInput`:
1. A manifest with `kind: Service` to verify non-Deployment kind detection.
2. A manifest with no `kind:` key to verify `input_kind == UNKNOWN`.

---

**Lens 4 verdict:** The `classify_risk()` test suite is comprehensive (90 tests
covering all five acceptance criteria and the PT-1 proof test with positive, negative,
and boundary cases). The coverage gap is entirely in `validator.py` and `parser.py`
(three uncovered lines, two uncovered branches). Five minor gaps identified.

---

## Lens 5 — Edge Cases

**Question:** Are edge cases handled correctly? Are there inputs that would produce
incorrect or unexpected results?

---

### Finding 5.1

**Severity:** minor  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 163 (`\bWarning\s+\w+\b` pattern)  
**Finding:** The diagnosis classification pattern `r"\bWarning\s+\w+\b"` matches any
English sentence containing the word "Warning" followed by whitespace and a word,
regardless of context. For example:

- `"Warning about deployment gaps."` matches → triggers DIAGNOSIS classification.
- `"Warning: consider adding PDB"` does not match (the colon prevents `\s+` match).

A readiness review text containing advisory language like `"Warning about PDB
absence. Operational readiness review needed."` classifies as DIAGNOSIS rather than
READINESS, because DIAGNOSIS has highest priority and only one pattern match is
required. This is a false-positive trigger.

The pattern is intended to match Kubernetes event lines of the form:
`"Warning  BackOff   21s  kubelet"`. The current pattern is wider than the Kubernetes
event format requires.

**Suggested fix:** Narrow the pattern to require the Kubernetes event format:
`r"\bWarning\s+\w+\s+\d"` (requires a digit after the event-name word, matching
the timestamp field). This retains detection of legitimate Kubernetes events while
avoiding false positives on advisory English prose.

---

### Finding 5.2

**Severity:** minor  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 259  
**Finding:** `classify(None)` is not handled at the runtime level. The function
signature is `def classify(text: str)` and the first guard is `if not text or not
text.strip()`. In Python, `not None` evaluates to `True`, so `classify(None)` returns
`None` without raising. However, `None.strip()` would raise `AttributeError` if the
`not text` branch did not short-circuit. This is a coincidental protection that
depends on evaluation order.

Similarly, `classify_risk(None)` passes the `if not findings` guard (since `not None`
is `True`) and returns `RiskLevel.LOW` without raising. The type annotations declare
`list[Finding]`, but no runtime guard enforces this.

**Suggested fix:** Add explicit `isinstance` guards that raise `TypeError` on non-str
input for `classify()` and non-list input for `classify_risk()`, consistent with the
pattern already used in `parser.py`.

---

### Finding 5.3

**Severity:** nit  
**File:** `src/readiness_engine/report.py`  
**Line:** 138  
**Finding:** `AuditItem.status` defaults to `AuditStatus.FAIL`. An `AuditItem`
constructed with only `number` and `name` (the two required fields) will have
`status=FAIL` and `priority=HIGH` by default. This means an uninitialised checklist
item looks like a production blocker by default, which could lead to incorrect report
summaries if a builder forgets to set the status. A default of `AuditStatus.PARTIAL`
or requiring `status` as a positional argument would be safer.

**Suggested fix:** Consider making `status` a required field (remove the default) to
force explicit assignment at construction time.

---

**Lens 5 verdict:** The `\bWarning\s+\w+\b` pattern can produce false-positive
DIAGNOSIS classifications on advisory prose. The `None` input handling in `classify()`
and `classify_risk()` relies on coincidental short-circuit evaluation. No
classification logic defects were found. No edge case produces an incorrect
`RiskLevel` for valid `Finding` inputs.

---

## Lens 6 — Security / Tool Surface

**Question:** Does the implementation expose any security concerns? Does it honour
the read-only constraint? Does it have any unsafe patterns?

---

### Finding 6.1

**Severity:** nit  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 149–225 (all regex patterns)  
**Finding:** All 46 regex patterns compiled in `_DIAGNOSIS_PATTERNS`,
`_AUDIT_PATTERNS`, `_COST_PATTERNS`, and `_READINESS_PATTERNS` use linear-complexity
patterns (no nested quantifiers, no catastrophic backtracking). The patterns were
reviewed against the ReDoS test criteria:

- No nested `(a+)+` or `(a*)*` constructs.
- All quantifiers are applied to character classes or simple groups.
- `\s+` appears in multiple patterns but only with bounded prefix/suffix anchors.

No ReDoS vulnerability was found.

**Finding:** No finding for this lens on write-command generation. The implementation
contains no `subprocess`, `os.system`, `exec`, `eval`, or shell-invocation calls.
No I/O is performed. The read-only constraint is fully honoured.

---

### Finding 6.2

**Severity:** nit  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 149  
**Finding:** All patterns are compiled at module import time (module-level constants).
This is correct for performance (avoids recompilation per call) and safe (patterns are
immutable after module load). The `re.IGNORECASE` flag is consistently applied to all
patterns.

No finding for this lens on input sanitisation. The classify functions process text
provided by the caller. No user input is ever executed, interpolated into commands, or
written to files. The security surface is limited to the regex matching itself.

**Overall Lens 6 verdict:** No security finding. The read-only constraint is absolute
and correctly enforced. No tool surface is exposed. Two nits recorded for completeness.

---

**No finding for this lens** on write-command generation, subprocess use, or
read-only constraint violations.

---

## Lens 7 — Over Engineering

**Question:** Is there any unnecessary complexity? Are there abstractions that add
cost without adding value?

---

### Finding 7.1

**Severity:** nit  
**File:** `src/readiness_engine/classifier.py`  
**Line:** 262–278  
**Finding:** The `classify()` function builds a `scores` dict to count pattern matches
per request type, then iterates `priority_order` to return the first type with any
score. The `scores` dict collects all matching types before a winner is selected.
Given that the priority resolution does not use the count (the `scores[request_type]`
value is never compared between types — it is only tested for existence via `in
scores`), the scoring step is not necessary. The function could be simplified to:

```python
for request_type, patterns in _PRIORITY_TABLE:
    if _count_matches(text, patterns) > 0:
        return request_type
return None
```

The current two-pass approach (build scores, then select winner) is more code for no
additional capability. The comment says "Match count is used only as a secondary
tie-breaker between types at the same priority level (which cannot happen in the
current table)." The tie-breaker code is therefore dead code in the current
implementation.

**Suggested fix:** Either remove the two-pass approach and inline the single-pass
logic, or add a test that verifies tie-breaker behaviour so the code is justified.

---

### Finding 7.2

**Severity:** nit  
**File:** `src/readiness_engine/models.py`  
**Line:** 380–422  
**Finding:** `models.ReadinessReport` (the immutable domain model) is a `frozen=True`
dataclass that carries `verdict`, `maturity_gaps`, `artefact_reference`, and
`critical_drift_active`. `report.ReadinessReport` (the mutable output type) carries
`answers`, `support_ownership`, `next_actions`, `maturity_gaps`, and `verdict`.

The domain model's `maturity_gaps: tuple[str, ...]` is a subset of the output model's
`maturity_gaps: list[str]`. The domain model's `critical_drift_active: bool` exists
only to propagate drift state into readiness assessment — a concern that belongs in
the integration layer, not in the domain model. No current code uses
`models.ReadinessReport.critical_drift_active` in integration logic (T2/T3/T5 are
not yet implemented).

The `models.ReadinessReport` class anticipates a future integration path but carries
that path's state in the domain model layer, mixing concerns. This is premature
abstraction for features not yet implemented.

**Suggested fix:** This is an acceptable Sprint 1 scaffold decision. No immediate
refactor is required. However, the class should be reviewed when Components 2–5 are
implemented to determine whether `critical_drift_active` belongs in the domain model
or in the output formatter layer.

---

**No further finding for Lens 7.** The `classify_risk()` five-priority loop is
correctly structured and no simpler representation of the ordered-evaluation logic
exists. The `validator.py` aggregate validators are appropriate thin wrappers. The
`parser.py` dataclasses are minimal scaffolds consistent with the v0.1 scope
declaration.

---

## Engineering Findings Summary

| # | Lens | Severity | File | Line | Title |
|---|---|---|---|---|---|
| 1.1 | Behaviour Preservation | major | classifier.py | 317 | classify_risk() omits rationale from Seam 1 contract |
| 1.2 | Behaviour Preservation | minor | classifier.py | 228 | Contradictory priority-order comment |
| 1.3 | Behaviour Preservation | nit | \_\_init\_\_.py | 30 | \_\_spec\_version\_\_ tracks stale version 1.0.0 |
| 2.1 | Hidden Assumptions | major | validator.py | 197 | Cost baseline definition uses monthly_total; artefacts use AI meter |
| 2.2 | Hidden Assumptions | major | classifier.py | 467 | risk_level=CRITICAL on plain category silently produces LOW |
| 2.3 | Hidden Assumptions | minor | validator.py | 128 | validate_audit_checklist_completeness() silently accepts non-dict items |
| 2.4 | Hidden Assumptions | nit | models.py | 408 | Docstring example path has spurious space |
| 3.1 | Spec / ADR Drift | major | classifier.py | 317 | Seam 1 rationale field absent from classify_risk() output |
| 3.2 | Spec / ADR Drift | minor | report.py | 309 | ReadinessReport.verdict typed as str, not ReadinessVerdict |
| 3.3 | Spec / ADR Drift | nit | report.py | 285 | ReadinessReport name collision between models.py and report.py |
| 4.1 | Test Coverage | minor | test_validator.py | 303 | No test for missing alert_threshold in cost report |
| 4.2 | Test Coverage | minor | test_validator.py | 196 | No test for non-dict items in audit checklist |
| 4.3 | Test Coverage | minor | test_validator.py | 154 | No test for non-numeric confidence_pct string value |
| 4.4 | Test Coverage | minor | test_classifier.py | 494 | No test documenting CRITICAL risk_level on plain category → LOW |
| 4.5 | Test Coverage | minor | test_parser.py | 93 | No test for non-Deployment kind or no-kind manifest |
| 5.1 | Edge Cases | minor | classifier.py | 163 | \bWarning\s+\w+\b over-broad: matches advisory English prose |
| 5.2 | Edge Cases | minor | classifier.py | 259 | classify(None) and classify_risk(None) rely on coincidental short-circuit |
| 5.3 | Edge Cases | nit | report.py | 138 | AuditItem.status defaults to FAIL, potentially misleading |
| 6.1 | Security | nit | classifier.py | 149 | Regex patterns verified safe (no ReDoS); noted for completeness |
| 7.1 | Over Engineering | nit | classifier.py | 262 | Two-pass scoring in classify() with dead tie-breaker code |
| 7.2 | Over Engineering | nit | models.py | 380 | models.ReadinessReport.critical_drift_active anticipates unimplemented future path |

**Finding count by severity:**

| Severity | Count |
|---|---|
| blocker | 0 |
| major | 4 |
| minor | 11 |
| nit | 7 |
| **Total** | **22** |

---

## Merge Verdict

**Request Changes**

The implementation is structurally sound. The CRITICAL classification logic, priority
ordering, PDB-presence carve-out, and HIGH/CRITICAL boundary condition are correctly
implemented and pass 242 tests including AC-1 through AC-5 and the PT-1 proof test.
All three verification gates pass (ruff, mypy, pytest).

The following items must be resolved or explicitly deferred before merge:

**Must resolve before Components 2–5 are implemented:**

1. **Finding 1.1 / 3.1 (major):** The `rationale` field is absent from
   `classify_risk()`. Downstream components are specified to consume it. Either
   add it to the return value or record its deferral in `tasks.md` so Seam 1's
   contract is not misleading.

2. **Finding 2.1 (major):** The "baseline" definition for the cost cap rule
   is inconsistent between `validator.py` (uses `monthly_total`) and the reference
   artefacts (use AI meter only). This ambiguity must be resolved in the
   specification before Components 2–5 consume the validator.

3. **Finding 2.2 (major):** A `Finding` with `risk_level=CRITICAL` on a plain
   category silently produces `LOW`. This hidden assumption needs either a runtime
   guard or documented contract enforcement to prevent silent misclassification in
   future detection layer implementations.

**Acceptable as tracked items (should not block T2):**

- Finding 1.2 (minor): Comment fix.
- Finding 3.2 (minor): verdict type alignment.
- Findings 4.1–4.5 (minor): Test coverage gaps (all in validator.py and parser.py).
- Finding 5.1 (minor): Warning pattern narrowing.
- All nits.

The three major findings represent incomplete interface contracts and an unresolved
specification ambiguity. They do not constitute runtime defects in the current T1
scope, but they will cause ambiguity or silent errors in the next sprint without
resolution.

---

*Review produced under Kata K 5.D.9 — Deep Engineering, Seven-Lens Engineering Review.*  
*Isolation Tier C (Limited) — implementation and review occurred in the same engineering effort.*

---

## Adversarial Pass

**Model:** Claude Sonnet 4.6  
**Date:** 2026-07-23  
**Scope:** Sprint 1 + Sprint 2 implementation — same file set as the Seven-Lens Review  
**Prior review artefact:** `reviews/T1/review.md` (22 findings, Seven-Lens)  
**Constraint:** Findings already recorded in the Seven-Lens Review are excluded.

---

### Pre-mortem Finding — Confirmed Defect (Fixed)

**Finding:** `parse_audit_input()` detected `:latest` using a raw substring search across the entire lowercased manifest text. Any occurrence of the string `:latest` anywhere in the input — including YAML comments, annotation values, and label values — triggered `has_image_tag_latest = True`, regardless of whether the live container image reference used a mutable tag.

**Trigger:** A Kubernetes manifest containing an annotation that referenced a previous image version (for example, `deployment.kubernetes.io/previous-image: "ghcr.io/example/cart-api:latest"`) while the active `image:` field used a digest reference caused a false positive. Common maintenance patterns such as `# formerly :latest before migration` in a comment had the same effect.

**Blast radius:** Every downstream audit consuming `RawAuditInput.has_image_tag_latest` as a proxy for checklist item 6 ("Immutable image reference") produced a false `FAIL` for a correctly configured manifest. Over time, operators would learn to ignore item 6 failures and stop acting on genuine `:latest` tag regressions. The audit signal would lose its discriminatory value for the most commonly introduced image reference mistake.

**Mitigation applied:** The raw substring scan was replaced with a compiled, module-level regular expression anchored to YAML `image:` field lines:

```python
_IMAGE_LATEST_RE: re.Pattern[str] = re.compile(
    r"^\s*-?\s*image:\s*\S+:latest\s*$",
    re.MULTILINE,
)
```

The pattern matches only lines where `image:` is the field key and the reference ends in `:latest`. Comments, annotations, and label values are not matched. The pattern is compiled once at module import and reused across all calls.

**Resolution: FIX NOW**

The fix was applied to `src/readiness_engine/parser.py`. Four new tests were added to `tests/test_parser.py` to document and verify the corrected behaviour. All 246 tests pass after the change.

---

### Edge Case Hunter Finding — Accepted Risk (No Code Change)

**Finding:** `validate_cost_cap()` computes a cap floor by multiplying `monthly_total` by `HARD_CAP_FLOOR_MULTIPLIER` (1.20). When `monthly_total` is a negative float — reachable if a caller passes a signed accounting figure such as a credit or refund value — the computed floor is also negative (`-500.0 × 1.20 = -600.0`). Any `hard_cap >= -600.0` satisfies the arithmetic condition, including `hard_cap=0.0`. The validator passes a cost report with a negative baseline and a zero hard cap without raising a violation.

**Input shape:** `{"monthly_total": -500.0, "hard_cap": 0.0, "alert_threshold": 0.0, "cloud_rent": ..., "ai_meter": ...}`

**Observable failure:** `validate_cost_cap()` returns `passed=True`. The cost cap guardrail — which exists to prevent under-provisioned financial controls — is bypassed silently for any input with a negative monthly total.

**Mitigation considered:** Adding a non-negativity guard at the start of `validate_cost_cap()` before the floor computation. The guard would call `result.fail(...)` and return early on `float(baseline) < 0`.

**Resolution: ACCEPT WITH DOCUMENTED RISK**

The specification (SKILL.md §Output Type 3 and CLAUDE.md Rule 6) does not define whether negative cloud cost values are valid inputs. All reference figures in CLAUDE.md and the artefacts are strictly positive. Until the specification explicitly defines the valid numeric range for cost inputs, the behaviour for negative values is undefined by contract rather than incorrect by implementation. Applying a guard would be an assumption layered on top of the specification, not a requirement derived from it.

`validator.py` is not modified for this item.

**Accepted risk condition:** If a future specification version introduces signed cost figures (credits, refunds, or adjustments), this path must be revisited and an explicit non-negativity guard or a sign-normalisation step added to `validate_cost_cap()`.

---

### Adversarial Pass Verdict

**APPROVED** — after the parser fix.

The confirmed defect (`has_image_tag_latest` false-positive on non-image-field `:latest` occurrences) has been corrected. The edge case risk (negative cost baseline producing a false-pass in `validate_cost_cap`) is accepted pending specification clarification. No other implementation defects were identified that are not already tracked in the Seven-Lens Review findings summary.

| Finding | Category | Resolution |
|---|---|---|
| `parse_audit_input()` `:latest` raw substring scan | Confirmed defect | FIX NOW — applied |
| Negative `monthly_total` bypasses cap guard | Undefined-input risk | ACCEPT WITH DOCUMENTED RISK |

*Adversarial Pass produced by Claude Sonnet 4.6 — independent review, no prior exposure to the Sprint 1 / Sprint 2 implementation.*
