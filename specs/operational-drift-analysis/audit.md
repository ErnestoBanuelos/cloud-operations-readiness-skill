# Operational Drift Analysis — Specification Audit

**Spec under review:** `specs/operational-drift-analysis/spec.md`  
**Spec version:** 1.0.0  
**Audit version:** 1.0.0  
**Kata:** K 5.D.4  
**Date:** 2026-07-22  
**Isolation tier:** A — The reviewer has not participated in authoring this specification.
The audit is conducted solely from the written text of spec.md. No context beyond the
specification and the repository's existing engineering conventions is used.

---

## Isolation Statement

This audit is conducted at **Isolation Tier A**. The auditor has not authored, co-authored,
or reviewed any draft of this specification prior to this audit. The audit examines only
what is written in the specification. No benefit of the doubt is extended for omissions.
Assumptions are not made. Every finding is grounded in the specification text.

---

## Audit Scope

The following sections were examined:

1. Behaviour (Section 1)
2. Concurrency (Section 2)
3. Errors (Section 3)
4. Boundaries (Section 4)
5. Integrations (Section 5)
6. NFR Budget (Section 6)
7. Acceptance Criteria (Section 1.6)

---

## Finding 1

**ID:** AUDIT-ODA-01  
**Section:** 1.2 Drift Detection Logic — Step 6, Risk Level Classification Table  
**Severity:** High  
**Finding title:** Risk level CRITICAL trigger condition is underspecified — "minimum-replica
guarantee" is undefined in this specification

**Observation:**

Section 1.2, Step 6 defines four risk levels. The CRITICAL trigger condition includes:

> "any component whose removal would violate minimum-replica guarantee"

The term "minimum-replica guarantee" is not defined anywhere in this specification. The
specification does not state:

- What the minimum-replica value is.
- Where that value is sourced from (artefact field, external policy, hard-coded constant).
- How the capability determines what the current replica count is in State B.
- Whether the capability reads the PDB `minAvailable` field, the Deployment `replicas` field,
  or an external policy document.

An engineer implementing this rule cannot determine what to compare against. Without a defined
source value, this trigger condition is unimplementable as written.

**Resolution chosen:** INCORPORATE

**Rationale for resolution:** The finding is technically correct. The trigger condition as
written would produce inconsistent implementations. The specification must define the source
of the minimum-replica guarantee and its evaluation logic.

**Spec update applied:**

In Section 1.2, Step 6, the CRITICAL row of the risk level table is updated to:

> "Any component whose removal would cause the effective replica count in State B to fall
> below the `minAvailable` value declared in the PodDisruptionBudget present in State A.
> When no PodDisruptionBudget is present in State A, this trigger does not apply and the
> removal is classified as HIGH. The capability reads `minAvailable` from the PDB artefact
> field; it does not query live cluster state."

---

## Finding 2

**ID:** AUDIT-ODA-02  
**Section:** 5.1 Parent Skill Integration — Routing Rule  
**Severity:** Medium  
**Finding title:** Routing rule is ambiguous — it does not specify behaviour when only one
labelled state is provided

**Observation:**

Section 5.1 states the routing rule as:

> "If the input contains two labelled infrastructure state snapshots (State A and State B),
> route to Drift Analysis."

This rule specifies the positive case (both states present) but is silent on the partial
case: what happens when the input contains exactly one labelled state. The specification
does not state whether the capability:

(a) Routes to Drift Analysis and immediately emits a `MISSING_INPUT` error.  
(b) Does not route to Drift Analysis and instead routes to a different output type.  
(c) Prompts the user to supply the missing state before routing.

The `MISSING_INPUT` error in Section 3.1 handles the error after routing, but the routing
decision itself is unspecified for the single-state case. An engineer implementing the
routing layer cannot determine which path to take.

**Resolution chosen:** INCORPORATE

**Rationale for resolution:** The routing rule must cover the partial input case. The correct
behaviour is (a): route to Drift Analysis and emit `MISSING_INPUT`. This is consistent with
the existing Skill convention of entering the output type and then validating inputs, as
demonstrated in RUN-001 in run-log.md ("correctly requested inputs before proceeding").

**Spec update applied:**

In Section 5.1, the routing rule is extended to:

> "If the input contains two labelled infrastructure state snapshots (State A and State B),
> route to Drift Analysis. If the input contains exactly one labelled state snapshot and the
> other state is absent, route to Drift Analysis and immediately emit a `MISSING_INPUT` error
> requesting the missing state. Do not route to any other output type on the basis of a
> partial drift input."

---

## Finding 3

**ID:** AUDIT-ODA-03  
**Section:** 6.6 Token Efficiency — NFR Budget  
**Severity:** Low  
**Finding title:** Token efficiency NFR targets are not independently verifiable — "reference
size" and "output token count" measurement methods depend on tooling not specified

**Observation:**

Section 6.6 specifies:

> "Output token count — reference size: ≤ 2,000 output tokens per Drift Report at reference
> size. Measurement method: Measure output token count per invocation."

The measurement method "Measure output token count per invocation" does not specify:

- Which tokeniser to use (GPT-4 cl100k_base, Claude tokeniser, character-count proxy).
- Whether system prompt tokens are included in the output count or only response tokens.
- What tooling or command is used to perform the measurement.
- Whether the measurement is performed in automated CI or manually.

Without a defined tokeniser and measurement command, two engineers will produce different
measurements for the same output. The NFR target of ≤ 2,000 tokens is numerically precise
but practically unverifiable without a shared measurement instrument.

**Resolution chosen:** DEFER

**Rationale for resolution:** Specifying the tokeniser requires selecting a concrete model
and tooling dependency. The existing Skill lists `tested_clients: claude-sonnet-4-6` but
does not commit to a tokeniser in any specification artefact. Introducing a tokeniser
dependency in this specification would create a coupling that is outside the scope of K 5.D.4
and would require an engineering decision (new dependency) that the Escalation Gates in
CLAUDE.md require to be stopped at. The finding is valid and recorded. Resolution is deferred
to the next engineering iteration when model selection and tokeniser tooling are decided.

**Gap entry added to spec Section 6.6:**

> "Note: Token measurement method is deferred (AUDIT-ODA-03). Until a shared tokeniser is
> agreed, token targets are verified by character-count proxy: ≤ 8,000 characters per Drift
> Report at reference size; ≤ 2,000 characters for minimal-input pairs. Update this note
> when tokeniser tooling is confirmed."

---

## Audit Summary Table

| Finding ID | Section | Severity | Title (abbreviated) | Resolution |
|---|---|---|---|---|
| AUDIT-ODA-01 | 1.2 — Risk level table | High | CRITICAL trigger underspecified — "minimum-replica guarantee" undefined | INCORPORATE |
| AUDIT-ODA-02 | 5.1 — Routing rule | Medium | Routing rule silent on single-state input | INCORPORATE |
| AUDIT-ODA-03 | 6.6 — Token efficiency | Low | Token NFR measurement method unverifiable without defined tokeniser | DEFER |

---

## Spec Update Record

The following changes were applied to `spec.md` as a result of this audit:

### Change 1 — AUDIT-ODA-01 INCORPORATED

**Location:** Section 1.2, Step 6, Risk Level table, CRITICAL row  
**Before:**

> "Any component whose removal would violate minimum-replica guarantee"

**After:**

> "Any component whose removal would cause the effective replica count in State B to fall
> below the `minAvailable` value declared in the PodDisruptionBudget present in State A.
> When no PodDisruptionBudget is present in State A, this trigger does not apply and the
> removal is classified as HIGH. The capability reads `minAvailable` from the PDB artefact
> field; it does not query live cluster state."

### Change 2 — AUDIT-ODA-02 INCORPORATED

**Location:** Section 5.1, routing rule paragraph  
**Before:**

> "If the input contains two labelled infrastructure state snapshots (State A and State B),
> route to Drift Analysis."

**After:**

> "If the input contains two labelled infrastructure state snapshots (State A and State B),
> route to Drift Analysis. If the input contains exactly one labelled state snapshot and the
> other state is absent, route to Drift Analysis and immediately emit a `MISSING_INPUT` error
> requesting the missing state. Do not route to any other output type on the basis of a
> partial drift input."

### Change 3 — AUDIT-ODA-03 DEFERRED

**Location:** Section 6.6, output token count rows  
**Added note:**

> "Note: Token measurement method is deferred (AUDIT-ODA-03). Until a shared tokeniser is
> agreed, token targets are verified by character-count proxy: ≤ 8,000 characters per Drift
> Report at reference size; ≤ 2,000 characters for minimal-input pairs. Update this note
> when tokeniser tooling is confirmed."

---

## Audit Completion Statement

Three findings were produced. All three findings were reviewed and assigned resolutions.
Two findings (AUDIT-ODA-01, AUDIT-ODA-02) were INCORPORATED and the specification was
updated accordingly. One finding (AUDIT-ODA-03) was DEFERRED with a documented interim
measurement proxy. No findings were REJECTED. The specification is cleared for Engineering
Review at the current version.
