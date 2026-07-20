# Incident Analysis & Runbook Review

This document contains the incident analysis for the `cart-api` service together with an independent operational review of the diagnosis and runbook.

The objective is to demonstrate a structured incident response process by identifying evidence-based hypotheses, defining immediate mitigation actions, and producing a reusable operational runbook for future incidents.

---

# Incident Summary

Approximately 20 minutes after deploying the **"Summarize my cart"** AI feature, half of the `cart-api` pods entered `CrashLoopBackOff`.

Kubernetes events identified `OOMKilled` as the termination reason.

As replicas became unavailable, the remaining healthy pods absorbed additional traffic, increasing latency and application error rates.

Although no complete outage occurred, service availability degraded significantly.

---

# Independent Incident Review

The incident analysis was reviewed independently in a fresh AI session to validate the technical reasoning, operational usefulness, and suitability of the document as a reusable production runbook.

## Review Findings

| Review Area | Assessment | Recommendation |
|--------------|------------|----------------|
| Incident Summary | Good | Include deployment version, timestamps, and customer impact metrics for future production incidents. |
| Observed Symptoms | Good | Quantify latency, error rate, and memory utilization where monitoring data is available. |
| Ranked Hypotheses | Good | Hypotheses are evidence-based and properly ranked. Additional memory profiling would increase diagnostic confidence. |
| Immediate Mitigation | Good | Rollback is correctly identified as the safest first response to restore service availability. |
| Long-Term Corrective Actions | Good | Continue assigning clear ownership and prioritize memory profiling before increasing resource limits. |
| Operational Runbook | Good | The runbook provides actionable recovery steps suitable for L2 support. Future versions could reference monitoring dashboards and alert identifiers. |
| Lessons Learned | Good | Convert architectural lessons into measurable engineering actions tracked through operational work items. |

---

# Overall Assessment

The incident analysis demonstrates a structured operational approach consistent with modern Site Reliability Engineering practices.

Rather than immediately assuming a solution, the document prioritizes evidence-based hypotheses, identifies the least expensive diagnostic actions, recommends rollback as the primary stabilization mechanism, and separates immediate mitigation from permanent corrective actions.

The independent review concluded that the document is suitable as the foundation for an operational runbook, with opportunities to improve observability references and incident metrics.

---

# Confidence in Diagnosis

**Estimated confidence:** **90 / 100**

The strongest evidence is the combination of:

- `OOMKilled` Kubernetes events.
- Symptoms beginning shortly after introducing the AI-powered feature.
- Delayed failure pattern suggesting runtime memory growth rather than startup failure.
- Increased latency on surviving replicas caused by reduced cluster capacity.

While additional heap profiling would distinguish between payload accumulation and a true memory leak, the overall diagnosis is strongly supported by the available operational evidence.

---

# Runbook Readiness Summary

**Estimated readiness score:** **88 / 100**

## Strengths

- Evidence-based incident analysis.
- Clearly ranked hypotheses.
- Appropriate rollback strategy.
- Practical Kubernetes diagnostic commands.
- Defined ownership between Platform Operations and Product Engineering.
- Reusable operational runbook structure.

## Recommended Improvements

- Include deployment version and incident timeline.
- Reference specific monitoring dashboards and alert names.
- Capture quantitative metrics (memory usage, latency, error rate).
- Link corrective actions to engineering work items.
- Document alternative mitigation strategies when rollback is not immediately possible.

---

# Positive Findings

The independent review highlighted several strong engineering practices.

- Root cause investigation is based on observable evidence instead of assumptions.
- Hypotheses are prioritized by likelihood.
- Diagnostic steps prioritize low-cost validation before deeper investigation.
- Immediate rollback minimizes customer impact.
- Long-term corrective actions distinguish operational improvements from application changes.
- Ownership boundaries between Platform Operations and Product Engineering are clearly defined.
- Lessons learned reinforce operational readiness for AI-enabled services.

---

# Assumptions

- This incident represents a synthetic operational scenario created for learning purposes.
- Monitoring platforms, alert names, dashboards, and escalation systems vary by organization and are intentionally omitted.
- Commands assume appropriate Kubernetes RBAC permissions.
- The incident references the deployment described in `02-deploy-manifest.md` and the CI/CD workflow documented in `03-ci-workflow.md`.