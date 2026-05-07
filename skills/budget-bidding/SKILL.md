---
name: budget-bidding
description: Adjust campaign budgets and bidding strategies. Use for "increase budget on campaign X", "switch to target CPA / target ROAS / max conversions / max conversion value", "set daily budget", "share a budget across campaigns", "lower bid ceiling", "limited by budget campaigns", "audit bidding strategies".
---

# Budget and bidding management

## Budget structure

Budgets are separate `campaign_budget` resources. Each campaign references one budget. A budget can be shared among campaigns (`explicitlyShared=true`).

`amountMicros` is daily budget in micros (multiply by 1,000,000). Google may spend up to 2x on a single day, balanced over 30.4 days.

`deliveryMethod`:
- `STANDARD` (default) - paced evenly throughout the day
- `ACCELERATED` (deprecated for Search; still on Display) - spend as fast as possible

### Update a budget amount

```python
import sys; sys.path.insert(0, '.')
from lib import GoogleAdsClient
c = GoogleAdsClient()
CUSTOMER_ID, BUDGET_ID = "1234567890", "55555"
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaignBudgets", BUDGET_ID),
        "amountMicros": str(c.micros(75)),  # 75 in account currency / day
    },
    "updateMask": "amount_micros",
}]
print(c.mutate_resource(CUSTOMER_ID, "campaignBudgets", ops))
```

To find the budget for a campaign:
```sql
SELECT campaign.id, campaign.name, campaign_budget.id, campaign_budget.amount_micros
FROM campaign
WHERE campaign.id = CAMPAIGN_ID
```

## Bidding strategies (inline on campaign)

Each campaign has exactly one bidding strategy. Replace it via update with the new strategy field set and `updateMask` listing exactly that one field.

| strategy | when | required fields |
|---|---|---|
| `manualCpc` | manual control, learning | empty {} or `{enhancedCpcEnabled: true}` |
| `targetSpend` | maximize clicks within budget | optional `cpcBidCeilingMicros`, `targetSpendMicros` |
| `maximizeConversions` | optimize for conversion volume | optional `targetCpaMicros` |
| `maximizeConversionValue` | optimize for revenue | optional `targetRoas` |
| `targetCpa` | hit target cost per conversion | `targetCpaMicros` |
| `targetRoas` | hit target return on ad spend | `targetRoas` (e.g. 4.0 = 400%) |
| `targetImpressionShare` | brand visibility | `location`, `targetImpressionShare`, `cpcBidCeilingMicros` |

### Switch a campaign to maximize conversions

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "maximizeConversions": {},  # no extra config
    },
    "updateMask": "maximize_conversions",
}]
```

### Switch to target ROAS

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "maximizeConversionValue": {"targetRoas": 4.0},
    },
    "updateMask": "maximize_conversion_value.target_roas,maximize_conversion_value",
}]
```

The `update_mask` MUST list every nested field touched, plus the parent oneof if you're switching strategies.

### Switch to target CPA

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "targetCpa": {"targetCpaMicros": str(c.micros(15))},  # 15 / conversion
    },
    "updateMask": "target_cpa.target_cpa_micros,target_cpa",
}]
```

### Portfolio (shared) bidding strategies

For sharing one strategy across many campaigns, create a `bidding_strategy` resource and reference it from each campaign via `campaign.biddingStrategy = "customers/.../biddingStrategies/{id}"`. Useful for keeping all campaigns under one tROAS goal.

## Audit: campaigns limited by budget

```sql
SELECT campaign.id, campaign.name, campaign.status,
       campaign_budget.amount_micros,
       metrics.cost_micros,
       metrics.search_budget_lost_impression_share,
       metrics.search_lost_impression_share_due_to_budget
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
  AND metrics.search_budget_lost_impression_share > 0.10
ORDER BY metrics.search_budget_lost_impression_share DESC
```

A `search_budget_lost_impression_share > 0.10` (10%) means the campaign would spend more if budget allowed.

## Audit: bidding strategy distribution

```sql
SELECT campaign.bidding_strategy_type, COUNT(campaign.id)
FROM campaign
WHERE campaign.status = 'ENABLED'
```

GAQL doesn't support COUNT - aggregate in Python. The lib's `fmt.summarize_metrics()` helps; for raw counts iterate rows.

## Pacing analysis (today's spend vs daily budget)

```sql
SELECT campaign.name, campaign_budget.amount_micros,
       metrics.cost_micros
FROM campaign
WHERE segments.date = 'TODAY'
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
```

Pace ratio = cost / (budget * fraction_of_day_elapsed). Below 0.7 = underpacing; above 1.3 = will hit cap.

## Common pitfalls

1. **update_mask wrong** -> changes silently ignored. Always include nested paths.
2. **Setting two strategies at once** -> `INVALID_ARGUMENT`. The strategies are mutually-exclusive oneof.
3. **Bid ceiling too low** -> "limited by bid". Symptoms: top-impression-share stuck.
4. **Smart bidding too soon** -> needs ~30 conversions in 30 days. Without that, target CPA/ROAS may not learn.
5. **Shared budget edits** -> changes affect ALL campaigns sharing that budget.

## Reference
- [reference/mutations-guide.md](../../reference/mutations-guide.md)
- [reference/reporting-patterns.md](../../reference/reporting-patterns.md) - impression-share interpretations
