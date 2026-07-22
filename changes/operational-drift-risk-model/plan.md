# Implementation Plan — Operational Drift Risk Model Extension

**Plan version:** 1.0.0
**Delta source:** changes/operational-drift-risk-model/delta.md — version 1.0.0
**Baseline spec:** specs/operational-drift-analysis/spec.md — version 1.0.1
**Target spec version:** 1.1.0
**Kata:** K 5.D.6
**Date:** 2026-07-22
**Status:** Planning artefact — no implementation included

---

## How the Change Propagates

The delta formalises CRITICAL as a first-class risk level across the entire
Drift Analysis capability. The propagation path is:

```
Risk Classification Logic (M-1)
        │
        ├──► Output Schema: Risk Level section (M-2)
        │         └──► READINESS IMPACT annotation (A-3)
        │
        ├──► Escalation Cap Rule (M-3)
        │         └──► Mandatory executive escalation block (A-2)
        │
        ├──► NFR Vocabulary Check (A-4)
        │
        ├──► Acceptance Criteria (M-4 / A-5)
        │
        └──► Spec Version Bump (M-6)
```

Every downstream component depends on the Risk Classification Logic as its
upstream input. No component modifies the upstream logic; each extends or
constrains the output contract for exactly one concern.

---

## Component 1 — Risk Classification Logic

**Delta items:** A-1, M-1, Risk Note (HIGH/CRITICAL boundary)

### Responsibility

Determine the correct risk level — LOW, MEDIUM, HIGH, or CRITICAL — from a
given set of drift findings. This component is the single source of truth for
the four-level severity ordering:

```
LOW < MEDIUM < HIGH < CRITICAL
```

It evaluates, in priority order:

1. CRITICAL trigger: write-command artefact present in State B, absent in
   State A.
2. CRITICAL trigger: replica count in State B falls below `minAvailable` from
   the PDB in State A. This trigger applies **only when a PDB is present in
   State A**. When no PDB is present, the evaluation falls through to the HIGH
   branch.
3. HIGH trigger: removal of a safety-relevant component; security context field
   modified; image tag changed to mutable reference.
4. MEDIUM trigger: modification to a non-safety field; added component with
   undetermined ownership.
5. LOW: all other cases.

The HIGH/CRITICAL boundary condition (PDB presence carve-out) is the
highest-risk area. The evaluation order must ensure that the absence of a PDB
in State A does not accidentally produce a CRITICAL output.

### Inputs

- Set of drift findings (added, removed, modified components) produced by
  the existing drift detection logic.
- State A artefact set — specifically the PDB field `minAvailable` when
  present.
- State B artefact set — specifically the Deployment `replicas` field and
  the presence or absence of write-command artefacts.

### Outputs

- A single risk level value: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
- A rationale string (one sentence) citing the trigger condition that
  produced the classification.
- A boolean flag: `critical_active` — true when risk level is CRITICAL,
  false otherwise. This flag gates all downstream CRITICAL-specific behaviour.

### Interface Contract

The Risk Classification Logic accepts drift findings and state artefacts and
emits exactly one risk level token plus a `critical_active` boolean; all
downstream components consume only these outputs and must not re-evaluate
the findings themselves.

---

## Component 2 — Risk Level Section Formatter

**Delta items:** M-2, A-3, R-4

### Responsibility

Render the Risk Level section of the Drift Report for all four risk levels.
When `critical_active` is true, append the mandatory READINESS IMPACT
annotation defined in A-3:

```
READINESS IMPACT: CRITICAL risk level is a hard block.
A Ready verdict cannot be issued until this risk level is resolved.
```

This annotation must not appear for LOW, MEDIUM, or HIGH outputs. The
formatter is the only component that writes to the Risk Level section.

### Inputs

- Risk level token (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`) from Component 1.
- Rationale string from Component 1.
- `critical_active` boolean from Component 1.

### Outputs

- The complete Risk Level section text, ready for inclusion in the Drift
  Report output. For CRITICAL outputs the text includes the READINESS IMPACT
  annotation. For all other risk levels the text is structurally unchanged
  from spec v1.0.1.

### Interface Contract

The Risk Level Section Formatter accepts the risk level token and the
`critical_active` flag and produces a fully-formed, self-contained section
string; it does not read artefacts or findings directly.

---

## Component 3 — Escalation Block Builder

**Delta items:** A-2, M-3, R-3

### Responsibility

Construct the Recommended Engineering Review section. Enforce the conditional
escalation block cap:

- When `critical_active` is false: cap is 5 blocks (spec v1.0.1 behaviour,
  unchanged).
- When `critical_active` is true: cap is 6 blocks. The mandatory executive
  escalation block is injected as one of the six and must always be present:

  ```
  Action:    Escalate to engineering leadership and executive sponsor
  Role:      Engineering Lead / Executive Sponsor
  Condition: Risk level is CRITICAL
  Artefact:  Drift Report — Risk Level section
  ```

  The mandatory block is prepended (highest prominence). The remaining up to
  five slots are filled with ranked engineering actions as before.

This component is also responsible for enforcing the read-only constraint:
no escalation block may recommend a write command.

### Inputs

- `critical_active` boolean from Component 1.
- Ranked list of engineering actions derived from the drift findings (existing
  escalation logic, unchanged).

### Outputs

- The complete Recommended Engineering Review section text containing 1–5
  blocks (non-CRITICAL) or 2–6 blocks (CRITICAL, mandatory block always
  present).

### Interface Contract

The Escalation Block Builder accepts the `critical_active` flag and a ranked
action list and emits a complete Recommended Engineering Review section that
is capped at 5 blocks when `critical_active` is false and 6 blocks when true.

---

## Component 4 — NFR Vocabulary Validator

**Delta items:** A-4, R-1, R-2

### Responsibility

Validate that the risk level field in any produced Drift Report is exactly one
of the four permitted vocabulary tokens:

```
LOW | MEDIUM | HIGH | CRITICAL
```

Previously CRITICAL was listed in the vocabulary but had no trigger path
in the acceptance criteria; a validator could assert it was never produced.
After this delta, CRITICAL is a valid, producible output. The validator must:

1. Accept CRITICAL as a non-error value (not a warning, not an anomaly).
2. Reject any value outside the four-token set.
3. Be updated in any test harness that previously asserted CRITICAL was
   unreachable.

This component is a verification/testing concern, not a runtime concern. It
represents the set of changes required to test infrastructure and NFR
measurement tooling.

### Inputs

- A Drift Report output (or the risk level field extracted from it).

### Outputs

- A pass/fail result: PASS when the risk level is one of the four tokens,
  FAIL otherwise.
- A note when CRITICAL is observed, confirming it was produced by a valid
  trigger path (for audit trail purposes).

### Interface Contract

The NFR Vocabulary Validator accepts a risk level field value and emits
PASS or FAIL; it must not reject CRITICAL as an invalid value.

---

## Component 5 — Acceptance Criterion Test Cases

**Delta items:** A-5, M-4, R-5

### Responsibility

Provide the test evidence that exercises the new CRITICAL classification path.
AC-5 is the new acceptance criterion:

> **Given** a State A snapshot containing a PodDisruptionBudget with
> `minAvailable: 2` and a Deployment with `replicas: 3`, and a State B
> snapshot in which the Deployment is modified to `replicas: 1` while the
> PodDisruptionBudget remains present
>
> **When** Drift Analysis is invoked with State A and State B as inputs
>
> **Then** the Drift Report classifies the overall Risk Level as CRITICAL,
> the Risk Level section includes the READINESS IMPACT annotation (A-3),
> and the Recommended Engineering Review contains the mandatory executive
> escalation block (A-2)

This component also includes the **Proof Test** from the delta Risk Note,
which must be recorded alongside AC-5 as a boundary condition test:

> **Given** State A: Deployment with `replicas: 3`, no PDB present.
> State B: Deployment with `replicas: 1`, no PDB present.
>
> **Then** Risk Level is HIGH (not CRITICAL). The READINESS IMPACT annotation
> must NOT be present. The mandatory executive escalation block must NOT be
> present.

These two test cases together bound the HIGH/CRITICAL decision boundary.

### Inputs

- Synthetic State A artefact: Kubernetes Deployment YAML + PDB YAML.
- Synthetic State B artefact: Kubernetes Deployment YAML (replicas reduced).
- Synthetic no-PDB pair: both states contain only a Deployment, no PDB.

### Outputs

- AC-5 test definition (Given / When / Then, referencing synthetic artefacts).
- Proof test definition (Given / When / Then, HIGH-preserved-on-no-PDB).
- Pass/fail verdict for each criterion.

### Interface Contract

The Acceptance Criterion Test Cases component accepts synthetic state
artefact pairs and emits structured test verdicts against each criterion;
it consumes Component 1 output (risk level token) and Components 2–3 output
(section text) to verify the full end-to-end path.

---

## Component 6 — Spec Version Increment

**Delta items:** M-6

### Responsibility

Issue spec version 1.1.0 of `specs/operational-drift-analysis/spec.md`,
incorporating all ADDED and MODIFIED items from the delta. The existing
spec.md must not be overwritten until explicit approval is granted per the
escalation gate in CLAUDE.md:

> "Never overwrite spec.md after sign-off without explicit approval."

This component represents the final delivery gate. It is the last component
to be completed. All other components must be reviewed and accepted before
spec.md is updated.

### Inputs

- Approved diff produced by Components 1–5 (all changes to classification
  logic, output schema, escalation cap, NFR validator, and acceptance criteria).
- Explicit approval signal from the Engineering Lead.

### Outputs

- `specs/operational-drift-analysis/spec.md` at version 1.1.0 with:
  - Section 1.2 Step 6: CRITICAL formally integrated.
  - Section 1.3: Risk Level section format includes A-3 annotation requirement.
  - Section 1.2 Step 7 and Section 6.3: escalation cap updated to conditional.
  - Section 1.6: AC-5 added.
  - Section 5.2: READINESS integration annotation rule formalised.
  - Header: version 1.0.1 → 1.1.0.

### Interface Contract

The Spec Version Increment component accepts an approved set of section edits
and produces an updated spec.md; it must not be applied until all other
components are reviewed and the escalation gate is cleared.

---

## Change Propagation Summary

| From (spec v1.0.1) | To (spec v1.1.0) | Propagation path |
|---|---|---|
| Implicit CRITICAL in risk table (no downstream treatment) | CRITICAL as first-class level | Component 1 produces `critical_active`; Components 2, 3, 4, 5 consume it |
| Risk Level section: clean for all levels | Risk Level section: READINESS IMPACT annotation when CRITICAL | Component 2 conditionally appends annotation |
| Unconditional 5-block escalation cap | Conditional cap (5 / 6) + mandatory executive block | Component 3 enforces conditional cap |
| Vocabulary check: CRITICAL listed but unreachable | Vocabulary check: CRITICAL is a valid, producible token | Component 4 updates validator |
| AC-1–AC-4 cover up to HIGH | AC-5 covers CRITICAL path; proof test covers HIGH boundary | Component 5 adds test evidence |
| spec.md at v1.0.1 | spec.md at v1.1.0 | Component 6 (gated by approval) |

---

*No implementation. Planning artefact only.*
