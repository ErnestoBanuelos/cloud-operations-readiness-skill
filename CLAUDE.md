# CLAUDE.md — Hot Context

## Identity

This repository is a read-only operational analysis Skill for cloud-native services.
The Skill reads artefacts, produces structured outputs, and escalates all write actions
to named human roles. It never executes infrastructure changes.

---

## Non-Negotiable Rules

1. **Read-only constraint is absolute.**
   Never execute, simulate, or produce write commands outside an Escalation section.
   This includes: `kubectl apply`, `kubectl delete`, `kubectl patch`,
   `terraform apply`, `terraform destroy`, gateway mutations, and rollback execution.

2. **Produce exactly three hypotheses for every diagnosis.**
   Never fewer. Never more. Each hypothesis requires: confidence %, evidence for,
   evidence against, and one read-only verification command.

3. **State unknown facts explicitly.**
   When information is absent, output: `UNKNOWN — owner needed`
   Never infer, estimate, or fabricate missing values.

4. **Every write action must be escalated to a named role.**
   Use the standard escalation block: Action / Role / Condition / Artefact.

5. **Audit checklist is fixed at 12 items.**
   Evaluate all 12. Never skip or reorder. Status must be PASS / FAIL / PARTIAL /
   NOT APPLICABLE. No gradational language.

6. **Cost reports always separate cloud rent from AI meter.**
   Report as two distinct line items with distinct owners.
   Hard cap ≥ 120% of baseline. Alert threshold ≤ 75% of hard cap.

7. **Readiness verdicts are one of three named values.**
   Ready / Ready with Mitigations / Not Ready.
   Never use gradational language ("mostly ready", "nearly there").

8. **Six readiness questions are fixed and evaluated in order.**
   All six must be answered or explicitly marked UNKNOWN.

---

## Escalation Format

```
ESCALATION REQUIRED
Action:    <write action required>
Role:      <named human role>
Condition: <trigger or approval gate>
Artefact:  <relevant document>
```

---

## Gap Log

If information required to produce a complete output is absent, record the gap
explicitly rather than proceeding with incomplete evidence. An incomplete audit
is more honest than a fabricated one.

---

## Safety Statement

The read-only constraint is not configurable. Any fork removing this constraint
requires explicit approval from a platform engineering lead before use against
live infrastructure.

---

## Repository Context

All repository-specific assumptions for this reference implementation are
consolidated here. These facts are specific to this repository and its
fictional `cart-api` reference service. They do not belong in the portable
Skill definition at `skills/cloud-operations-analysis/SKILL.md`.

### Reference Service

- **Service name:** `cart-api` — a checkout service exposing a cart
  summarisation AI feature.
- **AI feature name:** "Summarize my cart"
- **Deployment namespace:** `checkout`

### Technology Stack

- **Container orchestration:** Kubernetes
- **CI/CD system:** GitHub Actions
- **Container registry:** `ghcr.io` (GitHub Container Registry)
- **Application runtime:** Python 3.11
- **Test runner:** pytest (executed as `pytest tests/`)
- **Dependency manager:** pip (`requirements.txt`)
- **Dependency scanner:** `pypa/gh-action-pip-audit`
- **Image scanner:** Trivy or Grype (referenced in supply-chain audit)
- **Image signing:** Cosign / Sigstore
- **Database:** PostgreSQL
- **Cache:** Redis
- **AI routing layer:** Enterprise AI Gateway (centralised LLM proxy)

### Deployment Tooling (read-only commands for this stack)

```
kubectl get pods
kubectl get events
kubectl describe pod
kubectl describe deployment
kubectl logs
kubectl top pods
kubectl top nodes
kubectl rollout history
kubectl rollout status
```

Write commands (escalation sections only):
```
kubectl rollout undo     (rollback — requires human approval)
kubectl apply            (deployment — requires CI/CD pipeline or human approval)
```

Never reference: `terraform apply`, `terraform destroy`, `kubectl delete`,
or gateway / SLO mutation commands.

### Infrastructure Security Context Fields (Kubernetes-specific)

When auditing Kubernetes manifests, the security context checklist item
evaluates: `runAsNonRoot`, `readOnlyRootFilesystem`,
`allowPrivilegeEscalation: false`.

### Reference Cost Figures (fictional — for artefact demonstration only)

| Item | Value |
|---|---|
| Cloud rent (3 pods + database + cache + load balancer) | $1,500 / month |
| AI input price | $2.50 / 1M tokens |
| AI output price | $10.00 / 1M tokens |
| AI calls per month | 3,000,000 |
| AI meter total | $15,000 / month |
| Grand total | $16,500 / month |
| Hard cap | $18,000 / month (120% of baseline) |
| Alert threshold | $13,500 / month (75% of hard cap) |

### Reference Artefact Set

Located at `artefacts/800-wide/`:

| File | Content |
|---|---|
| `01-stack-map.md` | Component ownership map; request flow |
| `02-deploy-manifest.md` | Kubernetes Deployment and Service manifest |
| `03-ci-workflow.md` | GitHub Actions CI/CD pipeline |
| `04-incident-runbook.md` | OOMKill incident analysis and runbook |
| `05-cost-estimate.md` | Monthly cost estimate; AI meter arithmetic; cap |
| `06-readiness-brief.md` | Executive readiness summary; go/no-go verdict |

### Architectural Constraints

- Service is containerised; image digest references required (not `latest`).
- OIDC Workload Identity is the required credential model for CI/CD pipeline
  authentication to the cluster.
- `PodDisruptionBudget` with `minAvailable: 2` is the expected disruption
  budget for a three-replica service.
- `topologySpreadConstraints` or pod anti-affinity rules are required for
  placement distribution across failure domains.
- `automountServiceAccountToken: false` is required for workloads that do not
  need Kubernetes API access.

### Ownership Labels

- `[ops]` — platform / infrastructure team
- `[mine/Product]` — application / feature product team
