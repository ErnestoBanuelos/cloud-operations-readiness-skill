# Cloud Operations & Support Brief — `cart-api`

This brief consolidates the five preceding operational artefacts into a single
decision-ready summary for engineering leads, on-call teams, and release approvers.

---

## Operational Summary

| Area | Summary |
|---|---|
| **Architecture** | `cart-api` is a stateless Kubernetes-hosted checkout service depending on a load balancer, PostgreSQL, Redis, and an Enterprise AI Gateway for the "Summarize my cart" feature (~3M AI calls/month). |
| **Deployment** | GitHub Actions pipeline: build → test → dependency scan → container build → image scan → push to registry → `kubectl apply` with rollout verification against the `checkout` namespace. |
| **Rollback** | `kubectl rollout undo deployment/cart-api -n checkout` reverts to the previous `ReplicaSet`; verified with `kubectl rollout status`. |
| **Monitoring** | Observability tooling covers all infrastructure layers — load balancer, cluster, application pods, Redis, PostgreSQL, and AI Gateway — via metrics, logs, and distributed traces. |
| **Incident Response** | Structured runbook: detect via `CrashLoopBackOff` / OOMKill alerts → diagnose with `kubectl describe` and `kubectl top` → stabilise via rollback → investigate root cause post-stabilisation. |
| **Monthly Cost** | $16,500/month — $1,500 flat cloud rent (9%) + $15,000 variable AI meter (91%). |
| **Cost Guardrails** | Enterprise AI Gateway hard cap: **$18,000/month**; alert threshold: **$13,500/month** (75% of cap, fires with $4,500 headroom remaining). |

---

## Readiness Questions

| Question | Answer | Status |
|---|---|---|
| How does the application deploy? | GitHub Actions pushes a SHA-tagged image to the container registry and applies the Kubernetes manifest via `kubectl apply`; rollout is verified with `kubectl rollout status`. | **Documented** |
| How does rollback work? | `kubectl rollout undo deployment/cart-api -n checkout` reverts to the previous `ReplicaSet` within the `checkout` namespace. | **Documented** |
| Who is paged during incidents? | On-call platform engineer → service owner → AI Gateway team if upstream latency is implicated. Specific pager identities and escalation tool are not defined in this artefact set. | UNKNOWN — owner needed |
| What is monitored? | Load balancer, Kubernetes cluster, `cart-api` pods, Redis, PostgreSQL, and Enterprise AI Gateway — metrics, logs, and traces. Specific alert names and dashboard links are not yet defined. | **Partial — alert definitions needed** |
| What is the estimated monthly cost and cost cap? | $16,500/month total. Hard cap: $18,000/month AI spend. Alert: $13,500/month. | **Documented** |
| What is the operational kill switch? | Roll back the deployment (`kubectl rollout undo`) and, if cost-related, disable or hard-cap the AI feature at the Enterprise AI Gateway. A dedicated feature flag or circuit breaker is not yet implemented. | **Partial — feature flag not implemented** |

---

## L1–L3 Support Ownership

| Ticket Type | Primary Tier | Runbook | Escalation |
|---|---|---|---|
| `CrashLoopBackOff` / `OOMKilled` | L2 — Platform Operations | `04-incident-runbook.md`: check `kubectl describe pod`, run `kubectl top pods`, execute rollback if deployment correlates | L3 — Product Engineering if root cause is application memory behaviour; L3 — AI Gateway team if upstream latency is implicated |
| AI Gateway Cost Cap Reached (HTTP 429) | L2 — Platform Operations | Verify spend against gateway dashboard; confirm cap value in `05-cost-estimate.md`; notify product team cost owner | L3 — Product Engineering to reduce call volume or adjust feature behaviour; Finance owner if cap increase is required |

---

## Operational Maturity Gaps

- **No `PodDisruptionBudget`** — planned maintenance can temporarily evict all replicas simultaneously.
- **No `securityContext`** — containers do not yet enforce `runAsNonRoot`, `readOnlyRootFilesystem`, or dropped Linux capabilities.
- **No alert definitions** — monitoring coverage is declared but specific alert names, thresholds, and dashboard links are absent from all artefacts.
- **No feature flag or circuit breaker** — the AI feature cannot be disabled without a full deployment rollback.
- **No OIDC/Workload Identity** — CI/CD pipeline uses a static `KUBECONFIG` secret rather than short-lived workload credentials.
- **Image tag in manifest is a placeholder** — `your-registry/cart-api:latest` must be replaced with a registry path and pinned tag before any deployment.

---

## Final Readiness Verdict

**Ready with Mitigations**

The core operational artefacts — architecture map, deployment manifest, CI workflow, incident
runbook, and cost estimate — are complete and internally consistent. The service can be
deployed once the gateway cost cap is configured, the container image reference is resolved,
and the two critical security gaps (`securityContext` and Workload Identity for CI) are
addressed. Remaining gaps are tracked above and should be resolved in the sprint immediately
following initial deployment.

---

## Next Recommended Actions

- **Configure the Enterprise AI Gateway cost cap** at $18,000/month with an alert at $13,500
  before the "Summarize my cart" feature is enabled in production.
- **Resolve the container image reference** — replace `your-registry/cart-api:latest` in the
  deployment manifest with the actual registry path and a pinned, immutable image tag.
- **Add a `securityContext`** to the pod and container spec (`runAsNonRoot`,
  `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`).
- **Define alert rules** for `CrashLoopBackOff`, pod memory utilisation above 80% of limit,
  and AI Gateway spend at the $13,500 threshold; link them to the on-call rotation.
- **Implement Workload Identity (OIDC)** for the CI/CD pipeline to replace the static
  `KUBECONFIG` secret with short-lived, least-privilege cluster credentials.

---

## Assumptions

- This brief summarises artefacts `01` through `05` in this repository. It does not replace
  those documents; refer to them for full detail, commands, and arithmetic.
- Specific pager routing, monitoring tool names, dashboard URLs, and escalation contacts are
  organisation-specific and are intentionally omitted.
- All artefacts in this series are illustrative reference examples. Implementation details
  must be validated against the actual target environment before production use.
