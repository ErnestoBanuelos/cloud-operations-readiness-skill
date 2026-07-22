# ADR-001 — Introduce a Reference Implementation

**Status:** Proposed

**Date:** 2026-07-22

---

## Context

The Cloud Operations Readiness Skill repository was originally designed as a
documentation-first project.

The repository contains:

- The portable Skill definition (`SKILL.md`)
- Repository-specific context (`CLAUDE.md`)
- Reference documentation (`REFERENCE.md`)
- Specifications
- Brownfield deltas
- Planning artefacts
- Session logs
- Example operational artefacts

This structure has successfully supported the first seven Deep Engineering
katas by treating the Skill specification itself as the primary deliverable.

However, beginning with later Deep Engineering katas, the expected workflow
assumes the existence of executable artefacts that can be independently tested,
reviewed, and verified.

Examples include:

- Independent test generation
- Seven-lens engineering review
- Adversarial verification
- Provenance validation
- CI execution against implementation

Without executable artefacts, these exercises require increasingly artificial
adaptations that no longer reflect the intended engineering workflow.

---

## Decision

This repository SHALL evolve from a documentation-only Skill repository into a
repository containing both:

1. The normative Skill specification.
2. A Reference Implementation.

The specification remains the source of truth.

The Reference Implementation exists to demonstrate one correct implementation
of the specification.

It is intentionally educational and verification-oriented rather than
production-oriented.

---

## Rationale

Introducing a Reference Implementation provides several benefits.

### Executable verification

The repository gains executable behaviour that can be validated using unit
tests, integration tests, and CI pipelines.

### Independent implementation review

Later Deep Engineering katas can evaluate actual implementation decisions
instead of simulated documentation workflows.

### Specification validation

The implementation serves as a continuous check that the specification is
complete, internally consistent, and implementable.

### Educational value

Engineers can study both the declarative specification and one canonical
implementation.

Alternative implementations remain possible.

---

## Consequences

Positive:

- Future Deep Engineering katas can execute without artificial adaptations.
- Independent tests become meaningful.
- Seven-lens review evaluates executable code.
- CI validates implementation behaviour.
- Repository becomes a complete reference project.

Negative:

- Repository maintenance increases.
- Specification and implementation must remain synchronized.
- Additional tooling (tests, linting, packaging) becomes necessary.

---

## Architectural Principles

The following principles govern the implementation.

### Specification First

The specification defines expected behaviour.

Implementation SHALL never introduce behaviour absent from the specification.

### Reference, Not Production

The implementation demonstrates correctness.

It is not intended to optimize performance or provide production-grade
deployment characteristics.

### Incremental Growth

Implementation SHALL evolve one bounded capability at a time.

Each Deep Engineering kata implements only the behaviour required by that kata.

### Behaviour Preservation

Whenever implementation changes, the specification remains the normative
contract.

Any behavioural change must first appear in the specification or Brownfield
Delta before code changes are made.

---

## Initial Scope

Version 0.1 of the Reference Implementation includes only the first execution
slice identified during task decomposition.

Initial capabilities include:

- Risk level domain model
- Risk classification engine
- Report validation primitives

Future capabilities will be added incrementally.

---

## Alternatives Considered

### Continue using documentation-only artefacts

Rejected.

This increasingly diverges from the intended Deep Engineering workflow and
prevents meaningful verification.

### Create a separate implementation repository

Rejected.

Keeping specification and implementation together improves traceability,
verification, and educational value.

---

## Implementation Impact

The repository will gain a new executable layer.

```
src/
    readiness_engine/

tests/

scripts/
```

The documentation layer remains unchanged.

```
SKILL.md
REFERENCE.md
CLAUDE.md
specs/
changes/
sessions/
```

Both layers evolve together.

---

## Success Criteria

This ADR is considered successful when:

- The repository contains an executable Reference Implementation.
- The implementation remains fully traceable to the specification.
- Independent tests validate implementation behaviour.
- Future Deep Engineering katas execute against real code instead of simulated artefacts.
- Specification continues to act as the single source of truth.