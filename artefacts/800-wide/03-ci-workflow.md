# CI/CD Workflow Review

This document contains the initial GitHub Actions workflow for the `cart-api` service together with an independent supply-chain security audit.

The objective is not only to automate the build and deployment process, but also to demonstrate the engineering practice of validating AI-generated CI/CD workflows through an independent security review before they are trusted to deliver software into production.

---

# Service Overview

**Service:** `cart-api`

The `cart-api` service is deployed as a containerized application on Kubernetes. The CI/CD pipeline is responsible for building, testing, scanning, packaging, publishing, and deploying the application on every push to the `main` branch.

The workflow follows this high-level lifecycle:

- Build the application
- Execute unit tests
- Scan application dependencies
- Build and publish a container image
- Scan the container image
- Deploy to Kubernetes
- Verify deployment rollout

---

# GitHub Actions Workflow

```yaml
name: cart-api CI

on:
  push:
    branches:
      - main

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/cart-api

jobs:
  build-test:
    name: Build and Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run unit tests
        run: pytest tests/

  scan-dependencies:
    name: Dependency Scan
    runs-on: ubuntu-latest
    needs: build-test

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Scan dependencies
        uses: pypa/gh-action-pip-audit@v1.1.0
        with:
          inputs: requirements.txt

  build-push-image:
    name: Build and Push Image
    runs-on: ubuntu-latest
    needs: scan-dependencies

    permissions:
      contents: read
      packages: write

    outputs:
      image_digest: ${{ steps.push.outputs.digest }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-

      - name: Build and push
        id: push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  scan-image:
    name: Container Image Scan
    runs-on: ubuntu-latest
    needs: build-push-image

    steps:
      - name: Scan image
        uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build-push-image.outputs.image_digest }}
          format: table
          exit-code: "1"
          severity: CRITICAL,HIGH

  deploy:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    needs: scan-image

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure kubeconfig
        run: |
          mkdir -p $HOME/.kube
          echo "${{ secrets.KUBECONFIG }}" > $HOME/.kube/config

      - name: Substitute image tag
        run: |
          sed -i "s|your-registry/cart-api:latest|${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build-push-image.outputs.image_digest }}|g" \
            artefacts/800-wide/02-deploy-manifest.md

      - name: Apply manifest
        run: |
          kubectl apply -f artefacts/800-wide/02-deploy-manifest.md --namespace checkout

      - name: Verify rollout
        run: |
          kubectl rollout status deployment/cart-api --namespace checkout --timeout=120s
```

---

# Workflow Notes

- Uses GitHub Container Registry (`ghcr.io`) with the built-in `GITHUB_TOKEN`.
- Images are referenced by immutable digest instead of mutable tags.
- Dependency scanning is performed using `pip-audit`.
- Container image scanning is performed using Trivy.
- Deployment references the exact image digest that was scanned.
- Rollout status is verified after deployment.
- This workflow represents an initial AI-generated implementation and requires an independent security review before production use.

---

# Independent Supply Chain Security Audit

The workflow was reviewed in a **fresh AI session** to simulate an independent Pull Request review performed by a Senior DevSecOps Engineer.

## Audit Findings

| Control | Status | Priority | Recommendation |
|----------|--------|----------|----------------|
| **Pinned GitHub Actions** | Partial | **High** | Replace mutable version tags (`@v4`, `@v5`, `@v6`) with immutable commit SHAs for every third-party GitHub Action. |
| **OIDC Authentication** | Partial | **High** | Replace the long-lived `KUBECONFIG` repository secret with short-lived OIDC-based authentication provided by the cloud platform. |
| **Image Signing & Provenance** | Missing | **High** | Sign published container images with Cosign/Sigstore and generate SLSA provenance attestations. |
| **Dependency Security** | Partial | **Medium** | Strengthen dependency verification and ensure dependency validation occurs before production deployment. |
| **Container Image Security** | Present | **Low** | Continue using Trivy and publish scan results in SARIF format for centralized security reporting. |
| **Least-Privilege Permissions** | Partial | **Medium** | Define workflow-level `permissions: read-all` and grant only the permissions required by each individual job. |
| **Deployment Safety / Rollback Gate** | Missing | **High** | Introduce deployment approvals through protected environments and implement an automated rollback path if rollout verification fails. |

---

# Positive Findings

The review identified several engineering decisions that already align with modern CI/CD best practices.

- Uses immutable image digests throughout the build, scan, and deployment stages.
- Performs dependency vulnerability scanning.
- Performs container image vulnerability scanning using Trivy.
- Blocks deployments when HIGH or CRITICAL vulnerabilities are detected.
- Uses GitHub's built-in `GITHUB_TOKEN` for container registry authentication instead of storing separate registry credentials.
- Verifies Kubernetes rollout completion after deployment.
- Separates the pipeline into logical build, scan, publish, and deployment stages.

---

# Overall Assessment

The workflow demonstrates a solid CI/CD foundation and follows many modern engineering practices, including immutable image deployment, automated vulnerability scanning, and rollout verification.

However, several important supply-chain security controls remain incomplete. Most findings relate to software supply-chain integrity, credential management, deployment governance, and artifact trust rather than pipeline functionality.

The independent review highlights an important engineering principle:

> A functional pipeline is not necessarily a trustworthy pipeline.

---

# Production Readiness Summary

**Estimated readiness score:** **82 / 100**

## Production blockers

- Pin all third-party GitHub Actions to immutable commit SHAs.
- Replace static Kubernetes credentials with OIDC-based authentication.
- Implement image signing and provenance generation.
- Introduce deployment approval and rollback controls.

## Recommended improvements

- Define workflow-wide least-privilege permissions.
- Improve dependency verification.
- Publish security scan results to GitHub Security.
- Add dependency and Docker layer caching to improve execution performance.

---

# Assumptions

- This workflow is a simplified reference example intended for educational purposes.
- Cloud-provider-specific authentication, deployment targets, and registry configuration are intentionally omitted.
- Security recommendations reflect current DevSecOps and software supply-chain best practices but may vary depending on organizational policies and platform capabilities.
- The workflow is intended as an architectural and operational reference rather than a production-ready CI/CD pipeline.