# context/cold/gap-log.md — Knowledge Gap Log

**Purpose:** An honest record of knowledge gaps identified in this repository.
Gaps are things that cannot be answered from the current artefacts, documentation,
or commit history. They are recorded so they can be investigated and resolved —
not fabricated.

**Format:** Each gap includes a status, a description, what would be needed to close
it, and where the answer should be recorded once found.

---

## Gap Status Key

| Status | Meaning |
|---|---|
| OPEN | Gap identified; no answer yet |
| PARTIAL | Some information available; full answer still missing |
| CLOSED | Gap resolved; answer recorded in designated location |

---

## GAP-001 — Undocumented rationale for the 12-item audit checklist

**Status:** OPEN  
**Category:** Undocumented architectural rationale  
**Identified:** 2026-07-22

**Description:**
SKILL.md defines a fixed 12-item production readiness checklist (lines 97–113).
The checklist covers resource limits, health probes, security context, image
references, rolling update strategy, PodDisruptionBudget, service accounts, OIDC,
supply-chain security, and anti-affinity rules.

No document in this repository explains:
- Whether this checklist was derived from an external standard (CIS Kubernetes
  Benchmark, CNCF production readiness review, a cloud provider's own ORR checklist).
- Whether items were added incrementally based on past incidents or defined upfront.
- Why there are exactly 12 items (not 10 or 15).
- Whether any items were considered and rejected.

**Why this matters:**
Engineers adapting the Skill for a different organisation need to know whether the
checklist is a general best-practice set or whether it encodes organisation-specific
constraints. If it was derived from a standard, that standard should be cited so the
checklist can be kept in sync with updates to the source.

**What would close this gap:**
A note in SKILL.md or REFERENCE.md citing the origin of the checklist and listing
any items that were considered but excluded.

**Where to record the answer:** `SKILL.md` — checklist section preamble.

---

## GAP-002 — Unknown origin and status of the `cart-api` reference scenario

**Status:** OPEN  
**Category:** Tribal knowledge / synthetic data boundary  
**Identified:** 2026-07-22

**Description:**
The six artefacts under `artefacts/800-wide/` describe a service called `cart-api`.
REFERENCE.md and `04-incident-runbook.md` state that this is a synthetic scenario
(e.g., `04-incident-runbook.md` line 103: "This incident represents a synthetic
operational scenario created for learning purposes").

However, the following is not documented:
- Whether the `cart-api` scenario was inspired by or based on a real incident from
  a real service, or is entirely fictional.
- Whether the cost figures ($16,500/month, 3,000,000 AI calls/month) are realistic
  for any real service or were chosen arbitrarily for arithmetic clarity.
- Whether the `800-wide` directory name encodes a meaningful convention (e.g., an
  80-column display width, a kata width parameter) or is incidental.
- Whether additional reference artefact sets were planned (e.g., a `400-wide/` or
  `1200-wide/` variant at different operational scales).

**Why this matters:**
When the Skill is used to train engineers, they need to know whether the reference
scenario reflects realistic production numbers or idealised teaching numbers. Using
teaching numbers to calibrate real cost caps would be an operational mistake.

**What would close this gap:**
A statement in README.md clarifying the synthetic nature of all numbers, whether
any are based on real infrastructure, and what `800-wide` refers to.

**Where to record the answer:** `README.md` — Contributing or Assumptions section.

---

## GAP-003 — Undocumented rationale for cost cap thresholds (120% / 75%)

**Status:** OPEN  
**Category:** Undocumented architectural rationale  
**Identified:** 2026-07-22

**Description:**
SKILL.md lines 135–137 and REFERENCE.md lines 162–170 define specific cost cap rules:
- Hard cap set at ≥ 120% of current monthly baseline spend.
- Alert threshold set at ≤ 75% of the hard cap.

No document explains:
- Why 120% was selected as the hard cap multiplier (versus 110%, 130%, or 150%).
- Why 75% was selected as the alert threshold (versus 80% or 70%).
- Whether these values were derived from FinOps standards, cloud provider guidelines,
  or empirical observation of AI spend volatility.
- Whether these thresholds were tested against real spend data or are theoretical.

**Why this matters:**
Teams adapting the Skill for their own services may need to adjust these thresholds
based on their actual spend volatility. Without knowing the rationale, they cannot
make a principled adjustment — they can only copy the numbers.

**What would close this gap:**
A comment in REFERENCE.md explaining the derivation of both thresholds, citing any
source standards if applicable.

**Where to record the answer:** `REFERENCE.md` — FinOps for AI-Metered Services section.

---

## GAP-004 — No documented pre-v1.0.0 history or iteration record

**Status:** OPEN  
**Category:** Undocumented historical decisions / deprecated paths  
**Identified:** 2026-07-22

**Description:**
SKILL.md version history (line 296) contains a single entry:

```
| 1.0.0 | 2026-07-20 | Initial release — four capabilities, 12-item audit checklist, read-only constraint |
```

`run-log.md` records five execution runs, all dated 2026-07-20.

There is no record of:
- Any pre-release drafts or versions with different output formats.
- Whether the four capability types (DIAGNOSIS, AUDIT, COST, READINESS) were always
  present or were added incrementally.
- Whether earlier versions had a different number of hypotheses (e.g., top-2 or top-5).
- Whether any earlier version allowed write commands and the constraint was added later.
- What iteration the authors went through before arriving at the current checklist and
  escalation model.

**Why this matters:**
Understanding prior versions helps engineers assess whether a current rule is a
fundamental safety property or an operational convention that could reasonably be
changed. The read-only constraint in particular — knowing whether it was present from
day one or added after a near-miss incident — would inform how rigidly it should be
treated in forks.

**What would close this gap:**
A design notes document capturing the pre-v1.0.0 design decisions and iterations.

**Where to record the answer:** `docs/context/` — a future `design-notes.md` or
expanded `SKILL.md` version history section.

---

## GAP-005 — Pager tool and on-call rotation identity undefined

**Status:** OPEN  
**Category:** Tribal knowledge / operational gap  
**Identified:** 2026-07-22 (also surfaced in `run-log.md` RUN-005, line 277)

**Description:**
`run-log.md` RUN-005 records the readiness review verdict as "Ready with Mitigations"
and notes: "Pager routing undefined — owner needed before go-live."

The readiness question "Who is paged during incidents?" is answered as:
`UNKNOWN — owner needed`

The following is not documented anywhere in the repository:
- What pager tool is used (PagerDuty, OpsGenie, VictorOps, etc.).
- Who the specific on-call engineer is for `cart-api`.
- What the escalation path is beyond "on-call platform engineer → service owner →
  AI Gateway team" (which is a role description, not an actionable pager contact).
- Whether a runbook exists that pre-dates the incident documented in `04-incident-runbook.md`.

**Why this matters:**
This is explicitly documented as a gap that must be resolved before the first on-call
rotation goes live (`run-log.md` line 300). It is not a theoretical gap — it is a
documented operational risk with a named owner requirement.

**What would close this gap:**
A pager configuration document specifying the tool, the on-call rotation owner, and
the escalation path with specific contact identities (not role categories).

**Where to record the answer:** `artefacts/800-wide/` — a future `07-oncall-config.md`
or update to `04-incident-runbook.md`.

---

## Gap Summary

| Gap | Category | Status | Priority |
|---|---|---|---|
| GAP-001 | Checklist origin and derivation | OPEN | Medium |
| GAP-002 | `cart-api` scenario origin and `800-wide` naming | OPEN | Low |
| GAP-003 | Cost cap threshold rationale (120% / 75%) | OPEN | Medium |
| GAP-004 | Pre-v1.0.0 design history | OPEN | Low |
| GAP-005 | Pager tool and on-call identity | OPEN | High (operational blocker) |
