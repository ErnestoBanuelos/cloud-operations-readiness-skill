# docs/context/stack.md — Warm Context

**Purpose:** Stable reference for the technology stack, repository structure, and
architectural constraints of the Cloud Operations Readiness Skill.

**Last verified:** 2026-07-22

---

## Language(s)

| Language | Role | Verified |
|---|---|---|
| Python 3.11 | Application runtime for the reference `cart-api` service | Yes — `artefacts/800-wide/03-ci-workflow.md` line 53: `python-version: "3.11"` |
| YAML | Kubernetes manifests and GitHub Actions workflows | Yes — `artefacts/800-wide/02-deploy-manifest.md`, `03-ci-workflow.md` |
| Markdown | All Skill definitions, artefacts, documentation | Yes — repository root, all artefact files |

The Skill itself (SKILL.md) is a declarative prompt-based definition; it has no
compiled or interpreted language runtime of its own.

---

## Framework(s)

| Framework | Role | Verified |
|---|---|---|
| Kubernetes | Container orchestration platform for the reference service | Yes — `02-deploy-manifest.md`, `03-ci-workflow.md` |
| GitHub Actions | CI/CD pipeline for the reference service | Yes — `03-ci-workflow.md` |
| pytest | Test runner for the reference `cart-api` application | Yes — `03-ci-workflow.md` line 59: `run: pytest tests/` |
| Enterprise AI Gateway | LLM routing, rate-limiting, cost attribution layer | Yes — `01-stack-map.md`, `REFERENCE.md` |

No web framework (Flask, FastAPI, etc.) is declared for `cart-api` — **Unverified**.
The service exposes `/healthz` on port 8080 but the framework that serves it is
not specified in any artefact.

---

## Build System

| Tool | Role | Verified |
|---|---|---|
| Docker / OCI | Container image build | Yes — `03-ci-workflow.md` uses `docker/build-push-action@v6` |
| GitHub Container Registry (`ghcr.io`) | Image registry | Yes — `03-ci-workflow.md` lines 38–39: `REGISTRY: ghcr.io` |

No standalone build tool (Make, Gradle, etc.) is declared. Build is entirely driven
by GitHub Actions — **Verified** from `03-ci-workflow.md`.

---

## Package Manager

| Tool | Role | Verified |
|---|---|---|
| pip | Python dependency management | Yes — `03-ci-workflow.md` line 56: `pip install -r requirements.txt` |
| pip-audit (`pypa/gh-action-pip-audit`) | Dependency vulnerability scanning | Yes — `03-ci-workflow.md` line 71: `uses: pypa/gh-action-pip-audit@v1.1.0` |

A `requirements.txt` file is referenced in the CI workflow but is not present in
this repository — this is expected because the repository contains Skill definitions
and synthetic artefacts, not the application source code.

---

## Test Runner

| Tool | Role | Verified |
|---|---|---|
| pytest | Unit test execution | Yes — `03-ci-workflow.md` line 59: `run: pytest tests/` |

Test files are expected under `tests/` — **Unverified** (no `tests/` directory
present in this repository; it would exist in the application source repository).

---

## Repository Layout

Verified directly against the repository root:

```
cloud-operations-readiness-skill/
├── CLAUDE.md                          # Hot Context (AI engineering rules)
├── README.md                          # Project overview and usage guide
├── SKILL.md                           # Skill definition and output contracts
├── REFERENCE.md                       # Operational best practices reference
├── examples.md                        # Annotated worked examples (7 examples)
├── run-log.md                         # Execution log (5 recorded runs)
├── artefacts/
│   └── 800-wide/                      # Reference artefact set for cart-api
│       ├── 01-stack-map.md            # Component ownership map
│       ├── 02-deploy-manifest.md      # Kubernetes Deployment + Service manifest
│       ├── 03-ci-workflow.md          # GitHub Actions CI/CD workflow
│       ├── 04-incident-runbook.md     # OOMKill incident analysis and runbook
│       ├── 05-cost-estimate.md        # Monthly cost estimate
│       └── 06-readiness-brief.md      # Executive readiness brief
├── context/
│   └── cold/                          # Cold Context (gap log, historical unknowns)
│       ├── README.md
│       └── gap-log.md
└── docs/
    └── context/
        └── stack.md                   # This file (Warm Context)
```

---

## Architectural Style

**Read-only analysis agent with four structured output modes.**

The Skill is not a web service, library, or CLI tool. It is a declarative AI Skill
definition that constrains an AI assistant's behaviour when processing operational
artefacts.

| Property | Value | Verified |
|---|---|---|
| Output modes | 4: DIAGNOSIS, AUDIT, COST, READINESS | Yes — `SKILL.md` lines 54–176 |
| Safety class | Read-only | Yes — `SKILL.md` line 5: `Safety class: Read-only` |
| Input format | Markdown artefacts, YAML manifests, plain text logs | Yes — `SKILL.md` lines 36–47 |
| Escalation model | Every write action escalated to a named human role | Yes — `SKILL.md` lines 198–216 |

---

## Important Engineering Conventions

These conventions are enforced by CLAUDE.md and SKILL.md:

1. **Exactly three hypotheses per diagnosis** — no fewer, no more.
   Source: `SKILL.md` line 73.

2. **Fixed 12-item audit checklist** — evaluated in order; never skipped.
   Source: `SKILL.md` lines 97–113.

3. **Cost always split: cloud rent vs. AI meter** — two separate line items.
   Source: `SKILL.md` lines 133–138, `REFERENCE.md` lines 148–159.

4. **Unknown information stated explicitly** — output: `UNKNOWN — owner needed`.
   Source: `SKILL.md` line 48.

5. **Three named readiness verdicts only** — Ready / Ready with Mitigations / Not Ready.
   Source: `SKILL.md` lines 170–175.

6. **Six fixed readiness questions** — evaluated in order; all must be answered.
   Source: `SKILL.md` lines 159–166.

7. **AI meter hard cap ≥ 120% of baseline; alert ≤ 75% of hard cap.**
   Source: `SKILL.md` lines 135–137, `REFERENCE.md` lines 162–170.

---

## Verified Architectural Constraint

**Claim:** The Skill's read-only constraint is unconditional — it will never execute
or reference write commands outside an escalation section.

**Evidence:** `SKILL.md`, lines 180–194 (DO / DON'T table):

> DO: Use read-only commands in verification steps  
> DON'T: Include `kubectl apply`, `kubectl patch`, or `kubectl delete`

Additionally, `SKILL.md` lines 240–245:

> The Skill will never reference `terraform apply`, `terraform destroy`,
> `kubectl delete`, or any gateway or SLO mutation commands.

**Corroborated by:** `run-log.md` RUN-003 (lines 150–196), which records a correct
refusal when a write command was explicitly requested.

**File:** `artefacts/800-wide/03-ci-workflow.md`  
**Lines for Python version claim:** 52–53

```yaml
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
```

**Verification status: CONFIRMED**
