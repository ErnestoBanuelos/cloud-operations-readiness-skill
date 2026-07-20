# REFERENCE.md — Operational Reference

This document summarises the operational disciplines, best practices, and standards that
underpin the Cloud Operations Readiness Skill. It is a reference for engineers using the
Skill and for those adapting it to different services or platforms.

---

## Operational Readiness

Operational readiness is the state in which a service can be deployed, observed,
diagnosed, rolled back, and cost-controlled without requiring information that only
exists in someone's head.

A service is **not operationally ready** if any of the following is true:

- The deployment mechanism is undocumented or inconsistently applied.
- There is no defined rollback procedure.
- Monitoring exists but alerting thresholds are not defined.
- An AI-metered feature has no cost cap.
- The operational kill switch requires a write action with no documented approver.
- On-call ownership is undefined or exists only in tribal knowledge.

Readiness is binary at the blocking level: a service either has a documented, testable
rollback or it does not. Gradational language ("mostly ready", "nearly there") defers
rather than resolves these gaps.

### Readiness Checklist Categories

| Category | What it covers |
|---|---|
| Deployment safety | Immutable images, rolling update strategy, health probes |
| Observability | Metrics, logs, traces, alert definitions |
| Incident response | Runbook, rollback procedure, on-call ownership |
| Cost controls | AI meter cap, alert threshold, spend attribution |
| Security posture | Security context, least privilege, secret management |
| Support ownership | L1/L2/L3 routing, escalation paths, runbook references |

---

## Incident Diagnosis

Structured incident diagnosis reduces time-to-mitigation by separating observation from
inference. The correct sequence is:

1. **Observe** — collect raw signals: pod state, events, logs, metrics.
2. **Hypothesise** — form ranked hypotheses from the evidence. Do not skip to solutions.
3. **Verify cheaply** — identify the lowest-cost diagnostic step that distinguishes
   between hypotheses. Prefer read-only commands.
4. **Mitigate** — stabilise the service. Rollback is usually the safest first action.
5. **Investigate** — after stabilisation, determine root cause from profiling data.
6. **Remediate** — implement a permanent fix through the normal change process.

Skipping from observation to remediation without a hypothesis phase leads to addressing
symptoms rather than causes and to repeated incidents.

### OOMKill Pattern Recognition

`OOMKilled` is a hard termination by the Linux kernel's out-of-memory manager. It
occurs when a container's memory consumption reaches the configured limit.

Common root causes ranked by frequency:

| Rank | Cause | Distinguishing signal |
|---|---|---|
| 1 | Large payload buffered in memory | Memory grows with request rate; correlates with a new I/O path |
| 2 | Memory leak or unbounded cache | Linear memory growth over time; does not stabilise |
| 3 | Upstream latency causing goroutine/thread accumulation | CPU also elevated; many in-flight connections visible |

The delay between deployment and first OOMKill is a diagnostic signal. Immediate
crashes suggest startup allocation. Delayed crashes under load suggest runtime
accumulation. Both are distinct patterns with distinct investigation approaches.

### Kubernetes Diagnostic Commands (read-only)

```bash
# Pod state
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>

# Resource consumption
kubectl top pods -n <namespace>
kubectl top nodes

# Crash history
kubectl logs <pod-name> -n <namespace> --previous

# Events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Rollout history
kubectl rollout history deployment/<name> -n <namespace>
```

---

## Deployment Audits

A deployment audit applies a fixed checklist to a Kubernetes manifest or CI/CD
configuration. The checklist is evaluated the same way every time, regardless of
the service being reviewed, so that outputs are comparable and gaps are not
overlooked because the reviewer is familiar with the codebase.

### Critical Findings (production blockers)

| Finding | Risk |
|---|---|
| Mutable image tag (`latest`) | Different pods may run different versions; rollback is unreliable |
| No `securityContext` | Container may run as root; increased blast radius if compromised |
| No resource limits | A single pod can exhaust node memory; cascading failures |

### High-Priority Findings

| Finding | Risk |
|---|---|
| Shared liveness/readiness endpoint | Dependency failure triggers container restart instead of traffic removal |
| No explicit rolling update strategy | Deployment behaviour depends on Kubernetes defaults, which may change |
| No `PodDisruptionBudget` | Planned maintenance can evict all replicas simultaneously |
| Static credentials in CI/CD | Long-lived secrets are a supply-chain attack vector |

### Supply-Chain Security

A CI/CD pipeline has supply-chain risk at three points:

1. **Source dependencies** — third-party packages with known CVEs.
2. **Base image** — container base layer vulnerabilities.
3. **Action pinning** — GitHub Actions pinned to a mutable tag rather than a commit SHA.

Mitigations:

- Dependency scanning (e.g. `pip-audit`, `npm audit`, Dependabot) blocks builds with
  known critical CVEs.
- Image scanning (e.g. Trivy, Grype) blocks pushes when the built image contains
  critical vulnerabilities.
- Actions pinned to a full commit SHA (`uses: actions/checkout@<sha>`) prevent a
  compromised action version from executing in the pipeline.
- Image signing (e.g. Cosign/Sigstore) allows the cluster to verify that a pushed
  image was built by the trusted pipeline before scheduling it.

---

## FinOps for AI-Metered Services

Services that call an LLM through an API gateway have a cost structure different from
traditional compute workloads. Cloud infrastructure cost (pods, database, cache, load
balancer) is largely flat. AI token cost scales directly with usage volume.

### Cost Split Principle

Always report AI-metered costs in two separate lines:

| Category | Behaviour | Owner |
|---|---|---|
| Cloud infrastructure | Flat — scales with capacity, not requests | Platform / ops team |
| AI meter | Variable — scales linearly with feature usage | Product / feature team |

Combining these into a single number hides the risk. The AI meter can double or triple
in a month if call volume increases or if an application loop occurs. The infrastructure
rent will not.

### Cost Cap Design

A gateway cost cap has two components:

**Hard cap** — the monthly spend value at which new AI requests are rejected.
- Set at ≥ 120% of current monthly baseline.
- Setting at or below current spend blocks production traffic at month-end.

**Alert threshold** — the spend value at which on-call engineers are notified.
- Set at ≤ 75% of the hard cap.
- An alert at the cap value means the first notification arrives when requests are
  already being rejected.

The enforcement action on cap breach should be HTTP 429 (Too Many Requests), not
silent failure. The application must handle 429 gracefully and degrade the AI feature
rather than returning an unhandled error.

### Token Cost Arithmetic

```
Monthly input cost  = (calls/month × input_tokens/call) ÷ 1,000,000 × price_per_1M_input
Monthly output cost = (calls/month × output_tokens/call) ÷ 1,000,000 × price_per_1M_output
AI meter total      = input cost + output cost
```

Sanity check: input cost alone should be the dominant figure. If the total is less than
the input-only calculation, the call volume or token count has been dropped.

---

## Readiness Reviews

An operational readiness review (ORR) answers a fixed set of questions before a service
is approved for production. The output is not a score — it is a binary gate plus a
structured gap inventory.

### Six Standard Readiness Questions

| # | Question | What a complete answer contains |
|---|---|---|
| 1 | How does the application deploy? | Tool, trigger, steps, verification mechanism |
| 2 | How does rollback work? | Command or procedure, verification step, time estimate |
| 3 | Who is paged during incidents? | Role name, escalation path, pager tool (or UNKNOWN) |
| 4 | What is monitored? | Named components, signal types (metrics/logs/traces), alert definitions |
| 5 | What is the estimated monthly cost and cost cap? | Split total, hard cap value, alert threshold |
| 6 | What is the operational kill switch? | Feature flag, circuit breaker, or rollback procedure |

An answer of `UNKNOWN — owner needed` is acceptable only if the gap is tracked and has
a named owner. An unknown kill switch or unknown on-call owner is a blocking gap.

### Verdict Definitions

| Verdict | Condition |
|---|---|
| **Ready** | All six questions answered; no critical audit findings; cost cap set |
| **Ready with Mitigations** | All questions answered or UNKNOWN with named owners; critical gaps tracked |
| **Not Ready** | Any critical gap without an owner; cost cap absent on AI-metered service; image reference unresolvable |

---

## Support Ownership

L1/L2/L3 tiering defines who responds first and when escalation occurs. Without this
definition, every incident defaults to the most senior available engineer.

| Tier | Scope | Response type |
|---|---|---|
| L1 | Alert triage, status page update, initial customer communication | Read-only diagnosis; escalate if unresolved in defined SLA |
| L2 | Operational runbook execution, rollback, feature disablement | Follows documented procedures; escalates for root-cause investigation |
| L3 | Root-cause investigation, permanent fix, post-incident review | Code or infrastructure change through normal change process |

For each known failure mode, the support ownership table should name:
- The ticket type or alert name
- The primary responding tier
- The specific runbook document and section
- The escalation path and trigger condition

---

## Cloud Operations

### Namespace and RBAC Design

- Every service should operate in its own Kubernetes namespace.
- A dedicated `ServiceAccount` per service allows RBAC to be scoped to the minimum
  required permissions.
- `automountServiceAccountToken: false` prevents the default token from being mounted
  into pods that do not require Kubernetes API access.

### Network Policy

Default Kubernetes networking allows all pods to communicate with all other pods. A
`NetworkPolicy` should restrict ingress to known sources (e.g. load balancer, ingress
controller) and egress to known dependencies (e.g. PostgreSQL, Redis, AI Gateway).

### High Availability

Three replicas provide basic tolerance for a single pod failure or a single-node
failure. A `PodDisruptionBudget` with `minAvailable: 2` ensures at least two replicas
remain available during voluntary disruptions (node drain, rolling upgrade).

`topologySpreadConstraints` or pod anti-affinity rules ensure replicas are not
co-located on the same node or availability zone.

### Observability Signals

| Signal type | What it answers | Tool examples |
|---|---|---|
| Metrics | Is the service healthy right now? What are the trends? | Prometheus, Datadog, CloudWatch |
| Logs | What happened in a specific request or time window? | Loki, Splunk, CloudWatch Logs |
| Traces | Which service or dependency introduced latency or errors? | Jaeger, Tempo, X-Ray |
| Events | What did Kubernetes do and why? | `kubectl get events` |

Memory utilisation alerting at 80% of the pod memory limit gives actionable warning
before OOMKill at 100%. Without this alert, the first signal from a memory-leaking
pod is a production crash.

---

## Production Readiness Standards

The following standards apply regardless of the cloud provider or platform:

1. Every service has a documented deployment procedure that any engineer on the team
   can execute without prior context.
2. Every service has a tested rollback procedure with a documented recovery time.
3. Every AI-metered feature has a cost cap and an alert threshold set before it ships.
4. Every service has a named on-call owner and an escalation path to a secondary.
5. Every deployment pipeline produces an immutable, scannable artefact (container image
   with digest) that is traceable back to a specific commit.
6. Every production manifest defines resource requests and limits, a security context,
   and separate liveness and readiness probes.
7. Every new service is reviewed against this checklist before its first production
   deployment, and the review output is retained as an artefact.
