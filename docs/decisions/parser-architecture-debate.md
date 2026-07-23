# Parser Architecture Debate

**Status:** Decision recorded  
**Date:** 2026-07-23  
**Affects:** `src/readiness_engine/parser.py` — `parse_audit_input()` and all Kubernetes manifest inspection logic

---

## Decision Question

Should the Reference Engine continue using a lightweight pattern-based parser for Kubernetes manifest inspection, or should it evolve to a structured YAML parser?

---

## Decision Criteria

The following five criteria govern this evaluation. Each is stated, defined, and justified.

### 1. Correctness on Kubernetes Manifests

A parser is correct when it returns the right answer for well-formed Kubernetes YAML and fails safely — rather than silently — on unusual or malformed input.

This matters because the Reference Engine's downstream risk classification depends entirely on the boolean presence signals produced by `parse_audit_input()`. A false positive on `has_image_tag_latest` (flagging a manifest whose live container uses a digest, not `:latest`) triggers an unwarranted `HIGH` risk finding. A false negative (missing a real `:latest` usage buried in an anchor-aliased block) silently suppresses a legitimate finding. Both failure modes corrupt the risk classification without raising an exception.

### 2. Implementation Complexity

Complexity is the total engineering effort required to introduce, test, and maintain the parser over the life of the codebase — not just the effort to write the initial version.

This matters because the Reference Engine is a demonstration artefact whose primary obligation is fidelity to the Skill specification. Complexity that does not improve fidelity is waste. Complexity that introduces new failure modes is debt.

### 3. Long-Term Maintainability

Maintainability is the ease with which a future contributor can read, understand, modify, and extend the parser without introducing regressions.

This matters because the codebase will continue to accrete kata slices. Each new slice adds detection requirements. If the parser's internals are opaque or tightly coupled, slice boundaries become fragile. If the parser's internals are transparent and well-bounded, slices remain independently testable.

### 4. Dependency Footprint

Dependency footprint is the total count of runtime packages that the engine requires beyond the Python 3.11 standard library.

This matters because `pyproject.toml` currently declares `dependencies = []`. This is not an accident: `CLAUDE.md` imposes an escalation gate before any new dependency is added. The gate exists because runtime dependencies increase supply-chain risk, widen the security audit surface, and can introduce version-conflict failures in consumer environments. Any architecture that requires a third-party YAML library must clear this gate explicitly.

### 5. Ease of Future Feature Expansion

Expandability is the degree to which the parser's structure accommodates new extraction requirements — reading field *values* rather than detecting field *presence*, traversing nested structures, handling multi-document manifests — without requiring a complete rewrite.

This matters because the current detection backlog already requires value-level inspection: `minAvailable` from `PodDisruptionBudget`, `replicas` from `Deployment`, and security-context sub-fields (`runAsNonRoot`, `allowPrivilegeEscalation`). The parser that serves as the foundation for those features should not require demolition before the work begins.

---

## Round 1 — Strongest Case for Each Architecture

### Option A — Lightweight Pattern-Based Parser

**The pattern-based parser is already correct for the scenarios it must handle, and its correctness has been verified.**

The Adversarial Pass on T1 identified exactly one false-positive defect in the original implementation: a raw `:latest` substring scan triggered on comments, annotations, and label values that contained the string but were not image fields. That defect was fixed by replacing the raw scan with `_IMAGE_LATEST_RE`, a compiled multiline regex anchored to actual `image:` field lines:

```
r"^\s*-?\s*image:\s*\S+:latest\s*$"
```

[Evidence-backed] — `src/readiness_engine/parser.py:30–50`; `reviews/T1/review.md` Adversarial Pass Pre-mortem Cause 2.

The remaining field-presence checks (`securitycontext:`, `limits:`, `livenessprobe:`, `readinessprobe:`) use lowercased substring matching. For the canonical `cart-api` manifests — well-formed, single-document, standard indentation — these checks produce no false positives or false negatives in the current test suite. [Evidence-backed] — `tests/test_parser.py`: 32 tests passing, including 4 `:latest` regression tests.

The pattern-based parser carries zero runtime dependencies. It has been operational since v0.1.0, its behaviour is fully covered at 97.08% coverage, and its logic is readable in a single screen. A future contributor encountering `"securitycontext:" in lower` understands the check immediately without consulting library documentation. Implementation complexity is minimal. Maintenance cost is proportional to the number of patterns — which is small and grows linearly with new fields, not with YAML complexity.

For a reference implementation whose primary obligation is demonstrating Skill fidelity at bounded scope, the pattern-based parser is sufficient, correct, and appropriate today.

---

### Option B — Structured YAML Parser

**The pattern-based parser's correctness guarantee is bounded to the surface structure of the strings it has been tested against. The moment manifests deviate from that surface structure, the guarantee collapses silently.**

YAML is not a line-delimited key-value format. It is a structured data language with multi-line scalars, block and flow sequences, anchors, aliases, and merge keys. The following are all valid YAML representations of a container image field:

```yaml
# Flow scalar — will be missed by a line-anchored regex
image: "nginx:latest"

# Multi-line scalar — breaks line-by-line matching
image: |
  nginx:latest

# Anchor + alias — value is injected at parse time, invisible to text scanning
.image: &img nginx:latest
containers:
  - image: *img
```

[Evidence-backed] — YAML specification §6 (flow scalars), §8 (block scalars), §7.1 (alias nodes). [Evidence-backed] — `parser.py` module docstring: "Unusual YAML structures (multi-line scalars, anchors, aliases) are not covered."

A structured YAML parser (`yaml.safe_load()`, available in PyYAML, or `tomllib`-equivalent) produces a Python dictionary from the manifest. Field access becomes `spec["containers"][0]["image"]`. The presence check becomes `"image" in container`. There are no false positives from comments or annotations, because comments are not in the parsed tree. There are no false negatives from alternative scalar styles, because the parser resolves them.

[Evidence-backed] — `specs/operational-drift-analysis/spec.md §1.2`: the `pdb_replica_violation` CRITICAL trigger requires comparing `replicas` against `minAvailable` as integer values. Pattern matching cannot perform integer comparison. A structured YAML parser makes this extraction trivial and type-safe.

The detection backlog for future slices — `minAvailable`, `replicas`, security-context sub-fields — is fundamentally a structured-data problem. Building it on a text-pattern foundation means every new feature is a new special-case regex, each adding to a fragile, non-composable pile. A structured foundation makes each new feature a standard dictionary traversal.

---

## Round 2 — Cross-Examination

### Option A critiques Option B

**The structured YAML parser solves a class of problems that has not yet manifested in this repository, at the cost of a dependency constraint that is real and binding today.**

The most forceful argument for Option B is that manifests could contain anchors, aliases, or multi-line scalars that defeat the pattern-based parser. This is technically correct. It is also [Assumption] that any such manifest will appear as input to this engine in the foreseeable kata roadmap. The current and planned test corpus consists entirely of canonical, single-document Kubernetes manifests consistent with `artefacts/800-wide/02-deploy-manifest.md`. There is no multi-document manifest, no anchor-alias usage, and no flow-scalar image field in any artefact or test fixture. [Evidence-backed] — `tests/test_parser.py`; `artefacts/800-wide/02-deploy-manifest.md`.

The dependency footprint risk is not theoretical. `PyYAML` carries a documented history of security advisories. `ruamel.yaml`, a more correct YAML 1.2 implementation, is a 50 kLOC package. Adding either requires clearing the escalation gate in `CLAUDE.md`. [Evidence-backed] — `CLAUDE.md §Escalation Gates: "Stop before adding new dependencies."` The escalation gate exists precisely to prevent convenience additions that accrete supply-chain risk. A structured parser is not a convenience addition — it is an architectural shift — and that shift should be gated on a demonstrated need, not a hypothetical risk.

The integer-comparison argument (reading `replicas` vs. `minAvailable`) is the strongest technical case for Option B. But it is [Unknown] whether those fields will be read by the parser or by a separate detection-layer component that receives pre-parsed input. The current `plan.md` T2–T5 implementation plan does not specify which component performs value extraction. Assuming the parser must do it is premature.

---

### Option B critiques Option A

**The hardened regex is a local fix to a structural problem. It raises the ceiling on correctness for the specific case it covers, but it does not raise the ceiling for the cases it does not cover.**

`_IMAGE_LATEST_RE` was introduced because the original substring scan produced false positives. The fix is real and it works. [Evidence-backed] — `parser.py:30–50`; `tests/test_parser.py` regression tests. But the fix also illustrates the core weakness of the pattern-based approach: correctness is achieved one edge case at a time, through manual pattern refinement, not through structural correctness. Each new edge case requires a new patch, and each patch adds a new test, and each new test is evidence of a new way the pattern was previously wrong.

The remaining field-presence checks — `"securitycontext:" in lower`, `"limits:" in lower` — are not anchored. They will match `securitycontext:` in a comment block, in a string value, or in a label. [Evidence-backed] — `parser.py:196–200`. The Adversarial Pass only investigated the `:latest` path in depth; it did not systematically audit the substring checks. [Unknown] — whether similar false-positive conditions exist for the remaining four fields on inputs not yet in the test corpus.

The `input_kind` detection uses `f"kind: {kind}" in stripped`. This will match a comment `# kind: Deployment was removed`, returning `input_kind = "Deployment"` on a manifest that contains no Deployment resource. [Evidence-backed by reasoning] — the check is not anchored to YAML line boundaries. [Unknown] — whether this condition appears in practice in the current corpus.

These are not hypothetical risks. They are consequences of the current implementation's architecture that the test suite does not yet exercise.

---

## Evidence Classification Summary

| Claim | Classification |
|---|---|
| `_IMAGE_LATEST_RE` fix eliminated `:latest` false positives | Evidence-backed |
| 246 tests pass at 97.08% coverage | Evidence-backed |
| Anchors, aliases, multi-line scalars are valid YAML | Evidence-backed |
| No anchor/alias usage exists in current test corpus | Evidence-backed |
| `"securitycontext:" in lower` will match comment lines | Evidence-backed by reasoning |
| `input_kind` detection will match `# kind: Deployment` comments | Evidence-backed by reasoning |
| A future manifest in this kata will use anchors or aliases | Assumption |
| T2–T5 detection layer will require value-level YAML extraction | Unknown |
| PyYAML introduces meaningful supply-chain risk in this context | Assumption |
| Substring checks produce false positives on current corpus | Unknown |

---

## Decision

**Decision: Option A — Lightweight Pattern-Based Parser**

### Why it wins today

The strongest decision criterion is **Dependency Footprint** (Criterion 4), and it is not close.

`pyproject.toml` carries `dependencies = []`. `CLAUDE.md` imposes an explicit escalation gate before any new dependency is added. This constraint is documented, intentional, and architectural. It is not a default that was never examined — it was recorded as a principle in `ADR-001` ("Reference, Not Production") and enforced by the project's pre-commit and CI configuration.

A structured YAML parser requires a third-party package. No Python standard-library module provides `yaml.safe_load()`. `tomllib` (Python 3.11+) parses TOML, not YAML. The only standard-library option for YAML-adjacent structured parsing is `json` (which accepts JSON-subset YAML in narrow cases) — not a general solution. Adding `PyYAML` or `ruamel.yaml` would require an explicit escalation decision, not a parser refactor.

The correctness argument for Option B is technically valid but applies to a failure mode that does not yet exist in the production corpus. The Adversarial Pass found one real false-positive defect. It was caused by an unanchored substring scan on a specific field, not by a structural YAML parsing gap. The fix — an anchored, multiline regex — addressed the root cause for that field. The remaining field checks have not produced failures in any test or review.

The expandability concern (Criterion 5) is the strongest legitimate challenge to this decision. Reading `minAvailable` and `replicas` as integers requires structured parsing, not pattern matching. However, this requirement belongs to the detection layer (T2–T5, unimplemented) and the architecture of that layer has not been specified. Introducing a YAML parser now, before the detection layer design is settled, is a premature optimization that carries a real dependency cost in exchange for a speculative benefit.

### Why the alternative was rejected today

Option B was rejected not because structured YAML parsing is incorrect, inferior, or inadvisable as a general engineering pattern. It is the right approach for any system that must parse YAML with production correctness guarantees.

It was rejected because:

1. The escalation gate that governs dependency additions has not been cleared. Adopting Option B without clearing that gate would violate the project's documented architectural governance.
2. The specific correctness failures that motivate Option B (multi-line scalars, anchors, aliases) are not present in the current artefact corpus and are not scheduled for introduction in the current kata roadmap.
3. The implementation complexity introduced by a dependency adds maintenance surface — version pinning, security scanning, library upgrade cycles — that is disproportionate to the correctness improvement available today.

Option B is the correct future direction. It is not the correct choice today.

---

## Reversal Evidence

The following conditions, if observed, constitute objective engineering signals that justify reopening this decision. Each is a measurable condition, not a preference.

| Signal | Threshold | Measurement |
|---|---|---|
| Pattern parser false-positive rate | Any confirmed false positive on a field-presence check (`has_security_context`, `has_resource_limits`, `has_liveness_probe`, `has_readiness_probe`) in CI or production input | Regression test failure or filed issue with reproducing manifest |
| `:latest` regex false-positive regression | Any CI failure in the four `_IMAGE_LATEST_RE` regression tests | `tests/test_parser.py` output |
| Detection layer requires value extraction | T2 or any subsequent task slice requires reading a numeric, boolean, or enum value from a YAML field (e.g., `minAvailable`, `replicas`, `runAsNonRoot`) | Task slice spec or seam contract references field-value extraction |
| Multi-document manifests enter the corpus | Any artefact in `artefacts/` or test fixture in `tests/` uses a `---` document separator | `grep -r "^---" artefacts/ tests/` returns a result |
| Anchor or alias usage enters the corpus | Any artefact or test fixture uses YAML anchors (`&`) or aliases (`*`) | `grep -r "[&*]" artefacts/ tests/` returns a YAML anchor or alias |
| Dependency policy changes | `CLAUDE.md` escalation gate for new dependencies is explicitly lifted or modified by project authority | `CLAUDE.md §Escalation Gates` diff |
| `input_kind` comment false positive confirmed | A test or review documents a manifest where a comment containing `kind: <Kind>` causes incorrect `input_kind` detection | Issue filed with reproducing input |

If any two signals from this table are observed simultaneously, the decision should be revisited before the next kata slice begins.

---

## Conclusion

The Reference Engine should continue using the lightweight pattern-based parser for Kubernetes manifest inspection.

The pattern-based approach is correct for the current corpus, is fully tested, carries zero runtime dependencies, and respects the project's documented architectural governance. The correctness improvements offered by a structured YAML parser are real but premature relative to the current kata scope and the uncleared dependency escalation gate.

The decision remains open to reversal when the detection layer requires value-level YAML extraction, when the corpus introduces structures that defeat the current regex suite, or when the dependency governance policy changes. These are the engineering signals to monitor.

**Status: APPROVED**
