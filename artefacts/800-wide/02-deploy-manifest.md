# Deployment Manifest Review

This document contains the initial Kubernetes deployment manifest for the `cart-api` service together with an independent production-readiness audit.

The objective is not only to generate a valid Kubernetes manifest, but to demonstrate the engineering practice of validating AI-generated infrastructure artifacts through an independent review before they are considered for production deployment.

---

# Service Overview

**Service:** `cart-api`

The `cart-api` service is a stateless checkout backend deployed on Kubernetes. It serves HTTP traffic on port **8080**, stores cart data in PostgreSQL, uses Redis as a cache layer, and calls an Enterprise AI Gateway for the **"Summarize my cart"** feature.

Deployment assumptions:

- 3 replicas
- ~512 MiB memory per replica
- HTTP endpoint: `/healthz`
- Secrets provided through Kubernetes Secrets
- Internal communication via a ClusterIP Service

---

# Kubernetes Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
  namespace: checkout
  labels:
    app: cart-api
    component: backend
    version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cart-api
  template:
    metadata:
      labels:
        app: cart-api
        component: backend
        version: "1.0.0"
    spec:
      containers:
        - name: cart-api
          image: your-registry/cart-api:latest
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cart-api-secrets
                  key: database-url
            - name: AI_GATEWAY_API_KEY
              valueFrom:
                secretKeyRef:
                  name: cart-api-secrets
                  key: ai-gateway-api-key
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
---
apiVersion: v1
kind: Service
metadata:
  name: cart-api
  namespace: checkout
  labels:
    app: cart-api
    component: backend
spec:
  selector:
    app: cart-api
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
```

---

# Manifest Notes

- Secrets (`DATABASE_URL`, `AI_GATEWAY_API_KEY`) are referenced through Kubernetes Secrets and are expected to be provisioned independently.
- The image tag `latest` is intentionally used as a placeholder in this first draft.
- The service assumes ingress and load balancing are handled externally.
- This manifest represents an initial AI-generated baseline prior to production review.

---

# Independent Production Readiness Audit

The manifest was reviewed in a **fresh AI session** to simulate an independent Pull Request review by a Site Reliability Engineer (SRE).

## Audit Findings

| Finding | Why it Matters | Priority | Recommended Fix |
|----------|----------------|----------|-----------------|
| Mutable image tag (`latest`) | Prevents deterministic deployments and reliable rollbacks. Different pods may run different versions. | **Critical** | Use immutable image tags or image digests (SHA256). |
| Missing `securityContext` | Containers may run with unnecessary privileges, increasing security risk. | **Critical** | Configure `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, and drop Linux capabilities. |
| Shared liveness/readiness endpoint | Dependency failures could trigger unnecessary container restarts instead of temporarily removing pods from service. | **High** | Separate `/live` and `/ready` endpoints with distinct health semantics. |
| No explicit RollingUpdate strategy | Deployment behavior relies on Kubernetes defaults. | **Medium** | Define `strategy.type: RollingUpdate` with explicit `maxUnavailable` and `maxSurge` values. |
| Missing `startupProbe` | Slow-starting applications may enter restart loops before becoming healthy. | **Medium** | Add a `startupProbe` for initialization workloads. |
| Missing dedicated `ServiceAccount` | Pods inherit the namespace default service account, potentially violating least privilege. | **Medium** | Create a dedicated ServiceAccount and disable automatic token mounting unless required. |
| Missing `NetworkPolicy` | Pods may accept unrestricted traffic from other workloads in the cluster. | **Medium** | Restrict ingress and egress traffic using Kubernetes NetworkPolicies. |
| Missing `PodDisruptionBudget` | Planned maintenance could temporarily evict all replicas. | **Medium** | Configure a PDB to maintain service availability during voluntary disruptions. |
| Missing anti-affinity / topology spread | All replicas could be scheduled on the same node or availability zone. | **Medium** | Configure pod anti-affinity or topology spread constraints. |
| Missing observability annotations | Metrics collection may require additional manual configuration. | **Low** | Add Prometheus scrape annotations and standardized logging configuration. |
| Missing `revisionHistoryLimit` | Rollback history relies on Kubernetes defaults. | **Low** | Explicitly configure a revision history appropriate for the deployment strategy. |
| Implicit `imagePullPolicy` | Runtime behavior depends on Kubernetes defaults. | **Low** | Explicitly define the desired pull policy. |

---

# Positive Findings

The review also identified several good engineering practices already present in the manifest.

- Uses Kubernetes Secrets instead of hardcoded credentials.
- Defines both resource requests and limits.
- Includes separate liveness and readiness probes.
- Uses an internal `ClusterIP` Service suitable for backend workloads.
- Defines a dedicated namespace.
- Uses consistent labels and selectors.
- Deploys three replicas for basic availability.
- Keeps infrastructure concerns separated from application behavior.

---

# Overall Assessment

The generated manifest provides a solid baseline for a Kubernetes deployment and demonstrates many production-oriented practices expected from an AI-generated first draft.

However, an independent review identified several infrastructure controls that should be addressed before approving deployment to a production environment. Most findings relate to operational resilience, security hardening, deployment safety, and high availability rather than functional correctness.

This reinforces the primary lesson of the kata:

> Generating Kubernetes YAML is easy. Reviewing it critically is the engineering skill.

---

# Production Readiness Summary

**Estimated readiness score:** **78 / 100**

### Production blockers

- Replace mutable image tags.
- Add a container and pod `securityContext`.

### Recommended before production

- Configure an explicit rolling update strategy.
- Add a startup probe.
- Introduce a dedicated ServiceAccount.
- Define NetworkPolicies.
- Configure PodDisruptionBudget and scheduling constraints.
- Improve observability metadata.

---

# Assumptions

- This manifest is a simplified reference example for learning purposes.
- Cloud-provider-specific resources (Ingress, Load Balancer, Secret management, monitoring stack, autoscaling) are intentionally omitted.
- The audit reflects general Kubernetes and SRE best practices and may vary depending on organizational standards, platform capabilities, and service-level objectives.
- The deployment manifest is intended as an architectural and operational artifact rather than a production-ready Infrastructure-as-Code template.