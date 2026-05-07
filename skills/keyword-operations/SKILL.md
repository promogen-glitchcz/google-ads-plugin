---
name: keyword-operations
description: Add, update, remove keywords (positive and negative) in Google Ads. Manage match types. Add negatives at ad group, campaign, or shared list level. Mine search terms for new keyword opportunities. Use for "add keywords to ad group X", "add negative keywords", "negatives for irrelevant searches", "find new keywords from search terms", "change match type", "pause underperforming keywords", "remove keywords with low quality score".
---

# Keyword operations

## Match types
- `EXACT` - `[keyword]`
- `PHRASE` - `"keyword"`
- `BROAD` - keyword (no symbols)
- For negatives, all three apply too. Negative exact is most common.

## Add positive keywords to an ad group

```python
import sys; sys.path.insert(0, '.')
from lib import GoogleAdsClient
c = GoogleAdsClient()
CUSTOMER_ID, AD_GROUP_ID = "1234567890", "111222333"
keywords = [
    ("running shoes", "EXACT"),
    ("running shoes for women", "PHRASE"),
    ("buy running shoes online", "BROAD"),
]
ops = [
    {
        "create": {
            "adGroup": c.resource_name(CUSTOMER_ID, "adGroups", AD_GROUP_ID),
            "status": "ENABLED",
            "keyword": {"text": text, "matchType": match_type},
        }
    }
    for text, match_type in keywords
]
print(c.mutate_resource(CUSTOMER_ID, "adGroupCriteria", ops, validate_only=True))
```

Switch to `validate_only=False` after the dry run looks clean.

## Add negative keywords to an ad group

Same shape, but with `negative: true`:

```python
ops = [{
    "create": {
        "adGroup": c.resource_name(CUSTOMER_ID, "adGroups", AD_GROUP_ID),
        "status": "ENABLED",
        "negative": True,
        "keyword": {"text": "free", "matchType": "BROAD"},
    }
}]
c.mutate_resource(CUSTOMER_ID, "adGroupCriteria", ops)
```

## Add negative keywords at campaign level

```python
ops = [{
    "create": {
        "campaign": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "negative": True,
        "keyword": {"text": "free", "matchType": "BROAD"},
    }
}]
c.mutate_resource(CUSTOMER_ID, "campaignCriteria", ops)
```

## Shared negative keyword lists

For org-wide negatives, create a `shared_set` of type `NEGATIVE_KEYWORDS`, add `shared_criterion` items, and link to campaigns via `campaign_shared_set`. See [reference/mutations-guide.md](../../reference/mutations-guide.md).

## Pause / re-enable / remove a keyword

```python
# pause
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "adGroupCriteria", f"{AD_GROUP_ID}~{CRITERION_ID}"),
        "status": "PAUSED",
    },
    "updateMask": "status",
}]

# remove
ops = [{"remove": c.resource_name(CUSTOMER_ID, "adGroupCriteria", f"{AD_GROUP_ID}~{CRITERION_ID}")}]
```

Note: ad-group criterion resource names use `{ad_group_id}~{criterion_id}`.

## Find new keywords from search terms

The killer query - search terms that converted but aren't keywords yet:

```sql
SELECT search_term_view.search_term, search_term_view.status,
       campaign.name, ad_group.name,
       metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.conversions > 0
  AND search_term_view.status != 'ADDED'
ORDER BY metrics.conversions DESC
LIMIT 200
```

For each row, suggest adding as a positive keyword (usually EXACT in the same ad group).

## Find waste = candidates for negatives

```sql
SELECT search_term_view.search_term, campaign.name, ad_group.name,
       metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.conversions = 0
  AND metrics.cost_micros > 5000000  -- spent more than 5 currency units
ORDER BY metrics.cost_micros DESC
LIMIT 100
```

Review with the user before adding as negatives - some queries are valid and just slow to convert.

## Bulk add from a CSV

Use [bulk-operations skill](../bulk-operations/SKILL.md) for CSV-based mass adds.

## Adjust ad group default CPC bid

This is on the ad_group, not on each keyword:

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "adGroups", AD_GROUP_ID),
        "cpcBidMicros": str(c.micros(0.50)),
    },
    "updateMask": "cpc_bid_micros",
}]
c.mutate_resource(CUSTOMER_ID, "adGroups", ops)
```

## Per-keyword bid override

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "adGroupCriteria", f"{AD_GROUP_ID}~{CRITERION_ID}"),
        "cpcBidMicros": str(c.micros(0.75)),
    },
    "updateMask": "cpc_bid_micros",
}]
```

Per-keyword bids only apply when the campaign uses Manual CPC. With Smart Bidding, keyword bids are ignored.

## Reference
- [reference/mutations-guide.md](../../reference/mutations-guide.md)
- [reference/gaql-cookbook.md](../../reference/gaql-cookbook.md)
