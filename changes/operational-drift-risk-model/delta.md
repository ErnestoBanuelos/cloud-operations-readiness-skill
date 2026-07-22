# Change

Operational Drift Risk Model Extension

**Delta version:** 1.0.0  
**Baseline spec:** specs/operational-drift-analysis/spec.md — version 1.0.1  
**Status:** Proposed  
**Author role:** Senior Software Architect  
**Date:** 2026-07-22  
**Kata:** K 5.D.5  
**Requested by:** Product Owner (post-approval change request)

---

## Preserved Behaviour

All drift reports produced against LOW, MEDIUM, and HIGH trigger conditions must
continue to emit exactly the same risk level classification, operational impact
narrative, recommended engineering review actions, and output structure as
specified in spec version 1.0.1, without modification.

---

## ADDED

### A-1 — CRITICAL severity classification

A fourth named risk level, `CRITICAL`, is formally introduced into the risk
classification vocabulary. The trigger condition already recorded in spec v1.0.1
Section 1.2, Step 6 is ratified as the authoritative definition:

> Any write-command artefact detected in State B that was absent in State A;
> or any component whose removal would cause the effective replica count in
> State B to fall below the `minAvailable` value declared in the
> PodDisruptionBudget present in State A. When no PodDisruptionBudget is
> present in State A, this trigger does not apply and the removal is
> classified as HIGH. The capability reads `minAvailable` from the PDB
> artefact field; it does not query live cluster state.

The delta formalises CRITICAL as a first-class classification across all
sections of the specification that previously referenced only LOW, MEDIUM,
and HIGH.

### A-2 — Executive escalation recommendation

When the overall risk level is CRITICAL, the Recommended Engineering Review
section must contain at least one escalation block explicitly marked as
requiring executive visibility. The escalation block must carry:

```
Action:    Escalate to engineering leadership and executive sponsor
Role:      Engineering Lead / Executive Sponsor
Condition: Risk level is CRITICAL
Artefact:  Drift Report — Risk Level section
```

This block is mandatory and does not count against the existing cap of five
escalation blocks (see M-3 below for the cap modification).

### A-3 — CRITICAL propagation into READINESS integration

The READINESS integration rule already records that a CRITICAL drift risk level
is a hard block preventing a `Ready` verdict (spec v1.0.1, Section 5.2). This
rule is preserved and extended: the Drift Report must explicitly annotate the
Risk Level section with the text:

```
READINESS IMPACT: CRITICAL risk level is a hard block.
A Ready verdict cannot be issued until this risk level is resolved.
```

This annotation is required only when the risk level is CRITICAL.

### A-4 — Updated NFR vocabulary check target

The NFR metric at spec v1.0.1 Section 6.3 ("Risk level vocabulary compliance")
lists the permitted vocabulary as: `LOW / MEDIUM / HIGH / CRITICAL`. This
target already includes CRITICAL. The delta ratifies CRITICAL as a permitted
value in that automated vocabulary check and requires that any vocabulary
validation tooling or test harness be updated to recognise CRITICAL as a
valid non-error output value.

### A-5 — New acceptance criterion for CRITICAL

A new acceptance criterion is required to cover the CRITICAL trigger path:

**AC-5 — CRITICAL classification triggered by replica-count-below-minAvailable removal**

- **Given** a State A snapshot containing a PodDisruptionBudget with
  `minAvailable: 2` and a Deployment with `replicas: 3`, and a State B
  snapshot in which the Deployment is modified to `replicas: 1` while the
  PodDisruptionBudget remains present
- **When** Drift Analysis is invoked with State A and State B as inputs
- **Then** the Drift Report classifies the overall Risk Level as CRITICAL,
  the Risk Level section includes the READINESS IMPACT annotation (A-3),
  and the Recommended Engineering Review contains the mandatory executive
  escalation block (A-2)

---

## MODIFIED

### M-1 — Risk classification logic

**Before:** The risk classification table in Section 1.2 Step 6 contained four
rows (LOW, MEDIUM, HIGH, CRITICAL). CRITICAL was present in the table text but
had no downstream treatment differentiated from HIGH across the rest of the
specification. All sections outside the table referred implicitly to a
three-level model.

**After:** CRITICAL is explicitly integrated into every section that references
the risk level output. The classification table remains unchanged in its trigger
conditions. No existing LOW, MEDIUM, or HIGH trigger condition is altered. The
ordering of severity from lowest to highest is: LOW < MEDIUM < HIGH < CRITICAL.

### M-2 — Output schema: Risk Level section

**Before:** The Risk Level section in the output structure (Section 1.3) was
documented as emitting `[Single classification: LOW / MEDIUM / HIGH / CRITICAL
with rationale]`. The CRITICAL label was present but the downstream annotation
requirement did not exist.

**After:** When the classification is CRITICAL, the Risk Level section must also
emit the READINESS IMPACT annotation defined in A-3. The section format is
otherwise unchanged for LOW, MEDIUM, and HIGH outputs.

### M-3 — Escalation block cap for CRITICAL reports

**Before:** The Recommended Engineering Review section contained up to five
escalation blocks per Drift Report (Section 1.2 Step 7 and NFR 6.3).

**After:** When the risk level is CRITICAL, the cap is raised to six escalation
blocks to accommodate the mandatory executive escalation block (A-2). The
mandatory block occupies one slot. The remaining five slots are available for
ranked engineering actions as before. The NFR metric "Maximum escalation
actions" at Section 6.3 is updated from `≤ 5` to `≤ 6 when risk level is
CRITICAL; ≤ 5 otherwise`.

### M-4 — Acceptance criteria coverage

**Before:** Acceptance criteria AC-1 through AC-4 covered added component
detection, HIGH risk from safety-relevant removal, HIGH risk from security field
modification, and clean (no-drift) reports.

**After:** AC-5 (defined in A-5) is added to cover the CRITICAL classification
path. AC-1 through AC-4 are unchanged.

### M-5 — READINESS integration rule

**Before:** Section 5.2 stated that a CRITICAL drift risk level is a hard block
preventing a `Ready` verdict. This was a stated rule but lacked an in-report
annotation requirement.

**After:** The rule is unchanged in its verdict-blocking effect. The new A-3
annotation requirement makes the block visible in the Drift Report itself, not
only in the consuming READINESS output.

### M-6 — Spec version and status

**Before:** spec.md version 1.0.1, status Draft.

**After:** A new spec version must be issued (proposed: 1.1.0) incorporating all
ADDED and MODIFIED items. The existing spec.md must not be overwritten until
explicit approval is granted per the escalation gate in CLAUDE.md.

---

## REMOVED

### R-1 — Implicit guarantee that HIGH is the maximum severity

**Before:** Every section of the specification outside the risk classification
table (Section 1.2 Step 6) operated under an implicit three-level model
(LOW / MEDIUM / HIGH). Consumers reading the output contract, acceptance
criteria, and NFR section could reasonably assume that HIGH was the ceiling of
the risk level field.

**After:** CRITICAL is a valid output value. Any consumer, integration, or test
harness that treats HIGH as the maximum severity value — or that maps the risk
level field to a three-element enumeration — will produce incorrect results. The
implicit guarantee that `HIGH` is the maximum severity no longer exists.

### R-2 — Three-level classification assumption in consumers

**Before:** The READINESS integration rule (Section 5.2) stated that a CRITICAL
risk level "prevents a Ready verdict" but the output schema and acceptance
criteria contained no example of a CRITICAL output. A consumer building against
the specification examples could implement a three-level parser without error.

**After:** A CRITICAL output can now be produced and must be handled. A parser
that accepts only LOW, MEDIUM, or HIGH will now reject or misclassify valid
Drift Report output.

### R-3 — Unconditional five-block escalation cap

**Before:** The escalation block cap was an unconditional constraint: every Drift
Report, regardless of risk level, was limited to five escalation blocks.

**After:** The cap is conditional. A CRITICAL report may contain up to six
blocks. The guarantee that "no Drift Report will ever contain more than five
escalation blocks" no longer exists.

### R-4 — Absence of in-report READINESS IMPACT annotation

**Before:** The Drift Report format contained no annotation linking the Risk
Level section directly to the READINESS verdict. The verdict-blocking effect of
CRITICAL was documented only in the READINESS integration section (5.2).

**After:** A CRITICAL risk level causes a mandatory in-report annotation to
appear in the Risk Level section. Report consumers that parse the Risk Level
section by exact-format matching must accommodate the additional annotation text.

---

## REMOVED Audit

**Review question:** "What behaviour existed before that no longer exists?"

Reviewing each removal:

- **R-1** is genuine. The implicit HIGH-as-maximum guarantee existed throughout
  the acceptance criteria (AC-2, AC-3 both assert HIGH and no criterion
  asserted CRITICAL), the NFR vocabulary check (which listed CRITICAL but
  provided no trigger path that would produce it in a test), and the output
  examples. This guarantee disappears.

- **R-2** is genuine. No acceptance criterion or output example demonstrated a
  CRITICAL output. A test engineer implementing against AC-1–AC-4 alone would
  build a three-value parser. That parser is now incomplete.

- **R-3** is genuine. The five-block cap was stated unconditionally in two
  locations (Section 1.2 Step 7 and NFR 6.3). The conditional relaxation is a
  visible caller contract change.

- **R-4** is genuine. The Risk Level section format was clean for all risk
  levels before this change. CRITICAL now injects additional text. Any
  consumer performing exact-string matching on the Risk Level section output
  will break.

**Additional removal identified during audit:**

### R-5 — Guarantee that AC-2 represents the highest-severity acceptance criterion

**Before:** AC-2 (PDB removal → HIGH) was the highest-severity acceptance
criterion in the specification. It established HIGH as the de facto test ceiling.

**After:** AC-5 (replica count below minAvailable → CRITICAL) supersedes AC-2 as
the highest-severity acceptance criterion. The guarantee that "the highest risk
level exercised by an acceptance criterion is HIGH" no longer exists.

**Audit conclusion:** REMOVED is complete. Five genuine removals are identified.
No fabricated removals are included. Each removal describes a previously
caller-visible guarantee that disappears as a direct consequence of the change.

---

## Risk Note

### Highest-Risk Preserved Behaviour

The highest-risk preserved behaviour is:

> All drift reports produced against LOW, MEDIUM, and HIGH trigger conditions
> must continue to emit exactly the same risk level classification, without
> modification.

### Why It Is at Risk

The risk classification logic is a single ordered evaluation. Adding CRITICAL
introduces a new branch evaluated before (or in parallel with) the existing
HIGH branch. An incorrect implementation could short-circuit to CRITICAL on
conditions that the baseline specification classifies as HIGH — specifically
the safety-relevant removal path (PDB absent from State B), which is now a
shared trigger between HIGH (PDB absent, no replica count comparison possible)
and CRITICAL (replica count falls below `minAvailable`). A regression in the
boundary condition — where no PDB is present in State A — could incorrectly
emit CRITICAL when HIGH is required.

### Proof Test

**Proof test: HIGH-preserved-on-no-PDB**

```
Given:
  State A: Deployment with replicas: 3. No PodDisruptionBudget present.
  State B: Deployment with replicas: 1. No PodDisruptionBudget present.

When:
  Drift Analysis is invoked with State A and State B.

Then:
  The Drift Report Risk Level is HIGH (not CRITICAL).
  Rationale: The CRITICAL trigger for replica-count-below-minAvailable
  explicitly does not apply when no PDB is present in State A.
  The removal/modification of replicas is classified as HIGH
  (mutable image or structural change to a non-safety field).
  The mandatory executive escalation block (A-2) must NOT be present.
  The READINESS IMPACT annotation (A-3) must NOT be present.
```

This test directly exercises the boundary between HIGH and CRITICAL and
confirms that the no-PDB carve-out in the CRITICAL trigger definition is
correctly preserved.

---

## Engineering Review

### Is ADDED complete?

Yes. The following newly introduced behaviours are all captured:

- CRITICAL as a named severity (A-1)
- Executive escalation recommendation (A-2)
- In-report READINESS IMPACT annotation (A-3)
- NFR vocabulary check update (A-4)
- New acceptance criterion AC-5 (A-5)

One potential gap considered and rejected: a "notification channel" behaviour
for executive visibility. The specification is read-only and produces structured
output for human review. The mechanism for "executive visibility" is the
escalation block (A-2), which is within scope. A separate notification
integration would require new dependencies and is outside the Skill boundary.
Not added.

### Is MODIFIED complete?

Yes. Every section that contained an implicit or explicit reference to the
three-level model has a corresponding MODIFIED entry:

- M-1: classification logic integration
- M-2: output schema
- M-3: escalation cap
- M-4: acceptance criteria coverage
- M-5: READINESS integration annotation requirement
- M-6: spec version

One potential gap considered and rejected: COST integration (Section 5.4). The
Cost Delta sub-section is driven by artefact presence, not risk level. CRITICAL
does not alter the Cost Delta format. No modification required.

One potential gap considered and rejected: AUDIT integration (Section 5.3). The
AUDIT checklist operates independently of risk level. No modification required.

One potential gap considered and rejected: Error catalogue (Section 3). The
`WRITE_COMMAND_DETECTED` error was already the trigger source for one of the
CRITICAL conditions. The error is emitted and the risk level is set to CRITICAL.
The error format itself does not change. No modification required.

### Is REMOVED honest?

Yes. All five removals (R-1 through R-5) are genuine caller-visible behaviours
that disappear. No speculative removals are included. The spec did not contain:
a formal three-value enum type definition, a parser specification, or a
serialisation schema — therefore removal of those items is not claimed.

### Are any backward compatibility guarantees missing?

One compatibility risk not captured in REMOVED but warranting a note:

The NFR metric at Section 6.3 currently lists `CRITICAL` in the vocabulary
check. An automated vocabulary checker that was built against spec v1.0.1 would
already accept CRITICAL as a valid token. However, a checker that also validated
that CRITICAL was never produced (on the basis that no trigger path existed in
prior acceptance criteria) would now fail. This is a test-harness compatibility
risk, not a specification-level guarantee. It is subsumed by R-2 and does not
require a separate REMOVED entry.

### Would an implementation engineer understand exactly what changed without reading the original specification?

Yes, with one clarification needed: M-1 references the shared boundary between
the HIGH and CRITICAL trigger conditions (PDB present vs absent). An
implementation engineer must understand that the CRITICAL trigger for
replica-count-below-minAvailable is conditional on PDB presence in State A.
This boundary condition is documented in A-1 (which quotes the full trigger
definition) and in the Risk Note proof test. The delta is self-contained for
implementation purposes.

---

## Verification Report

| Requirement | Present | Location | Notes |
|---|---|---|---|
| Preserved Behaviour | Yes | Preserved Behaviour section | Single sentence; states the most important invariant |
| ADDED | Yes | A-1 through A-5 | CRITICAL severity, executive escalation, READINESS annotation, NFR update, AC-5 |
| MODIFIED | Yes | M-1 through M-6 | Classification logic, output schema, escalation cap, AC coverage, READINESS rule, spec version |
| REMOVED | Yes | R-1 through R-5 | HIGH-as-maximum, three-level parser assumption, unconditional cap, in-report annotation absence, AC ceiling |
| REMOVED Audit | Yes | REMOVED Audit section | All five removals verified genuine; one additional removal (R-5) identified during audit |
| Risk Note | Yes | Risk Note section | Highest-risk preserved behaviour identified with explanation |
| Proof Test | Yes | Risk Note — Proof Test | HIGH-preserved-on-no-PDB; exercises the HIGH/CRITICAL boundary condition |
| Engineering Review | Yes | Engineering Review section | ADDED, MODIFIED, REMOVED, backward compatibility, and implementation clarity all challenged |

All eight K 5.D.5 requirements are satisfied.

---

## Final Assessment

This delta is internally consistent and complete. The core change — formalising
CRITICAL as a first-class severity — introduces five additions, six
modifications, and five genuine removals. The most significant engineering risk
is the HIGH/CRITICAL boundary condition on PDB presence, which is directly
exercised by the proof test. No existing LOW, MEDIUM, or HIGH trigger condition
is altered. The read-only constraint and all escalation conventions are
unchanged. The delta is ready for specification review and sign-off before
implementation proceeds.
