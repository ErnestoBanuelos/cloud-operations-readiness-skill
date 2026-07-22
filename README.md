# cloud-operations-readiness-skill

A reusable Claude Skill that helps platform engineers and SREs evaluate whether a
cloud-native service is operationally ready for production.

The Skill is **read-only by design**. It reads artefacts, analyzes evidence, produces
ranked diagnoses, audits manifests, estimates costs, and recommends actions. It never
executes infrastructure changes. Every change recommendation is escalated to a named
human role.

---

## Repository Contents

This repository contains four distinct layers:

### 1. Skill Specification

The portable, normative definition of the Skill's behaviour.

| File | Purpose |
|---|---|
| `SKILL.md` | Claude Skill definition — four output types, invariant rules, tool allowlist |
| `REFERENCE.md` | Operational reference and engineering best practices |
| `CLAUDE.md` | Hot context — non-negotiable rules for every invocation |

### 2. Context Bundle

The synthetic evidence base for the `cart-api` reference service.

| Path | Contents |
|---|---|
| `artefacts/800-wide/01-stack-map.md` | Component ownership map |
| `artefacts/800-wide/02-deploy-manifest.md` | Kubernetes Deployment and Service manifest |
| `artefacts/800-wide/03-ci-workflow.md` | GitHub Actions CI/CD workflow |
| `artefacts/800-wide/04-incident-runbook.md` | OOMKill incident analysis and runbook |
| `artefacts/800-wide/05-cost-estimate.md` | Monthly cost estimate with AI meter split |
| `artefacts/800-wide/06-readiness-brief.md` | Executive operational readiness brief |

### 3. Reference Engine

A canonical Python implementation of the Skill specification (v0.1).
The specification remains the single source of truth.
The implementation demonstrates one correct realisation of the specification.

```
src/
└── readiness_engine/
    ├── __init__.py     # Package metadata and public surface
    ├── models.py       # Domain types — enumerations, constants, dataclasses
    ├── classifier.py   # Classify input text into one of four request types
    ├── validator.py    # Validate report structure against specification rules
    ├── report.py       # Output report dataclasses for the four output types
    └── parser.py       # Parse raw text / dict inputs into structured containers
```

Install the package (development mode):

```bash
pip install -e ".[dev]"
```

### 4. Verification Assets

Tests and CI configuration that validate the Reference Engine against
the specification.

```
tests/
├── __init__.py           # Test suite documentation
├── test_models.py        # Specification constant and enumeration invariants
├── test_classifier.py    # Classification accuracy against labelled fixtures
├── test_validator.py     # Structural validation rules from SKILL.md
└── test_parser.py        # Parser surface extraction from synthetic inputs
```

Run the verification suite:

```bash
pytest tests/
```

Lint and type-check:

```bash
ruff check src/ tests/
mypy src/
```

### 5. Engineering Artefacts

Decision records, session logs, and planning documents.

```
docs/adr/        — Architecture Decision Records
sessions/        — Deep Engineering session logs
specs/           — Specifications and brownfield deltas
changes/         — Change records
```

---

## Purpose

Production incidents are rarely caused by a single missing configuration. They emerge
from gaps across deployment safety, observability, cost controls, security context, and
ownership clarity — gaps that are individually easy to overlook but collectively
expensive.

This Skill applies a consistent, structured lens to four operational domains:

1. **Operational Diagnosis** — ranked hypotheses from logs, events, and pod output
2. **Deployment and IaC Audit** — manifest and workflow review against a fixed checklist
3. **Cloud Cost Review** — infrastructure rent vs. AI meter, with ownership and cap
4. **Operational Readiness Review** — go/no-go decision with explicit gap inventory

---

## Workflow

```
Engineer provides input
        │
        ▼
Skill classifies the request
        │
        ├── Operational Diagnosis     → 3 ranked hypotheses + verification commands
        ├── Deployment/IaC Audit      → checklist audit + gap report
        ├── Cloud Cost Review         → cost split + cap recommendation
        └── Readiness Review          → go/no-go decision + gap inventory
        │
        ▼
Skill produces read-only output
        │
        ▼
Human reviews and executes recommended actions
```

The Skill never proceeds past the recommendation step. All execution is the
responsibility of the engineer or approving role named in the output.

---

## Example Inputs

- Paste `kubectl describe pod <name>` output and ask: *"What is causing these crashes?"*
- Paste a Kubernetes manifest and ask: *"Audit this for production readiness."*
- Provide token volumes and pricing and ask: *"Estimate the monthly AI cost and set a cap."*
- Paste `kubectl get events` output and ask: *"What is the most likely root cause?"*
- Provide the six artefacts and ask: *"Is this service ready to ship?"*

---

## Example Outputs

**Operational Diagnosis**
> Three ranked hypotheses with confidence levels, supporting evidence, cheapest
> verification command, and escalation path. No `kubectl apply` or fix execution.

**Deployment Audit**
> Checklist table across 12 production criteria. Each gap includes priority, recommended
> fix, and the role responsible for implementing it.

**Cost Review**
> Line-by-line arithmetic. Cloud rent vs. AI meter split. Hard cap value. Alert threshold.
> Ship / ship-with-mitigation / reject recommendation.

**Readiness Review**
> Six-question readiness table. Maturity gap inventory. Final verdict with explicit
> rationale.

---

## Design Principles

### Read-Only Philosophy

The Skill is deliberately constrained to read, analyze, and recommend. It will never:

- Run `kubectl apply`, `kubectl patch`, or `kubectl delete`
- Run `terraform apply` or `terraform destroy`
- Modify gateway policies or cost caps
- Execute rollbacks
- Page on-call engineers

This constraint is not a limitation — it is a safety property. Infrastructure changes
in production require human intent, approval, and accountability. The Skill provides
the analysis that informs those decisions; it does not make them.

### Structured, Measurable Outputs

Every output follows deterministic rules:

- Diagnoses produce **exactly three hypotheses**, each with a confidence level.
- Audit reports use a **fixed 12-item checklist** with explicit pass/fail per item.
- Cost estimates separate **cloud rent from AI meter** with explicit ownership.
- Readiness reviews answer **six named questions** and produce a single verdict.

This structure makes outputs comparable across runs and reviewable by engineers who
were not present when the Skill was invoked.

### Escalation by Default

When the Skill cannot determine a fact from available evidence, it outputs
`UNKNOWN — owner needed` rather than inferring or inventing. When a recommended action
requires human approval, the output names the approving role explicitly.

---

## When to Use This Skill

- Before promoting a service to a production environment for the first time
- During a pre-launch readiness review or go/no-go gate
- When investigating a production incident and forming an initial hypothesis
- When reviewing a pull request that modifies a Kubernetes manifest or CI workflow
- When estimating the monthly cost of a new AI-powered feature before shipping
- When onboarding a new service onto a shared platform and auditing its configuration

---

## When Not to Use This Skill

- To execute infrastructure changes directly — the Skill does not do this
- As a replacement for a live `kubectl` session during an active incident — use the
  Skill to form hypotheses before the incident or to produce runbook content after it
- When authoritative source-of-truth data is unavailable — the Skill will surface gaps
  honestly, but an audit against incomplete evidence is an incomplete audit
- As the sole approval gate for a production deployment — human review is always required

---

## Contributing

This repository is structured as a reference implementation. To adapt the Skill for a
different service:

1. Replace the artefacts under `artefacts/` with the equivalent documents for your service.
2. Update the component and ownership references in `SKILL.md` to match your stack.
3. Add service-specific examples to `examples.md`.
4. Record execution results in `run-log.md`.

---

## License

This repository is published as an open reference implementation. See `LICENSE` for terms.
