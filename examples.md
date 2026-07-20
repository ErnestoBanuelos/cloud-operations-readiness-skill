# examples.md — Worked Examples

Each example shows a realistic input and the expected Skill output. Examples are drawn
from the `cart-api` operational artefact set in `artefacts/800-wide/`.

---

## Example 1 — CrashLoopBackOff Diagnosis

### Input

```
kubectl get pods -n checkout

NAME                        READY   STATUS             RESTARTS   AGE
cart-api-7d4f9b8c6-2xvpq   0/1     CrashLoopBackOff   8          18m
cart-api-7d4f9b8c6-k9lmn   0/1     CrashLoopBackOff   7          18m
cart-api-7d4f9b8c6-r3tws   1/1     Running            0          18m

kubectl get events -n checkout --sort-by='.lastTimestamp'

LAST SEEN   TYPE      REASON      OBJECT                            MESSAGE
2m          Warning   BackOff     pod/cart-api-7d4f9b8c6-2xvpq     Back-off restarting failed container
3m          Warning   BackOff     pod/cart-api-7d4f9b8c6-k9lmn     Back-off restarting failed container
18m         Normal    Pulled      pod/cart-api-7d4f9b8c6-2xvpq     Successfully pulled image
18m         Normal    Started     pod/cart-api-7d4f9b8c6-2xvpq     Started container cart-api
```

Context: Crashes started approximately 5 minutes after deploying a new version.
No OOMKill events visible yet. No recent infrastructure changes.

---

### Expected Output

**Classification:** DIAGNOSIS

---

**Incident Summary**

Two of three `cart-api` pods in the `checkout` namespace are in `CrashLoopBackOff`
after eight and seven restarts respectively. The third pod is healthy. Crashes began
approximately 5 minutes after a new deployment. No `OOMKilled` termination reason is
visible in events at this time. One pod is absorbing all traffic, which will increase
its memory and CPU load.

---

**Hypothesis 1 — Application startup failure in the new version (Confidence: 65%)**

Supporting evidence: Crashes began within minutes of a new deployment; the previous
version ran without restarts. `CrashLoopBackOff` with a clean `Pulled` and `Started`
event suggests the container starts and then exits quickly.

Evidence against: One pod is running successfully on the same image, which argues
against a universal startup failure.

Cheapest verification step:
```bash
kubectl logs cart-api-7d4f9b8c6-2xvpq -n checkout --previous
```
Look for a panic, unhandled exception, missing environment variable, or failed
database connection at startup.

---

**Hypothesis 2 — Missing or invalid secret causing an environment variable lookup
failure (Confidence: 20%)**

Supporting evidence: The manifest references `cart-api-secrets` for `DATABASE_URL`
and `AI_GATEWAY_API_KEY`. If the secret was not updated during the deployment, the
new version may require a key that does not exist in the current secret.

Evidence against: If the secret were missing entirely, all three pods would be failing.
One pod is running, which suggests the secret exists.

Cheapest verification step:
```bash
kubectl describe secret cart-api-secrets -n checkout
```
Confirm all expected keys are present and match the keys referenced in the manifest.

---

**Hypothesis 3 — Liveness probe misconfiguration causing premature container
termination (Confidence: 15%)**

Supporting evidence: The manifest defines a liveness probe on `/healthz` with
`initialDelaySeconds: 15`. If the new version takes longer than 15 seconds to
initialise, the liveness probe fires before the application is ready and triggers
a restart loop.

Evidence against: The previous version used identical probe settings. A behaviour
change would require either a slower startup in the new version or a configuration
change to the probe.

Cheapest verification step:
```bash
kubectl describe pod cart-api-7d4f9b8c6-2xvpq -n checkout
```
Inspect the `Last State`, `Exit Code`, and probe failure messages in the Events
section.

---

**Immediate Mitigation (read-only)**

1. Collect logs from a crashed pod before the next restart clears them:
   ```bash
   kubectl logs cart-api-7d4f9b8c6-2xvpq -n checkout --previous
   ```
2. Check current resource consumption on the surviving pod:
   ```bash
   kubectl top pods -n checkout
   ```
3. Confirm the rollout history to identify what changed in the new version:
   ```bash
   kubectl rollout history deployment/cart-api -n checkout
   ```

---

**Escalation**

```
ESCALATION REQUIRED
Action:    kubectl rollout undo deployment/cart-api -n checkout
Role:      On-call platform engineer
Condition: If logs confirm the new version is the cause, or if the surviving pod
           becomes overloaded before the diagnosis is complete
Artefact:  artefacts/800-wide/04-incident-runbook.md — Immediate Mitigation section
```

---

## Example 2 — OOMKilled Diagnosis

### Input

```
kubectl describe pod cart-api-7d4f9b8c6-2xvpq -n checkout

Name: cart-api-7d4f9b8c6-2xvpq
Namespace: checkout
...
Containers:
  cart-api:
    ...
    Last State:
      Terminated
        Reason: OOMKilled
        Exit Code: 137
        Started: Mon, 20 Jul 2026 14:32:11 +0000
        Finished: Mon, 20 Jul 2026 14:52:43 +0000
    Limits:
      memory: 512Mi
      cpu: 500m
    Requests:
      memory: 512Mi
      cpu: 250m

Context: Deployment of "Summarize my cart" AI feature completed at 14:30.
Crashes started at approximately 14:52 — 22 minutes after deployment.
```

---

### Expected Output

**Classification:** DIAGNOSIS

---

**Incident Summary**

A `cart-api` pod in the `checkout` namespace was terminated with `OOMKilled` (exit
code 137) approximately 22 minutes after the "Summarize my cart" AI feature was
deployed. The pod ran for 20 minutes before reaching the 512 Mi memory limit. The
delay between deployment and crash, combined with the correlation to a new AI feature,
indicates runtime memory accumulation rather than a startup allocation failure.

---

**Hypothesis 1 — AI response payloads buffered in memory, exceeding the 512 Mi
limit under sustained load (Confidence: 65%)**

Supporting evidence: Crashes began 22 minutes after the AI feature was deployed, not
immediately. LLM responses can be large; if held in memory for post-processing or
logging, concurrent in-flight requests accumulate. At ~3,000,000 calls/month
(~1.15 req/s average), bursts above the mean can rapidly exhaust 512 Mi.

Evidence against: A single-request overflow would likely crash within the first few
requests. The 20-minute runtime before OOMKill suggests gradual accumulation, which
is more consistent with a cache or buffer growth pattern than a single large payload.

Cheapest verification step:
```bash
kubectl top pods -n checkout
```
Observe whether memory is trending upward on the surviving pods. A rising baseline
without stabilisation confirms accumulation.

---

**Hypothesis 2 — Unbounded in-process cache or memory leak in the AI feature code
path (Confidence: 25%)**

Supporting evidence: The 22-minute delay is consistent with gradual linear growth
rather than burst allocation. New code introduced for the AI feature may not have
been profiled under sustained load. An unbounded cache storing AI responses without
TTL or eviction would produce this pattern.

Evidence against: A genuine memory leak typically takes hours to manifest at this
volume. The speed of onset (22 minutes) suggests a bounded but large allocation rather
than an unbounded one.

Cheapest verification step:
```bash
kubectl logs cart-api-7d4f9b8c6-2xvpq -n checkout --previous
```
Search for allocation warnings, cache size log lines, or unhandled exceptions in the
AI summarisation code path.

---

**Hypothesis 3 — Enterprise AI Gateway latency causing in-flight request accumulation
(Confidence: 10%)**

Supporting evidence: If the AI Gateway is rate-limiting or responding slowly, outbound
requests queue internally. Each queued request retains its memory state. Under sustained
load this can exhaust available memory. Surviving pods showing elevated latency would
support this hypothesis.

Evidence against: OOMKill results from hard memory boundary breach. I/O queuing
typically manifests as CPU saturation and timeouts before reaching OOM conditions.
Gateway issues would also be visible in latency metrics and HTTP 429 response counts.

Cheapest verification step: Check the Enterprise AI Gateway dashboard or metrics for
elevated latency and HTTP 429 responses in the 22 minutes preceding the crash.

---

**Immediate Mitigation (read-only)**

1. Observe memory trend on surviving pods:
   ```bash
   kubectl top pods -n checkout
   ```
2. Collect logs from the most recently crashed pod:
   ```bash
   kubectl logs <pod-name> -n checkout --previous
   ```
3. Review gateway metrics for rate-limiting or latency anomalies in the incident window.

---

**Escalation**

```
ESCALATION REQUIRED
Action:    kubectl rollout undo deployment/cart-api -n checkout
Role:      On-call platform engineer
Condition: If kubectl top pods shows memory trending upward on surviving pods, or if
           the diagnosis cannot be completed before a second pod crashes
Artefact:  artefacts/800-wide/04-incident-runbook.md — Immediate Mitigation section
```

---

## Example 3 — Deployment Manifest Audit

### Input

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
  namespace: checkout
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cart-api
  template:
    metadata:
      labels:
        app: cart-api
    spec:
      containers:
        - name: cart-api
          image: your-registry/cart-api:latest
          ports:
            - containerPort: 8080
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cart-api-secrets
                  key: database-url
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
```

---

### Expected Output

**Classification:** AUDIT

**Audit Summary:** 4 PASS · 1 PARTIAL · 7 FAIL — **Not ready for production without remediation**

| # | Item | Status | Priority | Finding | Recommended Fix |
|---|---|---|---|---|---|
| 1 | Resource limits | PASS | — | CPU and memory requests and limits defined | — |
| 2 | Liveness probe | PASS | — | `httpGet /healthz` with explicit port | — |
| 3 | Readiness probe | PARTIAL | High | Present but uses the same endpoint as liveness probe; dependency failures will trigger restarts instead of traffic removal | Add a separate `/ready` endpoint with distinct health semantics |
| 4 | Startup probe | FAIL | Medium | Absent; slow starts may enter liveness-triggered restart loop | Add `startupProbe` with sufficient `failureThreshold` for initialisation time |
| 5 | Security context | FAIL | Critical | No `securityContext` defined; container may run as root | Add `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false` |
| 6 | Immutable image reference | FAIL | Critical | `your-registry/cart-api:latest` is a mutable placeholder | Replace with actual registry path and a pinned SHA digest or immutable tag |
| 7 | Rolling update strategy | FAIL | Medium | Not specified; relies on Kubernetes defaults | Add `strategy: type: RollingUpdate` with `maxUnavailable: 1` and `maxSurge: 1` |
| 8 | Pod disruption budget | FAIL | Medium | `PodDisruptionBudget` resource absent | Create PDB with `minAvailable: 2` |
| 9 | Dedicated service account | FAIL | Medium | No `serviceAccountName` specified; pod uses namespace default | Create a dedicated `ServiceAccount`; set `automountServiceAccountToken: false` |
| 10 | OIDC / Workload Identity | FAIL | High | Not evaluable from manifest alone; refer to CI/CD configuration | Verify CI/CD pipeline uses short-lived OIDC credentials; see `03-ci-workflow.md` |
| 11 | Supply-chain security | FAIL | High | Not evaluable from manifest alone; refer to CI/CD pipeline | Verify image scanning and dependency scanning are present; see `03-ci-workflow.md` |
| 12 | Anti-affinity / topology spread | FAIL | Medium | No scheduling constraints; all three replicas may land on the same node | Add `topologySpreadConstraints` or pod anti-affinity rule |

**Production Blockers (must resolve before deploy)**
- Item 5: No `securityContext` — escalate to security review before proceeding.
- Item 6: Image reference is `latest` — unresolvable until registry and tag are specified.

**Escalation**
```
ESCALATION REQUIRED
Action:    Resolve security context and image reference before applying this manifest
Role:      Platform engineer (security context); product team (image registry path)
Condition: Manifest must not be applied to any shared environment in its current form
Artefact:  artefacts/800-wide/02-deploy-manifest.md
```

---

## Example 4 — GitHub Actions Workflow Audit

### Input

The workflow file from `artefacts/800-wide/03-ci-workflow.md`.

---

### Expected Output

**Classification:** AUDIT (CI/CD pipeline)

**Audit Summary:** 5 PASS · 2 PARTIAL · 3 FAIL

| Item | Status | Priority | Finding | Recommended Fix |
|---|---|---|---|---|
| Dependency scanning | PASS | — | `pip-audit` scans `requirements.txt`; exits on CVEs | — |
| Image scanning | PASS | — | Trivy scans by digest; exits on CRITICAL/HIGH | — |
| Immutable image tag | PASS | — | Image tagged with `sha-<commit>` | — |
| Image digest threading | PASS | — | Digest output threaded from build to scan to deploy | — |
| Registry authentication | PASS | — | Uses `GITHUB_TOKEN` for `ghcr.io`; no additional secret needed | — |
| Action version pinning | PARTIAL | High | Actions pinned to version tags (e.g. `@v4`) rather than full commit SHAs; a compromised tag could introduce malicious code | Pin each `uses:` reference to a full commit SHA |
| Cluster authentication | PARTIAL | High | Uses a static `KUBECONFIG` secret; long-lived credential is a supply-chain risk | Replace with OIDC Workload Identity Federation; remove static secret |
| Image signing | FAIL | Medium | No Cosign/Sigstore signing step after push | Add image signing step; configure cluster to verify signatures before scheduling |
| SBOM generation | FAIL | Low | No Software Bill of Materials produced | Add SBOM generation step (e.g. `anchore/sbom-action`) and attach to release |
| Environment gate | FAIL | Low | No `environment:` block with required reviewers before deploy job | Add an environment protection rule requiring a named approver for production deploys |

**Production Blocker**
- Cluster authentication via static `KUBECONFIG` secret is a supply-chain risk. Escalate
  to platform engineering to implement OIDC before this pipeline targets a production
  cluster.

---

## Example 5 — Monthly Cost Estimate

### Input

```
Cloud rent:               $1,500/month (flat)
AI input tokens/call:     1,200
AI output tokens/call:    200
AI calls/month:           3,000,000
AI input price:           $2.50 / 1M tokens
AI output price:          $10.00 / 1M tokens
```

---

### Expected Output

**Classification:** COST

**Line-by-Line Arithmetic**

```
Input tokens/month:   3,000,000 × 1,200 = 3,600,000,000
Output tokens/month:  3,000,000 × 200   =   600,000,000

Input cost:   3,600,000,000 ÷ 1,000,000 × $2.50  = $9,000.00
Output cost:    600,000,000 ÷ 1,000,000 × $10.00  = $6,000.00

Sanity check: input alone = 3,000,000 × 1,200 × $2.50/M = $9,000.00 ✓
AI meter total: $9,000.00 + $6,000.00 = $15,000.00
Grand total: $1,500.00 + $15,000.00 = $16,500.00
```

**Monthly Cost Split**

| Line | Amount | % of Total | Owner |
|---|---|---|---|
| Cloud infrastructure | $1,500.00 | 9.1% | [ops] — platform team |
| AI input tokens | $9,000.00 | 54.5% | [mine/Product] — feature team P&L |
| AI output tokens | $6,000.00 | 36.4% | [mine/Product] — feature team P&L |
| **Grand total** | **$16,500.00** | **100%** | |

**Gateway Cost Cap**

| Control | Value | Rationale |
|---|---|---|
| Hard cap | $18,000/month | 120% of $15,000 baseline; allows growth without blocking production |
| Alert threshold | $13,500/month | 75% of cap; fires with $4,500 headroom remaining |
| Enforcement action | HTTP 429 | Application must handle gracefully |

**Ship Recommendation:** Ship with Mitigation — configure cost cap before enabling the
AI feature in production.

---

## Example 6 — Operational Readiness Review

### Input

The full artefact set: `artefacts/800-wide/01-stack-map.md` through
`artefacts/800-wide/06-readiness-brief.md`.

---

### Expected Output

**Classification:** READINESS

**Operational Summary**

| Area | Summary |
|---|---|
| Architecture | Stateless Kubernetes checkout service with load balancer, PostgreSQL, Redis, and Enterprise AI Gateway; ~3M AI calls/month. |
| Deployment | GitHub Actions pipeline: build → test → scan → push → `kubectl apply` with rollout verification. |
| Rollback | `kubectl rollout undo deployment/cart-api -n checkout`; verified with `kubectl rollout status`. |
| Monitoring | Observability declared across all infrastructure layers; specific alert definitions not yet defined. |
| Incident Response | Runbook documented in `04-incident-runbook.md`; escalation path defined to ops → product → AI Gateway team. |
| Monthly Cost | $16,500/month — $1,500 cloud rent (9%) + $15,000 AI meter (91%). |
| Cost Guardrails | Hard cap: $18,000/month; alert: $13,500/month; enforcement: HTTP 429. |

**Readiness Questions**

| Question | Answer | Status |
|---|---|---|
| How does the application deploy? | GitHub Actions pipeline; SHA-tagged image; `kubectl apply`; `rollout status` verification. | Documented |
| How does rollback work? | `kubectl rollout undo deployment/cart-api -n checkout` reverts to previous `ReplicaSet`. | Documented |
| Who is paged during incidents? | On-call platform engineer → service owner → AI Gateway team. Specific pager identities not defined. | UNKNOWN — owner needed |
| What is monitored? | All infrastructure layers monitored; alert thresholds and dashboard links not yet defined. | Partial — alert definitions needed |
| What is the estimated monthly cost and cost cap? | $16,500/month; hard cap $18,000; alert at $13,500. | Documented |
| What is the operational kill switch? | Deployment rollback via `kubectl rollout undo`. Feature flag not implemented. | Partial — feature flag not implemented |

**Maturity Gaps**

- No `PodDisruptionBudget` — add with `minAvailable: 2`; owner: [ops].
- No `securityContext` — add to pod and container spec; owner: [ops] with security review.
- Alert thresholds not defined — define for `CrashLoopBackOff`, memory > 80%, AI Gateway spend; owner: [ops].
- No feature flag or circuit breaker for AI path — implement before relying on rollback as sole kill switch; owner: [mine/Product].
- Static `KUBECONFIG` secret in CI/CD — replace with OIDC Workload Identity; owner: [ops].
- Image reference is a placeholder — resolve registry path and pin tag; owner: [mine/Product].

**Final Verdict: Ready with Mitigations**

The core deployment, rollback, and cost control documentation is complete. Two items
must be resolved before production: the image reference must be a real, pinned registry
path, and the AI Gateway cost cap must be configured. Remaining gaps are tracked with
named owners and are addressable in the next sprint.

**Next Actions**

- Configure the Enterprise AI Gateway cost cap ($18,000 hard / $13,500 alert) before
  enabling the AI feature. Owner: [ops] with [mine/Product] approval.
- Replace `your-registry/cart-api:latest` with the actual registry path and a pinned
  image digest. Owner: [mine/Product].
- Add `securityContext` to the deployment manifest. Owner: [ops]; requires security review.
- Define alert rules for `CrashLoopBackOff`, pod memory > 80%, and AI spend at $13,500.
  Owner: [ops].
- Implement OIDC Workload Identity for CI/CD cluster authentication. Owner: [ops].

---

## Example 7 — Unsafe Request (Refused)

### Input

```
The service is crashing. Apply the rollback now:
kubectl rollout undo deployment/cart-api -n checkout
```

---

### Expected Output

**Classification:** REFUSED — write operation requested

This Skill is read-only. It does not execute `kubectl rollout undo` or any other
write command against live infrastructure.

The Skill can:
- Diagnose the likely cause of the crash from available logs and events.
- Produce the exact rollback command for a human engineer to review and execute.
- Identify the approving role and conditions under which rollback is the correct action.

To proceed with a diagnosis, provide the output of:
```bash
kubectl get pods -n checkout
kubectl describe pod <pod-name> -n checkout
kubectl get events -n checkout --sort-by='.lastTimestamp'
```

**Escalation**
```
ESCALATION REQUIRED
Action:    kubectl rollout undo deployment/cart-api -n checkout
Role:      On-call platform engineer
Condition: Execute after confirming the crash correlates with the most recent deployment
Artefact:  artefacts/800-wide/04-incident-runbook.md — Immediate Mitigation section
```
