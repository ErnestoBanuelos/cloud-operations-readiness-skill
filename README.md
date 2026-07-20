# cloud-operations-readiness-skill

A reusable Claude Skill that helps platform engineers and SREs evaluate whether a
cloud-native service is operationally ready for production.

The Skill is **read-only by design**. It reads artefacts, analyzes evidence, produces
ranked diagnoses, audits manifests, estimates costs, and recommends actions. It never
executes infrastructure changes. Every change recommendation is escalated to a named
human role.

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

## Repository Structure

```
cloud-operations-readiness-skill/
├── README.md                          # This file
├── SKILL.md                           # Claude Skill definition
├── REFERENCE.md                       # Operational reference and best practices
├── examples.md                        # Annotated worked examples
├── run-log.md                         # Execution log demonstrating Skill behaviour
└── artefacts/
    └── 800-wide/
        ├── 01-stack-map.md            # Component ownership map (cart-api)
        ├── 02-deploy-manifest.md      # Kubernetes Deployment and Service manifest
        ├── 03-ci-workflow.md          # GitHub Actions CI/CD workflow
        ├── 04-incident-runbook.md     # OOMKill incident analysis and runbook
        ├── 05-cost-estimate.md        # Monthly cost estimate with AI meter split
        └── 06-readiness-brief.md      # Executive operational readiness brief
```

### Artefact Relationships

The six artefacts under `artefacts/800-wide/` form a layered evidence chain for the
fictional `cart-api` checkout service:

| Artefact | Answers |
|---|---|
| `01-stack-map.md` | What components exist and who owns them? |
| `02-deploy-manifest.md` | How is the service deployed? What configuration gaps exist? |
| `03-ci-workflow.md` | How does code reach production? What supply-chain controls are present? |
| `04-incident-runbook.md` | What happened in the last incident? How do we respond next time? |
| `05-cost-estimate.md` | What does this service cost per month? Who owns the AI meter spend? |
| `06-readiness-brief.md` | Is the service ready to ship? What is the go/no-go decision? |

The Skill uses these artefacts as its primary evidence base. When invoked against a
different service, the engineer provides equivalent artefacts as inputs.

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
