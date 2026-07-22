"""
test_classifier.py — Classification accuracy tests.

All inputs are synthetic.  Tests verify that the classify() function returns
the expected RequestType for representative samples of each input category.

Test structure
--------------
- Positive cases: one representative fixture per RequestType.
- Negative cases: empty/whitespace returns None.
- Boundary cases: multi-signal inputs resolve to the expected priority winner.
"""

from readiness_engine.classifier import classify
from readiness_engine.models import RequestType

# ---------------------------------------------------------------------------
# Synthetic fixtures — one per category
# ---------------------------------------------------------------------------

DIAGNOSIS_INPUT = """\
Warning  BackOff   21s (x5 over 2m)  kubelet   Back-off restarting failed container
Normal   Pulled    3m                 kubelet   Successfully pulled image
kubectl describe pod cart-api-abc123 -n checkout
Last State: Terminated
  Reason: OOMKilled
  Exit Code: 137
  Restart Count: 5
"""

AUDIT_INPUT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
spec:
  template:
    spec:
      containers:
        - name: cart-api
          image: ghcr.io/example/cart-api:latest
          resources:
            requests:
              memory: "256Mi"
"""

COST_INPUT = """\
Cloud rent: $1,500 / month
AI meter: 3,000,000 calls at $2.50 per 1M input tokens
Monthly total cost estimate: $16,500
Hard cap: $18,000
Alert threshold: $13,500
"""

READINESS_INPUT = """\
We are conducting an operational readiness review for cart-api.
Please evaluate the artefact set (01-stack-map through 06-readiness-brief)
and produce a go/no-go decision with a maturity gap inventory.
"""


class TestPositiveClassification:
    """Each canonical input classifies to the expected RequestType."""

    def test_diagnosis_input_classified_as_diagnosis(self) -> None:
        result = classify(DIAGNOSIS_INPUT)
        assert result == RequestType.DIAGNOSIS

    def test_audit_input_classified_as_audit(self) -> None:
        result = classify(AUDIT_INPUT)
        assert result == RequestType.AUDIT

    def test_cost_input_classified_as_cost(self) -> None:
        result = classify(COST_INPUT)
        assert result == RequestType.COST

    def test_readiness_input_classified_as_readiness(self) -> None:
        result = classify(READINESS_INPUT)
        assert result == RequestType.READINESS


class TestNegativeClassification:
    """Inputs with no recognisable signals return None."""

    def test_empty_string_returns_none(self) -> None:
        assert classify("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert classify("   \n\t  ") is None

    def test_unrelated_text_returns_none(self) -> None:
        assert classify("The quick brown fox jumps over the lazy dog.") is None


class TestPriorityResolution:
    """Multi-signal inputs resolve to the highest-priority type."""

    def test_diagnosis_beats_audit_on_mixed_input(self) -> None:
        """OOMKilled + Deployment manifest -> DIAGNOSIS wins."""
        mixed = DIAGNOSIS_INPUT + "\n" + AUDIT_INPUT
        result = classify(mixed)
        assert result == RequestType.DIAGNOSIS

    def test_diagnosis_beats_cost_on_mixed_input(self) -> None:
        mixed = DIAGNOSIS_INPUT + "\n" + COST_INPUT
        result = classify(mixed)
        assert result == RequestType.DIAGNOSIS

    def test_audit_beats_cost_on_mixed_input(self) -> None:
        """Manifest YAML + cost figures -> AUDIT wins."""
        mixed = AUDIT_INPUT + "\n" + COST_INPUT
        result = classify(mixed)
        assert result == RequestType.AUDIT


class TestCaseInsensitivity:
    """Classification patterns must be case-insensitive."""

    def test_oomkilled_lowercase(self) -> None:
        result = classify("pod terminated with reason oomkilled exit code 137")
        assert result == RequestType.DIAGNOSIS

    def test_kind_deployment_mixedcase(self) -> None:
        result = classify("kind: deployment\napiVersion: apps/v1")
        assert result == RequestType.AUDIT
