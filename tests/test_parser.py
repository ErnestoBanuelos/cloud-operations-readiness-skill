"""
test_parser.py — Parser surface extraction tests.

All input data is synthetic.  Tests verify that parsers:
  1. Accept valid input and return the correct container type.
  2. Raise TypeError on wrong input types.
  3. Extract surface-level signals correctly (v0.1 scope).
"""

import pytest

from readiness_engine.models import UNKNOWN
from readiness_engine.parser import (
    RawAuditInput,
    RawCostInput,
    RawDiagnosisInput,
    RawReadinessInput,
    parse_audit_input,
    parse_cost_input,
    parse_diagnosis_input,
    parse_readiness_input,
)

# ---------------------------------------------------------------------------
# parse_diagnosis_input
# ---------------------------------------------------------------------------


class TestParseDiagnosisInput:
    def test_returns_correct_type(self) -> None:
        result = parse_diagnosis_input("OOMKilled pod cart-api-abc")
        assert isinstance(result, RawDiagnosisInput)

    def test_raw_text_is_stripped(self) -> None:
        result = parse_diagnosis_input("  some text  ")
        assert result.raw_text == "some text"

    def test_empty_string_accepted(self) -> None:
        result = parse_diagnosis_input("")
        assert result.raw_text == ""

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError):
            parse_diagnosis_input(123)  # type: ignore[arg-type]

    def test_default_pod_name_is_unknown(self) -> None:
        result = parse_diagnosis_input("some log output")
        assert result.pod_name == UNKNOWN


# ---------------------------------------------------------------------------
# parse_audit_input
# ---------------------------------------------------------------------------

MANIFEST_WITH_LATEST = """\
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
          securityContext:
            runAsNonRoot: true
          resources:
            limits:
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
          readinessProbe:
            httpGet:
              path: /ready
"""

MANIFEST_WITHOUT_ISSUES = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: safe-service
spec:
  template:
    spec:
      containers:
        - name: safe-service
          image: ghcr.io/example/safe-service@sha256:abc123
"""


class TestParseAuditInput:
    def test_returns_correct_type(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert isinstance(result, RawAuditInput)

    def test_detects_latest_tag(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert result.has_image_tag_latest is True

    def test_no_latest_tag_when_digest_used(self) -> None:
        result = parse_audit_input(MANIFEST_WITHOUT_ISSUES)
        assert result.has_image_tag_latest is False

    def test_detects_security_context(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert result.has_security_context is True

    def test_detects_resource_limits(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert result.has_resource_limits is True

    def test_detects_liveness_probe(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert result.has_liveness_probe is True

    def test_detects_readiness_probe(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert result.has_readiness_probe is True

    def test_detects_deployment_kind(self) -> None:
        result = parse_audit_input(MANIFEST_WITH_LATEST)
        assert result.input_kind == "Deployment"

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError):
            parse_audit_input({"key": "val"})  # type: ignore[arg-type]

    def test_no_security_context_in_minimal_manifest(self) -> None:
        result = parse_audit_input(MANIFEST_WITHOUT_ISSUES)
        assert result.has_security_context is False


# ---------------------------------------------------------------------------
# parse_audit_input — :latest detection boundary cases
#
# Adversarial Pass (pre-mortem Cause 2): the previous implementation used a
# raw ":latest" substring scan across the entire manifest text.  This
# triggered false positives when ":latest" appeared in comments, annotations,
# or label values rather than on an actual YAML image: field line.
#
# The fix anchors detection to lines matching:
#   ^\s*-?\s*image:\s*\S+:latest\s*$
#
# The four tests below document the correct behaviour after the fix.
# ---------------------------------------------------------------------------

MANIFEST_LATEST_IMAGE_FIELD = """\
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
"""

MANIFEST_DIGEST_WITH_LATEST_ANNOTATION = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
  annotations:
    deployment.kubernetes.io/previous-image: "ghcr.io/example/cart-api:latest"
spec:
  template:
    spec:
      containers:
        - name: cart-api
          image: ghcr.io/example/cart-api@sha256:abc123def456
"""

MANIFEST_LATEST_IN_COMMENT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
# Previously used :latest — now pinned to digest
spec:
  template:
    spec:
      containers:
        - name: cart-api
          image: ghcr.io/example/cart-api@sha256:abc123def456
"""

MANIFEST_LATEST_IN_LABEL = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cart-api
  labels:
    image-policy: allow-latest
spec:
  template:
    spec:
      containers:
        - name: cart-api
          image: ghcr.io/example/cart-api@sha256:abc123def456
"""


class TestParseAuditInputLatestDetectionBoundary:
    """
    Verify that :latest is detected only on actual YAML image: field lines.

    Traceable to: Adversarial Pass — pre-mortem Cause 2 (false-positive
    detection of ':latest' outside Kubernetes image fields).
    Fix: _IMAGE_LATEST_RE anchors match to image: field lines only.
    """

    def test_image_field_with_latest_tag_is_detected(self) -> None:
        """
        Positive: image: repo/app:latest on an image: line → detected.

        Represents the standard case the signal is designed to catch.
        """
        result = parse_audit_input(MANIFEST_LATEST_IMAGE_FIELD)
        assert result.has_image_tag_latest is True

    def test_latest_in_annotation_with_digest_image_not_detected(self) -> None:
        """
        Negative: annotation value contains ':latest'; image: field uses digest.

        The annotation is not an image reference.  The live container uses a
        digest.  has_image_tag_latest must be False.
        """
        result = parse_audit_input(MANIFEST_DIGEST_WITH_LATEST_ANNOTATION)
        assert result.has_image_tag_latest is False

    def test_latest_in_comment_not_detected(self) -> None:
        """
        Negative: comment line contains ':latest'; image: field uses digest.

        Comment text must not trigger the image-tag signal.
        """
        result = parse_audit_input(MANIFEST_LATEST_IN_COMMENT)
        assert result.has_image_tag_latest is False

    def test_latest_in_label_value_not_detected(self) -> None:
        """
        Negative: label value contains 'latest'; image: field uses digest.

        A label such as 'image-policy: allow-latest' must not trigger
        the signal.  The label value does not contain the ':latest' tag
        pattern on an image: field line.
        """
        result = parse_audit_input(MANIFEST_LATEST_IN_LABEL)
        assert result.has_image_tag_latest is False


# ---------------------------------------------------------------------------
# parse_cost_input — dict form
# ---------------------------------------------------------------------------

VALID_COST_DICT = {
    "cloud_rent": 1500.0,
    "ai_calls_per_month": 3_000_000,
    "input_tokens_per_call": 500,
    "output_tokens_per_call": 200,
    "price_per_1m_input": 2.50,
    "price_per_1m_output": 10.00,
}


class TestParseCostInputDict:
    def test_returns_correct_type(self) -> None:
        result = parse_cost_input(VALID_COST_DICT)
        assert isinstance(result, RawCostInput)

    def test_cloud_rent_extracted(self) -> None:
        result = parse_cost_input(VALID_COST_DICT)
        assert result.cloud_rent == pytest.approx(1500.0)

    def test_ai_calls_per_month_extracted(self) -> None:
        result = parse_cost_input(VALID_COST_DICT)
        assert result.ai_calls_per_month == 3_000_000

    def test_price_per_1m_input_extracted(self) -> None:
        result = parse_cost_input(VALID_COST_DICT)
        assert result.price_per_1m_input == pytest.approx(2.50)

    def test_price_per_1m_output_extracted(self) -> None:
        result = parse_cost_input(VALID_COST_DICT)
        assert result.price_per_1m_output == pytest.approx(10.00)

    def test_missing_keys_return_none(self) -> None:
        result = parse_cost_input({})
        assert result.cloud_rent is None
        assert result.ai_calls_per_month is None

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError):
            parse_cost_input(42)  # type: ignore[arg-type]


class TestParseCostInputString:
    def test_string_input_returns_container_with_raw_text(self) -> None:
        result = parse_cost_input("cloud rent $1500/month, AI meter $15000/month")
        assert isinstance(result, RawCostInput)
        assert "cloud rent" in result.raw_text

    def test_string_input_leaves_numeric_fields_as_none(self) -> None:
        result = parse_cost_input("some cost description")
        assert result.cloud_rent is None
        assert result.ai_calls_per_month is None


# ---------------------------------------------------------------------------
# parse_readiness_input
# ---------------------------------------------------------------------------


class TestParseReadinessInput:
    def test_returns_correct_type(self) -> None:
        result = parse_readiness_input("Is cart-api ready for production?")
        assert isinstance(result, RawReadinessInput)

    def test_raw_text_is_stripped(self) -> None:
        result = parse_readiness_input("  readiness review  ")
        assert result.raw_text == "readiness review"

    def test_default_service_name_is_unknown(self) -> None:
        result = parse_readiness_input("conduct a readiness review")
        assert result.service_name == UNKNOWN

    def test_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError):
            parse_readiness_input(None)  # type: ignore[arg-type]
