# Pull Request

## T1 — Risk Classification Logic: CRITICAL Trigger and Boundary Condition

This PR delivers the T1 first slice of the Operational Drift Risk Model Extension. It
introduces the CRITICAL risk level as a first-class classification in the Reference Engine's
risk classification logic, guarded by the PDB-presence boundary condition that prevents a
replica-count reduction from producing CRITICAL when no PodDisruptionBudget exists in
State A.

**What changed.** The `classify_risk()` function in `src/readiness_engine/classifier.py`
was extended with two new Priority 1 and Priority 2 CRITICAL trigger paths following the
five-priority ordered evaluation table formalised in `specs/operational-drift-analysis/spec.md
§1.2`. The `parse_audit_input()` function in `src/readiness_engine/parser.py` was hardened
to anchor `:latest` image tag detection to actual YAML `image:` field lines, eliminating
false positives caused by YAML comments, annotations, and label values containing the
substring. The Seven-Lens Review and Adversarial Pass were conducted and their findings
are recorded in `reviews/T1/review.md` and `reviews/T1/findings.csv`.

**Why the change exists.** The delta (`changes/operational-drift-risk-model/delta.md`)
formalised CRITICAL as a named severity in response to a Product Owner change request
against spec v1.0.1. The prior specification treated HIGH as the effective maximum, leaving
callers that built against the full vocabulary unable to trigger the fourth level. The delta
and its associated task decomposition (`changes/operational-drift-risk-model/tasks.md`)
defined T1 as the FIRST SLICE: implement the classification logic and freeze the Seam 1
interface contract so downstream tasks T2, T3, and T5 can consume `critical_active` and
`risk_level` without re-evaluating findings.

**Engineering value.** The implementation provides a deterministic, specification-traceable
risk classification engine whose correctness is demonstrated by 246 passing unit tests,
enforced by strict Ruff and MyPy configurations, and reviewed independently through both a
Seven-Lens Engineering Review (22 findings) and an Adversarial Pass (one confirmed defect
fixed, one accepted risk documented). The repository has been evolved into an executable
Python Reference Engine against which future Deep Engineering katas can run meaningful
independent verification.

---

## Provenance

### Tool / Model

| Item | Value |
|---|---|
| AI client | Codemie Code (Claude) |
| Model | claude-sonnet-4-6 |
| Kata chain | K 5.D.4 (spec) → K 5.D.5 (delta) → K 5.D.6 (plan + tasks) → K 5.D.7 (implementation session) → K 5.D.8 (independent verification) → K 5.D.9 (Seven-Lens Review) → K 5.D.10 (Adversarial Pass) → K 5.D.11 (PR Provenance) |
| Approximate execution dates | 2026-07-20 through 2026-07-23 |

Execution dates are confirmed by the git commit log. The implementation commits range from
`2c301d5` (2026-07-22 16:44) through `d663a24` (2026-07-23 11:17). Specification and
planning artefacts were authored on 2026-07-22. Skill execution runs (`run-log.md`
RUN-001 through RUN-005) were recorded on 2026-07-20.

---

### Context Loaded

**Primary implementation modified:**

`src/readiness_engine/classifier.py` — the risk classification engine. Sprint 2 extended
this module with the five-priority ordered evaluation table, CRITICAL trigger paths, and
the PDB-presence carve-out. The adversarial pass subsequently hardened
`src/readiness_engine/parser.py` by replacing a raw `:latest` substring scan with a
compiled, YAML-field-anchored regular expression (`_IMAGE_LATEST_RE`).

**Supporting files referenced throughout the engineering effort:**

| File | Role |
|---|---|
| `specs/operational-drift-analysis/spec.md` v1.0.1 | Normative specification; five-priority evaluation table; interface contract; acceptance criteria AC-1–AC-4 |
| `specs/operational-drift-analysis/audit.md` | Pre-implementation Tier A specification audit; AUDIT-ODA-01 and AUDIT-ODA-02 incorporated into spec |
| `changes/operational-drift-risk-model/delta.md` v1.0.0 | Brownfield delta; A-1 through A-5 additions; M-1 through M-6 modifications; R-1 through R-5 removals; proof test definition |
| `changes/operational-drift-risk-model/plan.md` v1.0.0 | Six-component implementation plan; Component 1 interface contract; propagation diagram |
| `changes/operational-drift-risk-model/tasks.md` v1.0.0 | Six-task decomposition; T1 FIRST SLICE annotation; Seam 1–5 interface contracts; dependency graph |
| `sessions/T1/session-log.md` | K 5.D.7 implementation session; seven verification gates; K 5.D.8 independent verification results |
| `CLAUDE.md` | Non-negotiable rules; escalation gates; cost reference figures |
| `docs/adr/ADR-001-reference-engine.md` | Architecture decision to evolve repository into an executable Python Reference Engine |
| `src/readiness_engine/models.py` | Domain model; `RiskLevel` enumeration; `Finding` dataclass |
| `src/readiness_engine/validator.py` | Report validation against SKILL.md rules |
| `src/readiness_engine/parser.py` | Audit input parser; `:latest` detection hardened by adversarial pass |
| `src/readiness_engine/report.py` | Output report dataclasses for the four output types |
| `tests/test_classifier.py` | 90 tests covering AC-1–AC-5 and PT-1 with positive, negative, and boundary cases |
| `tests/test_parser.py` | 32 tests including four new regression tests for `:latest` false-positive fix |
| `tests/test_validator.py` | 57 tests covering structural validation rules |
| `tests/test_models.py` | 67 tests covering specification constant and enumeration invariants |

**Engineering practices applied:**

- **Specification-Driven Development** — every implementation decision is traceable to a
  specification section, delta item, or task contract. No behaviour was introduced that
  does not appear in the specification.
- **Independent Verification** — all three gates (Ruff, MyPy, pytest) were run against an
  unmodified working tree before review commenced. Gate results are recorded in
  `sessions/T1/session-log.md`.
- **Seven-Lens Engineering Review** — conducted at Isolation Tier C (same engineering
  effort); 22 findings produced across seven lenses; recorded in `reviews/T1/review.md`
  and `reviews/T1/findings.csv`.
- **Adversarial Review** — pre-mortem and edge-case hunter passes conducted by
  claude-sonnet-4-6; one confirmed defect fixed (`:latest` false-positive); one accepted
  risk documented (negative cost baseline); recorded in `reviews/T1/review.md` Adversarial
  Pass section.

---

### Verification Gates

| Gate | Tool / Command | Result |
|---|---|---|
| Ruff | `python -m ruff check .` | **PASS** — 0 errors, 0 warnings |
| MyPy | `python -m mypy src` | **PASS** — 0 issues in 6 source files |
| PyTest | `python -m pytest` | **PASS** — 246/246 passed (242 pre-adversarial pass; 4 new tests added by adversarial fix) |
| Coverage | `pytest --cov` | **PASS** — 97.08% (threshold: 90%) |
| Independent Verification | K 5.D.8 — `sessions/T1/session-log.md` | **PASS** — all three gates passed on first run; no defects discovered; Isolation Tier C |
| Seven-Lens Review | K 5.D.9 — `reviews/T1/review.md` | **REQUEST CHANGES** — 22 findings (0 blocker, 4 major, 11 minor, 7 nit); 3 majors require resolution before T2/T3 consume the module |
| Adversarial Review | K 5.D.10 — `reviews/T1/review.md` Adversarial Pass | **APPROVED after fix** — 1 confirmed defect fixed; 1 accepted risk documented |

The Seven-Lens verdict of "Request Changes" reflects findings against the full Sprint 1 +
Sprint 2 implementation scope (all five source modules). The three major findings that
require resolution before T2/T3 proceed are: (1) `classify_risk()` omits `rationale` from
the Seam 1 contract (Finding 1.1/3.1); (2) cost baseline definition is inconsistent between
`validator.py` and the reference artefacts (Finding 2.1); (3) a `Finding` with
`risk_level=CRITICAL` on a plain category silently produces `LOW` (Finding 2.2). These are
tracked items, not deployment blockers for the T1 scope.

---

### Human Decisions

The following engineering decisions were made by the human engineer rather than the AI:

**Repository evolution to executable Reference Engine.**
The human decided to evolve the repository from a documentation-only Skill repository into
one containing both the normative specification and an executable Python Reference Engine.
This decision is recorded in `docs/adr/ADR-001-reference-engine.md` (Status: Proposed).
Without this decision, the subsequent Independent Verification, Seven-Lens Review, and
Adversarial Review katas would have operated on simulated rather than real executable
artefacts.

**Fixing the parser `:latest` detection.**
The Adversarial Pass identified that `parse_audit_input()` used a raw `:latest` substring
scan across the entire lowercased manifest text, producing false positives on YAML comments,
annotations, and label values. The human approved the fix: replacing the substring scan with
a compiled, YAML-field-anchored regular expression (`_IMAGE_LATEST_RE` in `parser.py`)
restricted to lines of the form `image: <ref>:latest`. The fix was applied to
`src/readiness_engine/parser.py` and four new regression tests were added to
`tests/test_parser.py`.

**Choosing NOT to implement validation for negative financial values.**
The Adversarial Pass edge-case hunter identified that `validate_cost_cap()` passes silently
when `monthly_total` is negative (e.g., a credit or refund figure), because the floor
computation (`negative × 1.20 = more negative`) is trivially satisfied by any
`hard_cap >= 0`. The human decided to accept this as a documented risk rather than add a
non-negativity guard, because the specification (SKILL.md §Output Type 3 and CLAUDE.md
Rule 6) does not define whether negative cloud cost values are valid inputs. Applying a
guard would be an assumption layered on top of the specification. `validator.py` was not
modified for this item. The decision is recorded in `reviews/T1/review.md`, Adversarial
Pass section, Edge Case Hunter finding.

---

### Known Limitations

**Seam 1 `rationale` field deferred.**
`classify_risk()` returns `RiskLevel` only. The Seam 1 interface contract in `tasks.md`
and the specification interface contract in `spec.md §1.2 Step 6` define three fields:
`risk_level`, `critical_active`, and `rationale`. The `rationale` string is not produced
by any code in the current T1 scope. This is a T1-scoped limitation recorded as Seven-Lens
Finding 1.1 (major). Downstream tasks T2 and T3 must not consume `classify_risk()` as
though `rationale` is available until this is resolved.

**Lightweight `:latest` detection (no full YAML parsing).**
`parse_audit_input()` uses a compiled regular expression anchored to YAML `image:` field
lines rather than a full YAML parser. This is intentional for the v0.1 scope: the parser
module is declared as a "minimal scaffold" with no logic beyond surface extraction. The
regex correctly handles standard Kubernetes Deployment YAML with list-form container
entries (`- image: ...`) and map-form entries (`image: ...`). Unusual YAML structures
(multi-line scalars, anchors, aliases) are not covered. This is recorded in the parser
module docstring as a future improvement.

**Cost baseline definition ambiguity.**
`validate_cost_cap()` uses `monthly_total` (cloud rent + AI meter) as the baseline for the
120% hard cap rule. The reference artefacts in `artefacts/800-wide/05-cost-estimate.md`
and `CLAUDE.md` define baseline as the AI meter spend alone ($15,000). This inconsistency
means the validator would reject the reference artefact's $18,000 cap as non-compliant
(minimum under validator logic: $19,800). The ambiguity must be resolved with the product
owner before spec v1.1.0 is issued. Recorded as Seven-Lens Finding 2.1 (major).

**CRITICAL on plain category produces LOW silently.**
A `Finding` constructed with `risk_level=CRITICAL` and a category that is neither
`CATEGORY_WRITE_COMMAND` nor `CATEGORY_PDB_REPLICA_VIOLATION` produces `RiskLevel.LOW`
rather than raising an error. The CRITICAL classification is category-gated, not
risk_level-gated, but no runtime assertion enforces this class invariant. A future
detection layer implementation that assigns `risk_level=CRITICAL` to a plain category
would silently produce LOW. Recorded as Seven-Lens Finding 2.2 (major).

**Components 2–5 not yet implemented.**
The Risk Level Section Formatter (T2), Escalation Block Builder (T3), NFR Vocabulary
Validator (T4), Acceptance Criterion test definitions (T5), and Spec Version Increment
(T6) are not implemented. These are future task slices. The T1 scope is the first and
only implemented slice.

---

### Session Duration

Approximately two days of elapsed calendar time (2026-07-22 to 2026-07-23), with active
engineering work spanning seven katas (K 5.D.4 through K 5.D.10). This includes
specification authoring, audit, delta and plan production, task decomposition, supervised
implementation, independent verification, Seven-Lens Review, and Adversarial Pass. Active
AI-assisted engineering time per kata is estimated at 30–90 minutes each.

---

### SDD Approach

This work follows the Specification-Driven Development workflow applied consistently
throughout this repository:

1. **Specification authored first** (K 5.D.4) — `specs/operational-drift-analysis/spec.md`
   defines all acceptance criteria, interface contracts, and NFR targets before any code
   is written.
2. **Specification audited** (K 5.D.4) — `specs/operational-drift-analysis/audit.md`
   conducts a Tier A audit of the specification, incorporating two findings and deferring
   one. The specification is updated to v1.0.1 before the delta is written.
3. **Delta authored** (K 5.D.5) — `changes/operational-drift-risk-model/delta.md`
   describes exactly what is ADDED, MODIFIED, and REMOVED, including a risk note and
   proof test, before implementation begins.
4. **Implementation planned and decomposed** (K 5.D.6) — `changes/operational-drift-risk-model/plan.md`
   and `changes/operational-drift-risk-model/tasks.md` define six components, six tasks,
   five seam contracts, and a dependency graph. T1 is identified as the FIRST SLICE.
5. **Supervised implementation** (K 5.D.7) — `sessions/T1/session-log.md` records the
   ordered action log, every proposal and approval, and seven verification gates.
6. **Independent verification** (K 5.D.8) — all three tool gates are run against an
   unmodified working tree and recorded in the session log.
7. **Seven-Lens Review** (K 5.D.9) — `reviews/T1/review.md` evaluates the full
   implementation across Behaviour Preservation, Hidden Assumptions, Spec/ADR Drift,
   Independent Test Coverage, Edge Cases, Security, and Over Engineering.
8. **Adversarial Review** (K 5.D.10) — `reviews/T1/review.md` (Adversarial Pass section)
   applies pre-mortem and edge-case hunter techniques; one confirmed defect is fixed.

The specification at `specs/operational-drift-analysis/spec.md` v1.0.1 is the normative
reference for all implementation decisions. Spec v1.1.0 incorporating the full delta is
gated behind the T6 Engineering Lead approval and has not yet been issued.

---

## Linked Evidence

| Artefact | Path |
|---|---|
| Specification (v1.0.1) | `specs/operational-drift-analysis/spec.md` |
| Specification audit | `specs/operational-drift-analysis/audit.md` |
| Brownfield delta (v1.0.0) | `changes/operational-drift-risk-model/delta.md` |
| Implementation plan (v1.0.0) | `changes/operational-drift-risk-model/plan.md` |
| Task decomposition (v1.0.0) | `changes/operational-drift-risk-model/tasks.md` |
| Session log (T1) | `sessions/T1/session-log.md` |
| Seven-Lens Review | `reviews/T1/review.md` |
| Adversarial Pass | `reviews/T1/review.md` (Adversarial Pass section) |
| Findings (machine-readable) | `reviews/T1/findings.csv` |
| Architecture Decision Record | `docs/adr/ADR-001-reference-engine.md` |
| Primary implementation | `src/readiness_engine/classifier.py` |
| Parser hardening | `src/readiness_engine/parser.py` |
| Domain model | `src/readiness_engine/models.py` |
| Report dataclasses | `src/readiness_engine/report.py` |
| Validator | `src/readiness_engine/validator.py` |
| Package init / spec version | `src/readiness_engine/__init__.py` |
| Classification tests | `tests/test_classifier.py` |
| Parser tests (incl. regression) | `tests/test_parser.py` |
| Validator tests | `tests/test_validator.py` |
| Domain model tests | `tests/test_models.py` |
| Tool configuration | `pyproject.toml` |
| Skill execution log | `run-log.md` |
| Repository-specific context | `CLAUDE.md` |
| Portable Skill definition | `skills/cloud-operations-analysis/SKILL.md` |

---

## Redaction Review

A redaction pass was conducted over all files listed in the Linked Evidence section above
and over the content of this document. The following categories were checked:

| Category | Finding |
|---|---|
| Secrets or credentials | None found. No API keys, tokens, passwords, or authentication material present in any file. |
| Customer data | None found. All service data is explicitly synthetic (`cart-api` reference service). |
| Internal URLs | None found. The `pyproject.toml` references `github.com/example/...` placeholder URLs, not internal infrastructure. |
| Employee names | None found. All role references use generic titles (Product Owner, Engineering Lead, On-call platform engineer). The git commit author field (`Ernesto Banuelos`) is a standard git attribution, not a sensitive disclosure. |
| Proprietary information | None found. The repository is published as an open reference implementation (README.md). All cost figures and service names are documented as fictional. |

**Redaction review completed successfully. No sensitive material was identified.**

---

## Read-as-a-Stranger Validation

**PASS**

A reviewer unfamiliar with this implementation can reconstruct the full engineering
narrative from the repository evidence alone:

1. The specification (`specs/operational-drift-analysis/spec.md`) defines all acceptance
   criteria and the interface contract against which the implementation is evaluated.
2. The audit (`specs/operational-drift-analysis/audit.md`) explains why spec v1.0.0 was
   revised to v1.0.1 before implementation began.
3. The delta (`changes/operational-drift-risk-model/delta.md`) explains what changed and
   why, including the proof test that bounds the HIGH/CRITICAL decision boundary.
4. The plan and tasks (`changes/operational-drift-risk-model/plan.md`,
   `changes/operational-drift-risk-model/tasks.md`) explain how the change was decomposed
   and which task slice was implemented first.
5. The session log (`sessions/T1/session-log.md`) records every proposal, approval, and
   verification gate result. The implementation is supervised and all decisions are
   traceable.
6. The Seven-Lens Review (`reviews/T1/review.md`) provides an independent structured
   evaluation covering all seven engineering lenses. Findings are severity-classified and
   resolved, deferred, or tracked.
7. The Adversarial Pass (`reviews/T1/review.md`, Adversarial Pass section) records the
   confirmed defect, the fix applied, and the accepted risk with documented rationale.
8. The test suite (`tests/test_classifier.py`) covers all five acceptance criteria and the
   PT-1 proof test with positive, negative, and boundary cases, providing executable
   evidence of correct behaviour.

A reviewer arriving at this PR with no prior context has sufficient evidence to evaluate
the correctness of T1, understand its scope limitations, assess the open findings, and
make an informed merge decision.
