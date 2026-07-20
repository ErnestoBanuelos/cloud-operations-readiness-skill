# Monthly Cost Estimate — `cart-api`

This document estimates the monthly running cost of the `cart-api` service, splits spend
between fixed cloud infrastructure and the variable AI meter, attributes ownership, and
sets a gateway cost cap to prevent uncapped AI spend.

---

## Cost Inputs

| Parameter | Value | Source |
|---|---|---|
| Cloud rent (3 pods + PostgreSQL + Redis + load balancer) | $1,500.00 / month | Flat infrastructure estimate |
| AI input tokens per call | 1,200 | System prompt + cart contents |
| AI output tokens per call | 200 | Generated summary |
| AI calls per month | 3,000,000 | Observed traffic volume |
| AI input price | $2.50 / 1M tokens | Reference price list |
| AI output price | $10.00 / 1M tokens | Reference price list |

> **Pricing note.** The input and output rates above ($2.50 / $10.00 per 1M tokens) match
> the kata reference price list and are consistent with mid-tier LLM API pricing as of the
> date of this document. Current OpenAI API pricing for comparable models
> (e.g. `gpt-5.6-terra` standard) is $2.50 input / $15.00 output per 1M tokens. The
> estimate uses the stated rates; a live recalculation against the current price list
> should be performed before each budget cycle.

---

## Line-by-Line Arithmetic

### Cloud Rent (flat)

| Component | Monthly Cost |
|---|---|
| 3 × `cart-api` pods | included in flat estimate |
| PostgreSQL | included in flat estimate |
| Redis | included in flat estimate |
| Load balancer | included in flat estimate |
| **Cloud rent subtotal** | **$1,500.00** |

The cloud rent is largely fixed. It does not scale with AI call volume.

---

### AI Meter (variable)

**Step 1 — Total tokens consumed per month**

```
Input tokens:   3,000,000 calls × 1,200 tokens/call = 3,600,000,000 tokens
Output tokens:  3,000,000 calls × 200   tokens/call =   600,000,000 tokens
```

**Step 2 — Input token cost**

```
3,600,000,000 ÷ 1,000,000 × $2.50 = $9,000.00
```

**Step 3 — Output token cost**

```
600,000,000 ÷ 1,000,000 × $10.00 = $6,000.00
```

**Step 4 — AI meter subtotal**

```
$9,000.00 (input) + $6,000.00 (output) = $15,000.00
```

> **Sanity check.** Input alone is 3,000,000 × 1,200 × $2.50/M = **$9,000**. Any total
> below $5,000 would indicate the call volume was dropped or mispriced. This estimate
> passes that check.

---

## Monthly Total

| Line | Amount | % of Total |
|---|---|---|
| Cloud rent | $1,500.00 | 9.1% |
| AI input tokens | $9,000.00 | 54.5% |
| AI output tokens | $6,000.00 | 36.4% |
| **Grand total** | **$16,500.00** | **100%** |

---

## Spend Attribution

| Spend Category | Monthly Cost | Behaviour | Owner |
|---|---|---|---|
| Cloud rent | $1,500.00 | Flat — does not scale with AI usage | [ops] — platform team |
| AI meter | $15,000.00 | Variable — scales linearly with "Summarize my cart" call volume | [mine/Product] — the feature team and its P&L |

**Key finding:** The AI meter is 91% of total monthly cost. The cloud infrastructure
that runs the service is 9%. An overspend event will almost certainly originate from the
AI meter, not from infrastructure sizing. Ownership of that spend sits with the product
team that introduced the feature, not the platform team.

---

## Ship Recommendation

| Criterion | Assessment |
|---|---|
| Monthly cost within budget envelope? | Depends on approved budget — verify before shipping |
| Cost split clearly attributed? | Yes — AI meter owned by [mine/Product] |
| Runaway meter risk present? | **Yes** — no cap is currently set; an uncapped loop at 3M calls/month costs $15,000 |
| Gateway cost cap configured? | **Not yet — required before shipping** |

**Recommendation: Ship with mitigation.**

The service is shippable once a hard cost cap and alert threshold are configured on the
Enterprise AI Gateway. Shipping without a cap exposes the business to unbounded AI spend
if call volume increases unexpectedly or an application loop occurs.

---

## Gateway Cost Cap

Set the following controls on the Enterprise AI Gateway before the "Summarize my cart"
feature goes to production:

| Control | Value | Rationale |
|---|---|---|
| **Hard cap (monthly AI spend)** | **$18,000** | 20% above current baseline of $15,000; allows normal traffic growth without triggering a hard block |
| **Alert threshold** | **$13,500** | 75% of the hard cap; provides actionable warning before the cap is reached, so the on-call team can investigate without being in a production outage |
| Cap enforcement action | Reject new AI requests with HTTP 429 | Prevents silent cost accumulation; the application must handle 429 gracefully |
| Alert channel | On-call engineering + product team cost owner | Both infrastructure and product team are notified; cost ownership is shared awareness |

> **Why the cap must be set above current spend.** A cap set at or below $15,000 would
> immediately block production traffic at month-end. The $18,000 cap provides a 20%
> growth buffer. If monthly spend consistently approaches the cap, the cap value and the
> feature's call volume should be reviewed together.

> **Why the alert must be below the cap.** An alert set at the cap value means the first
> notification arrives when the cap has already been reached and requests are already being
> rejected in production. The $13,500 alert fires with $4,500 of headroom remaining —
> enough time to investigate and respond before the hard limit is hit.

---

## Assumptions

- Cloud rent of $1,500/month is a flat estimate covering three application pods,
  one PostgreSQL instance, one Redis instance, and one load balancer. Actual costs
  vary by cloud provider, region, instance tier, storage I/O, and data transfer.
- AI token volumes are based on the stated 3,000,000 calls/month figure. Actual
  volume may vary with user behaviour, retry logic, and background batch processing.
- Prices used are the reference rates provided in the kata specification
  ($2.50 input / $10.00 output per 1M tokens). These should be verified against the
  current Enterprise AI Gateway billing terms or upstream LLM provider price list
  before any financial commitment is made.
- This estimate covers direct API cost only. It does not include observability,
  log storage, egress, support contracts, or team operational overhead.
- Cost cap values are illustrative starting points. Final values should be approved
  by the product and finance owners accountable for this feature's P&L.
