#!/usr/bin/env bash
# =============================================================================
# scripts/ci/validate-skill.sh
#
# Purpose:
#   Validates the integrity of the repository's engineering assets:
#     - skills/cloud-operations-analysis/SKILL.md  (the portable Skill)
#     - CLAUDE.md                                  (the hot context bundle)
#
# This script is the single source of logic for the skill-integrity CI gate.
# The GitHub Actions workflow (.github/workflows/skill-integrity.yml) calls
# this script directly; no validation logic lives in the YAML.
#
# Exit codes:
#   0  — all checks passed; repository assets are intact
#   1  — one or more checks failed; details printed to stdout
#
# Usage:
#   bash scripts/ci/validate-skill.sh          # from repository root
#   bash scripts/ci/validate-skill.sh --help   # print this header and exit 0
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths (relative to repository root; script must be run from root)
# ---------------------------------------------------------------------------
SKILL_FILE="skills/cloud-operations-analysis/SKILL.md"
CLAUDE_FILE="CLAUDE.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
FAILURES=0

fail() {
  echo "FAIL: $1"
  FAILURES=$(( FAILURES + 1 ))
}

pass() {
  echo "PASS: $1"
}

# ---------------------------------------------------------------------------
# Handle --help
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--help" ]]; then
  # Print every line of the opening comment block (lines beginning with #)
  awk '/^#!/{next} /^#/{print} /^[^#]/{exit}' "$0"
  exit 0
fi

echo "=== Skill Integrity Check ==="
echo "SKILL file : $SKILL_FILE"
echo "CLAUDE file: $CLAUDE_FILE"
echo ""

# ---------------------------------------------------------------------------
# CHECK 1 — SKILL.md exists
# ---------------------------------------------------------------------------
if [[ -f "$SKILL_FILE" ]]; then
  pass "SKILL.md exists at $SKILL_FILE"
else
  fail "SKILL.md not found at $SKILL_FILE"
fi

# ---------------------------------------------------------------------------
# CHECK 2 — CLAUDE.md exists
# ---------------------------------------------------------------------------
if [[ -f "$CLAUDE_FILE" ]]; then
  pass "CLAUDE.md exists"
else
  fail "CLAUDE.md not found"
fi

# ---------------------------------------------------------------------------
# Remaining checks depend on both files being present.
# If either is missing, report and exit now — no point reading absent files.
# ---------------------------------------------------------------------------
if (( FAILURES > 0 )); then
  echo ""
  echo "=== Result: FAILED ($FAILURES check(s) failed) ==="
  exit 1
fi

# ---------------------------------------------------------------------------
# CHECK 3 — SKILL.md has YAML frontmatter (opening --- delimiter)
#
# Valid frontmatter starts on line 1 with exactly "---" and closes with a
# second "---" line before the body begins. We check for the opening delimiter
# on line 1 and at least one closing delimiter within the first 60 lines.
# ---------------------------------------------------------------------------
first_line=$(head -1 "$SKILL_FILE")
if [[ "$first_line" == "---" ]]; then
  pass "SKILL.md has YAML frontmatter opening delimiter"
else
  fail "SKILL.md does not start with YAML frontmatter (expected '---' on line 1, got: '$first_line')"
fi

# Locate the closing --- of the frontmatter block (second occurrence of "---")
closing_line=$(awk '/^---/{count++; if(count==2){print NR; exit}}' "$SKILL_FILE")
if [[ -n "$closing_line" ]]; then
  pass "SKILL.md frontmatter closing delimiter found at line $closing_line"
else
  fail "SKILL.md frontmatter closing delimiter ('---') not found — frontmatter block is unclosed"
fi

# ---------------------------------------------------------------------------
# Extract the frontmatter block for field checks (between the two --- lines).
# We do this once and reuse it for checks 4, 5, 6.
# ---------------------------------------------------------------------------
if [[ -n "$closing_line" ]]; then
  # Lines 2 through (closing_line - 1) are the frontmatter body
  frontmatter=$(awk "NR>1 && NR<${closing_line}" "$SKILL_FILE")
else
  frontmatter=""
fi

# ---------------------------------------------------------------------------
# CHECK 4 — frontmatter contains required field: name
# ---------------------------------------------------------------------------
if echo "$frontmatter" | grep -qE '^name:'; then
  pass "Frontmatter contains 'name' field"
else
  fail "Frontmatter is missing required field: 'name'"
fi

# ---------------------------------------------------------------------------
# CHECK 5 — frontmatter contains required field: description
# ---------------------------------------------------------------------------
if echo "$frontmatter" | grep -qE '^description:'; then
  pass "Frontmatter contains 'description' field"
else
  fail "Frontmatter is missing required field: 'description'"
fi

# ---------------------------------------------------------------------------
# CHECK 6 — frontmatter contains required field: compatibility
# ---------------------------------------------------------------------------
if echo "$frontmatter" | grep -qE '^compatibility:'; then
  pass "Frontmatter contains 'compatibility' field"
else
  fail "Frontmatter is missing required field: 'compatibility'"
fi

# ---------------------------------------------------------------------------
# CHECK 7 — SKILL.md body is not empty
#
# "Body" = everything after the closing --- of the frontmatter.
# We consider the body empty if it contains no non-whitespace characters.
# ---------------------------------------------------------------------------
if [[ -n "$closing_line" ]]; then
  body=$(awk "NR>${closing_line}" "$SKILL_FILE")
  if echo "$body" | grep -qE '\S'; then
    pass "SKILL.md body is not empty"
  else
    fail "SKILL.md body is empty (no content after the frontmatter closing delimiter)"
  fi
else
  fail "SKILL.md body cannot be checked — frontmatter is malformed"
fi

# ---------------------------------------------------------------------------
# CHECK 8 — CLAUDE.md contains the Repository Context section
#
# This section was introduced by K 5.D.2 to hold all repository-specific
# assumptions. Its absence means the context bundle has been degraded.
# ---------------------------------------------------------------------------
if grep -qF "## Repository Context" "$CLAUDE_FILE"; then
  pass "CLAUDE.md contains '## Repository Context' section"
else
  fail "CLAUDE.md is missing the '## Repository Context' section — context bundle may have been degraded"
fi

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
echo ""
if (( FAILURES == 0 )); then
  echo "=== Result: PASSED (all checks passed) ==="
  exit 0
else
  echo "=== Result: FAILED ($FAILURES check(s) failed) ==="
  exit 1
fi
