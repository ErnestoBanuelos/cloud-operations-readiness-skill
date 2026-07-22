# Operational Drift Analysis — Feature Specification

**Skill:** cloud-operations-analysis  
**Capability:** Operational Drift Analysis  
**Spec version:** 1.0.1  
**Status:** Draft — Audit amendments applied (AUDIT-ODA-01 INCORPORATE, AUDIT-ODA-02 INCORPORATE, AUDIT-ODA-03 DEFER)  
**Author role:** Senior Software Architect  
**Date:** 2026-07-22  
**Kata:** K 5.D.4  

---

## Purpose

Compare two infrastructure states — a baseline state and a current state — and produce a
structured operational drift assessment. The capability identifies added components, removed
components, modified components, operational impact, risk level, and recommended engineering
review actions. It does not execute changes. All findings are presented as structured output
for human review and escalation.

---

## 1. Behaviour

### 1.1 Overview

The Drift Analysis capability accepts two infrastructure state snapshots — **State A
(baseline)** and **State B (current)** — and produces a single **Drift Report**. It operates
inside the existing Skill boundary: read-only, no write commands, all remediation escalated to
named roles.

A state snapshot is any combination of the following artefact types:

| Artefact type | Examples |
|---|---|
| Deployment manifest | Kubernetes Deployment YAML, Helm values file, Terraform plan output |
| CI/CD workflow | GitHub Actions YAML, pipeline definition |
| Cost estimate | Monthly cost sheet with line items |
| Readiness brief | Readiness question answers, verdict |
| Stack map | Component ownership map, topology diagram notes |
| Incident runbook | Runbook version, escalation contacts |

A state snapshot must contain at least one artefact. When fewer than one artefact is supplied
for either state, the capability emits a `MISSING_INPUT` error (see Section 3).

### 1.2 Drift Detection Logic

The capability applies the following detection logic in the order shown:

1. **Component identification** — enumerate every named component in State A and State B.
   A component is any discrete named element: a Kubernetes resource (Deployment, Service,
   ConfigMap, Secret, PDB, NetworkPolicy, ServiceAccount), a CI/CD job, a cost line item,
   a stack-map node, or a readiness question answer.

2. **Added components** — components present in State B but absent in State A. Each added
   component is listed with its type, name, owning team label (`[ops]` or `[mine/Product]`
   when determinable, otherwise `UNKNOWN — owner needed`), and an initial risk assessment.

3. **Removed components** — components present in State A but absent in State B. Each removed
   component is listed with its type, name, owning team label, and an initial risk assessment.
   Removal of safety-relevant components (PDB, securityContext, readiness probe) is
   automatically classified as risk level HIGH.

4. **Modified components** — components present in both states whose values differ. Each
   modified component is listed with its type, name, the changed field(s), State A value,
   State B value, and an initial risk assessment.

5. **Operational impact assessment** — a structured summary of what the detected drift means
   for the running service. Stated in terms of availability, security posture, cost, and
   deployability.

6. **Risk level** — a single overall risk classification for the entire drift set:

   | Risk level | Trigger condition |
   |---|---|
   | LOW | All changes are additive with no safety-relevant removals; no modified security fields |
   | MEDIUM | At least one modification to a non-safety field; or at least one added component with undetermined ownership |
   | HIGH | At least one removal of a safety-relevant component; or any security context field modified; or image tag changed to mutable reference |
   | CRITICAL | Any write-command artefact detected in State B that was absent in State A; or any component whose removal would cause the effective replica count in State B to fall below the `minAvailable` value declared in the PodDisruptionBudget present in State A. When no PodDisruptionBudget is present in State A, this trigger does not apply and the removal is classified as HIGH. The capability reads `minAvailable` from the PDB artefact field; it does not query live cluster state. |

7. **Recommended engineering review** — a list of up to five named, role-attributed actions
   using the standard escalation block format (Action / Role / Condition / Artefact). Actions
   are ranked by risk level descending. The capability never recommends execution of write
   commands.

### 1.3 Output Structure

Every Drift Report contains the following fixed sections in the following order:

```
## DRIFT REPORT

### Drift Summary
[Table: State A identifier, State B identifier, components analysed, drift count by category]

### Added Components
[Table or "None detected"]

### Removed Components
[Table or "None detected"]

### Modified Components
[Table or "None detected"]

### Operational Impact
[Structured narrative: availability / security posture / cost / deployability]

### Risk Level
[Single classification: LOW / MEDIUM / HIGH / CRITICAL with rationale]

### Recommended Engineering Review
[Up to 5 escalation blocks: Action / Role / Condition / Artefact]

### Gap Log
[Any UNKNOWN — owner needed entries or missing evidence items]
```

No section may be omitted. If a section has no content, it must contain the literal string
`None detected` or `No gaps recorded` as appropriate.

### 1.4 Confidence and Evidence Rules

- Every finding must cite the artefact and field from which it was derived.
- A finding with no citable evidence must be recorded as `UNKNOWN — owner needed`.
- The capability never infers a drift finding from contextual knowledge alone. Drift is only
  asserted when the delta is directly observable in the supplied artefacts.
- The Gap Log records every unknown and every missing artefact field using the format
  inherited from the existing Skill:

  ```
  Gap: <description>
  Impact: <what cannot be determined without this information>
  Owner needed: <role or team>
  ```

### 1.5 Relationship to Existing Skill Output Types

Drift Analysis is a fifth output type alongside DIAGNOSIS, AUDIT, COST, and READINESS. It
does not replace any existing output type. An engineer may request Drift Analysis as a
standalone operation or as a precursor to READINESS.

When Drift Analysis is requested before a READINESS review, the Drift Report's risk level
feeds the readiness verdict: a CRITICAL drift risk level prevents a `Ready` verdict.

### 1.6 Acceptance Criteria

**AC-1 — Added component detection**

- **Given** a State A snapshot containing a Kubernetes Deployment with two containers and a
  State B snapshot containing the same Deployment plus a sidecar container and a new
  NetworkPolicy resource
- **When** Drift Analysis is invoked with State A and State B as inputs
- **Then** the Drift Report lists exactly two added components (the sidecar container and the
  NetworkPolicy), assigns each an owning team label or `UNKNOWN — owner needed` when
  undeterminable, and records no false positives in the Added Components section

**AC-2 — Safety-relevant removal triggers HIGH risk**

- **Given** a State A snapshot containing a PodDisruptionBudget with `minAvailable: 2` and
  a State B snapshot in which the PodDisruptionBudget is absent
- **When** Drift Analysis is invoked with State A and State B as inputs
- **Then** the Drift Report lists the PodDisruptionBudget in the Removed Components section,
  the overall Risk Level is classified as HIGH, and the Recommended Engineering Review
  contains at least one escalation block citing the PDB removal with a named role

**AC-3 — Modified security field detected and reported**

- **Given** a State A snapshot in which the Deployment securityContext sets
  `runAsNonRoot: true` and `readOnlyRootFilesystem: true`, and a State B snapshot in which
  `readOnlyRootFilesystem` is absent from the securityContext
- **When** Drift Analysis is invoked with State A and State B as inputs
- **Then** the Drift Report lists `readOnlyRootFilesystem` in the Modified Components section
  with State A value `true` and State B value `absent`, the overall Risk Level is classified
  as HIGH, and the Gap Log records the owning team if undetermined

**AC-4 — No drift produces a clean report**

- **Given** a State A snapshot and a State B snapshot that are byte-for-byte identical in
  all supplied artefact fields
- **When** Drift Analysis is invoked with State A and State B as inputs
- **Then** the Drift Report records `None detected` in each of the Added, Removed, and
  Modified Components sections, the Risk Level is LOW, and the Recommended Engineering
  Review section contains `None detected`

---

## 2. Concurrency

### 2.1 Execution Model

The capability is stateless and synchronous. It processes exactly one Drift Analysis request
per invocation. No internal state is retained between invocations. There are no background
threads, queues, or asynchronous operations.

### 2.2 Parallel Invocation Constraint

When two or more Drift Analysis requests are active simultaneously (e.g., a user provides
multiple pairs of states in a single message), each pair must be processed independently and
in declaration order. The output must label each Drift Report with the pair identifier
(`Pair 1`, `Pair 2`, etc.) and must not merge findings across pairs.

If more than three pairs are provided in a single invocation, the capability emits an
`INPUT_LIMIT_EXCEEDED` error (see Section 3) and processes no pairs until the input is
reduced.

### 2.3 Shared Resource Access

The capability reads only the artefacts provided in the request. It does not read live
system state, external APIs, or any shared mutable resource. There are no race conditions,
lock requirements, or atomicity concerns.

### 2.4 Idempotency

Given identical inputs, the capability produces identical output. The Drift Report is
deterministic: the same State A and State B always produce the same findings, risk level,
and escalation blocks.

---

## 3. Errors

All error responses follow the existing Skill escalation block format and are emitted in
place of the Drift Report.

### 3.1 Error Catalogue

| Error code | Trigger condition | Required output |
|---|---|---|
| `MISSING_INPUT` | Fewer than one artefact supplied for State A or State B | State the missing state identifier, list what was received, request the missing artefact |
| `AMBIGUOUS_STATE` | A supplied artefact cannot be unambiguously assigned to State A or State B | State the ambiguous artefact name, request clarification of which state it belongs to |
| `UNPARSEABLE_ARTEFACT` | A supplied artefact contains no machine-readable fields (e.g., free-form prose with no structured data) | Name the artefact, state what structure was expected, request a structured replacement |
| `INPUT_LIMIT_EXCEEDED` | More than three state pairs provided in a single invocation | State the limit, list the pairs received, request the input be split across invocations |
| `WRITE_COMMAND_DETECTED` | State B contains an artefact with a write command that was absent in State A | Refuse to proceed, name the write command and artefact, escalate to the named owner role |

### 3.2 Error Format

Every error follows the format:

```
## DRIFT ANALYSIS ERROR

Error: <ERROR_CODE>
Artefact: <artefact name or "Not applicable">
Detail: <one-sentence description of what was received>
Required: <one-sentence description of what is needed to proceed>
Escalation (if applicable): Action / Role / Condition / Artefact
```

### 3.3 Partial Artefact Sets

When State A or State B is partially supplied (some artefact types present, others absent),
the capability proceeds with the available artefacts. Every finding derived from an
incomplete artefact set is annotated with:

```
Note: State [A/B] artefact set is partial. Findings reflect only the supplied artefacts.
      Missing artefact types: <list>
      Gap: <description>
      Impact: <what cannot be determined>
      Owner needed: <role>
```

This is not an error; it is a degraded-mode execution recorded in the Gap Log.

---

## 4. Boundaries

### 4.1 Read-Only Constraint

The Drift Analysis capability inherits the absolute read-only constraint from the parent
Skill. It never recommends, generates, or implies any write command. The `WRITE_COMMAND_DETECTED`
error (Section 3.1) is the only mechanism by which write commands are referenced, and only to
refuse and escalate.

### 4.2 Scope of Comparison

The capability compares only artefacts explicitly provided. It does not:

- Query live Kubernetes clusters, cloud APIs, or CI/CD systems.
- Infer the contents of missing artefacts from contextual knowledge.
- Cross-reference artefacts with external registries, cost databases, or third-party tooling.
- Produce compliance verdicts (e.g., SOC 2, ISO 27001) — compliance mapping is out of scope.

### 4.3 Component Granularity

The minimum granularity of a drift finding is a named field within a named component.
The capability does not produce byte-level diffs of file content. String values are compared
as opaque tokens unless the field is a known security-relevant field (image tag, securityContext
sub-field, RBAC verb, PDB threshold), in which case the comparison also evaluates the
security direction of the change (hardening vs weakening).

### 4.4 State Identifier Requirements

Each state snapshot must carry an identifier. Accepted identifier forms:

| Form | Example |
|---|---|
| Semantic version | `v1.2.0` |
| Timestamp (ISO 8601) | `2026-07-22T14:00:00Z` |
| Git SHA (short or full) | `a1b2c3d` |
| Deployment label | `pre-deployment`, `post-deployment` |
| Freeform label | `baseline`, `current`, `candidate` |

When no identifier is supplied, the capability assigns `State-A` and `State-B` as defaults
and records the absence in the Gap Log.

### 4.5 Ownership Label Boundary

The capability assigns ownership labels (`[ops]` or `[mine/Product]`) only when the artefact
explicitly carries the label or when the component type maps unambiguously to an ownership
pattern defined in the Context Bundle. It never infers ownership from component name alone.
Undetermined ownership is always recorded as `UNKNOWN — owner needed`.

### 4.6 Out-of-Scope Items

The following are explicitly outside the boundary of this capability:

- Remediation execution or script generation.
- Automated deployment of either state.
- Version control operations (git merge, rebase, cherry-pick).
- Compliance framework mapping.
- Drift detection from live system state (only artefact-to-artefact comparison is in scope).
- Cost delta calculation when cost artefacts are absent from either state.

---

## 5. Integrations

### 5.1 Parent Skill Integration

Operational Drift Analysis is invoked via the same entry point as all other Skill output
types. The routing rule added to the Skill is:

```
If the input contains two labelled infrastructure state snapshots (State A and State B),
route to Drift Analysis. If the input contains exactly one labelled state snapshot and the
other state is absent, route to Drift Analysis and immediately emit a MISSING_INPUT error
requesting the missing state. Do not route to any other output type on the basis of a
partial drift input.
```

The capability shares the following with the parent Skill:

| Shared element | Inherited from |
|---|---|
| Read-only constraint | SKILL.md — DO/DON'T table, Safety Statement |
| Escalation block format | SKILL.md — Escalation Policy |
| `UNKNOWN — owner needed` convention | CLAUDE.md — Rule 3 |
| Gap Log format | `context/cold/gap-log.md` and `docs/context/stack.md` |
| Ownership labels `[ops]` / `[mine/Product]` | CLAUDE.md — Repository Context |
| Refusal of write commands | SKILL.md — Tool Allowlist |

### 5.2 READINESS Integration

When Drift Analysis precedes a READINESS review in the same session:

- The Drift Report's risk level is carried forward as an input to the Readiness verdict.
- A CRITICAL risk level is a hard block: the Readiness verdict cannot be `Ready`.
- A HIGH risk level contributes at least one item to the Maturity Gaps section of the
  Readiness output.
- The Drift Report's Gap Log entries are merged into the Readiness Gap Log without
  duplication.

This integration is unidirectional: READINESS does not feed back into Drift Analysis.

### 5.3 AUDIT Integration

When Drift Analysis is requested on the same artefact set as an AUDIT:

- The AUDIT checklist operates on a single state (State B, the current state).
- The Drift Report operates on the delta between states.
- The two outputs are independent and must not be merged into a single section.
- The recommended ordering is: Drift Analysis first, then AUDIT on State B.

### 5.4 COST Integration

When both states include cost artefacts, the capability produces a Cost Delta sub-section
within the Operational Impact section:

```
### Cost Delta
State A monthly total: $X
State B monthly total: $Y
Delta: $Z (+/-N%)
Attribution change: [ops] delta / [mine/Product] delta
Hard cap status: [within cap / approaching cap / exceeds cap]
```

When cost artefacts are absent from either state, the Cost Delta sub-section is replaced by:

```
### Cost Delta
UNKNOWN — owner needed. Supply cost artefacts for both states to enable cost delta analysis.
```

### 5.5 Cold Context Integration

If a drift finding references a component whose ownership, rationale, or history is recorded
in `context/cold/gap-log.md`, the capability must cross-reference the relevant gap entry and
note it in the Drift Report's Gap Log. This cross-reference is informational and does not
alter the finding.

---

## 6. NFR Budget

All values are measurable against a single Drift Analysis invocation on artefact sets of
the reference size defined in 6.1.

### 6.1 Reference Artefact Set Size

The reference size for all NFR measurements is:

- State A: 6 artefacts totalling ≤ 2,000 lines of YAML/Markdown combined.
- State B: 6 artefacts totalling ≤ 2,000 lines of YAML/Markdown combined.
- Total input token budget: ≤ 24,000 tokens (inclusive of both states and the system prompt).

All NFR values below are specified at reference size. Deviations above reference size are
recorded in the Gap Log as NFR pressure items.

### 6.2 Completeness

| Metric | Target | Measurement method |
|---|---|---|
| Section completeness | 100% of the 8 mandatory Drift Report sections present | Count sections in output; zero omissions permitted |
| Finding coverage | ≥ 95% of directly observable deltas reported | Manually inject 20 known deltas into a test pair; count detected |
| False positive rate | ≤ 5% of reported findings have no corresponding artefact delta | Manually review reported findings against source artefacts |
| `UNKNOWN — owner needed` accuracy | 100% of ownership gaps recorded; 0% of fabricated ownership labels | Manual review of all ownership assignments |

### 6.3 Output Structure Compliance

| Metric | Target | Measurement method |
|---|---|---|
| Section order compliance | 100% of reports have sections in the specified order | Automated header-order check against spec |
| Escalation block format compliance | 100% of escalation blocks contain all four fields (Action / Role / Condition / Artefact) | Automated field presence check |
| Risk level vocabulary compliance | 100% of risk level values are exactly one of: LOW / MEDIUM / HIGH / CRITICAL | Automated vocabulary check |
| Maximum escalation actions | ≤ 5 escalation blocks per Drift Report | Count blocks in output |

### 6.4 Safety and Constraint Compliance

| Metric | Target | Measurement method |
|---|---|---|
| Write command generation rate | 0 write commands generated per 100 Drift Analysis invocations | Execute 100 invocations including adversarial prompts; count write commands in output |
| `WRITE_COMMAND_DETECTED` precision | 100% of write commands in State B artefacts trigger the error | Inject 10 state pairs each containing one write command; verify all 10 trigger the error |
| Read-only constraint breach rate | 0 breaches per 100 invocations | Same adversarial test set |

### 6.5 Consistency

| Metric | Target | Measurement method |
|---|---|---|
| Idempotency | Given identical inputs, output is identical across 10 repeated invocations | Run same pair 10 times; diff outputs |
| Risk level consistency | The same delta set produces the same risk level across 10 invocations | Run same pair 10 times; check risk level field |

### 6.6 Token Efficiency

| Metric | Target | Measurement method |
|---|---|---|
| Output token count — reference size | ≤ 2,000 output tokens per Drift Report at reference size | Measure output token count per invocation |
| Output token count — minimal input (1 artefact per state) | ≤ 500 output tokens | Measure output token count with minimal input pair |
| Prompt repetition rate | Gap Log entries not duplicated within a single Drift Report | Automated duplicate-entry check |

> **Note (AUDIT-ODA-03 — DEFERRED):** Token measurement method is deferred pending
> agreement on a shared tokeniser. Until a tokeniser is confirmed, token targets are
> verified by character-count proxy: ≤ 8,000 characters per Drift Report at reference
> size; ≤ 2,000 characters for minimal-input pairs. Update this note when tokeniser
> tooling is confirmed.

### 6.7 Error Handling

| Metric | Target | Measurement method |
|---|---|---|
| `MISSING_INPUT` trigger accuracy | 100% triggered when fewer than 1 artefact per state | Inject 10 missing-state pairs; verify all trigger error |
| `INPUT_LIMIT_EXCEEDED` trigger accuracy | 100% triggered when > 3 pairs supplied | Inject 5 over-limit requests; verify all trigger error |
| Error format compliance | 100% of error responses contain all 5 required fields | Automated field presence check |
