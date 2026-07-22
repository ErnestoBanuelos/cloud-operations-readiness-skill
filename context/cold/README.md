# context/cold/README.md — Cold Context Index

**Purpose:** This directory holds knowledge that cannot be verified from the current
repository contents. It records historical gaps, undocumented decisions, tribal
knowledge, deprecated paths, and previous incidents that are known to be absent from
the codebase.

Cold Context is read when a new engineer joins the project, when an incident reveals
a previously unknown constraint, or when the warm context is insufficient to answer a
question. It is never assumed to be complete.

---

## What Belongs in Cold Context

### 1. Undocumented Historical Decisions

Architectural or operational choices that were made before documentation practices
were established, or whose rationale was never recorded. Examples:

- Why a specific checklist item was added or removed from the 12-item audit list.
- Why the artefact naming convention (`01-` through `06-`) was chosen.
- Why the `800-wide/` directory name was selected (width of a content column?
  a display format?).
- Why Python 3.11 specifically was selected over 3.12 or 3.10.

### 2. Deprecated Paths

File paths, commands, conventions, or workflows that existed in an earlier version
of the Skill but have since been changed or removed. Examples:

- Earlier output formats before the current DIAGNOSIS / AUDIT / COST / READINESS
  classification scheme was established.
- Any earlier CLAUDE.md or AI instructions that predate this bundle.
- Previous artefact sets under directory names other than `800-wide/`.

### 3. Tribal Knowledge

Operational knowledge that was never written down and exists only in the memory
of the engineers who originally built the Skill. Examples:

- The intended audience and deployment context for the Skill's first production use.
- Whether the `cart-api` artefacts represent a real service, a sanitised real service,
  or a fully synthetic scenario.
- The reasoning behind specific confidence percentages in the diagnosis examples
  (65% / 25% / 10%).

### 4. Previous Incidents

Operational incidents or failure modes encountered during the development or use of
the Skill that are not documented in `run-log.md`. The run-log records five execution
traces as of v1.0.0, but does not record:

- Any incidents encountered during pre-release testing.
- Any cases where the Skill produced incorrect or dangerous output that required
  correction.
- Any edge cases in the cost arithmetic that caused calculation errors.

### 5. Undocumented Architectural Rationale

Constraints or design choices present in the Skill definition whose rationale is
not explained. Examples:

- Why the readiness questions are exactly six (not five or seven).
- Why the hard cap is set at 120% specifically (not 110% or 150%).
- Why the alert threshold is 75% of the hard cap (not 80%).
- Whether the 12-item audit checklist was derived from an external standard (CIS,
  NIST, a cloud provider's production readiness review) or was composed independently.

---

## What Does NOT Belong in Cold Context

- Verified facts that can be read directly from the repository.
- Stack and technology details — those belong in `docs/context/stack.md`.
- Engineering rules and constraints — those belong in `CLAUDE.md`.
- Speculative history — do not invent gaps that cannot be genuinely identified.

---

## Files in This Directory

| File | Contents |
|---|---|
| `README.md` | This index |
| `gap-log.md` | Honest record of identified knowledge gaps |

---

## Maintenance

Add a new entry to `gap-log.md` whenever:

- An engineer discovers a question that cannot be answered from existing documentation.
- A historical decision surfaces during an incident or review without a traceable rationale.
- Tribal knowledge is identified that should be captured before it is lost.

Do not close a gap entry unless the answer has been verified from a primary source
and recorded in the appropriate context layer (warm or hot).
