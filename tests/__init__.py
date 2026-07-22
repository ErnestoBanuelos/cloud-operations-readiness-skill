"""
tests/ — Verification assets for the Reference Engine.

Test modules
------------
test_models.py      — Invariants on domain constants and enumerations.
test_classifier.py  — Classification accuracy against labelled fixtures.
test_validator.py   — Structural validation rules from SKILL.md.
test_parser.py      — Parser surface extraction from synthetic inputs.

All tests use synthetic data only (CLAUDE.md §Escalation Gates).
No external network calls, no live cluster connections.
"""
