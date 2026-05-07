---
name: bulk-operations
description: Apply mass changes via CSV files or programmatic batches - bulk add keywords, bulk pause campaigns/ad groups, bulk negative keywords, import a structure from a spreadsheet, export data, mass status changes. Use for "add 200 keywords from this file", "pause all campaigns matching X", "import this structure", "bulk export everything".
---

# Bulk operations

## When to use this skill

- Mass adds or edits where one-by-one would be slow / error-prone
- CSV-driven workflows (user has data in a spreadsheet)
- Cleanups: pause everything matching a pattern; remove orphaned items

## Two ways to batch

### A. Single-resource batch (one mutate_resource call)

Up to 5,000 operations per call on one resource type. Use for "add 200 keywords to one ad group".

```python
import sys; sys.path.insert(0, '.')
from lib import GoogleAdsClient
c = GoogleAdsClient()

ops = [
    {"create": {
        "adGroup": c.resource_name(CUSTOMER_ID, "adGroups", AD_GROUP_ID),
        "status": "ENABLED",
        "keyword": {"text": kw, "matchType": "EXACT"},
    }}
    for kw in keywords_list
]

# always validate first
print(c.mutate_resource(CUSTOMER_ID, "adGroupCriteria", ops, validate_only=True, partial_failure=True))
# then for real
print(c.mutate_resource(CUSTOMER_ID, "adGroupCriteria", ops, partial_failure=True))
```

`partial_failure=True` lets the rest succeed if a few fail. The response will list the failed indexes with reasons.

### B. Cross-resource batch (one mutate_batch call)

For end-to-end structures: budget + campaign + ad groups + keywords + ads in one shot.

Up to 10,000 operations across resources. Use temporary IDs (negative numbers) to reference objects created earlier in the same batch.

```python
mutate_ops = [
    {"campaignBudgetOperation": {"create": {
        "resourceName": f"customers/{CUSTOMER_ID}/campaignBudgets/-1",
        "name": "Budget", "amountMicros": str(c.micros(50)), "deliveryMethod": "STANDARD",
    }}},
    {"campaignOperation": {"create": {
        "resourceName": f"customers/{CUSTOMER_ID}/campaigns/-2",
        "name": "Search Test", "advertisingChannelType": "SEARCH",
        "status": "PAUSED", "manualCpc": {},
        "campaignBudget": f"customers/{CUSTOMER_ID}/campaignBudgets/-1",
    }}},
    {"adGroupOperation": {"create": {
        "resourceName": f"customers/{CUSTOMER_ID}/adGroups/-3",
        "name": "Ad Group 1",
        "campaign": f"customers/{CUSTOMER_ID}/campaigns/-2",
        "status": "ENABLED", "type": "SEARCH_STANDARD",
        "cpcBidMicros": str(c.micros(0.50)),
    }}},
    # add keywords + RSA referencing -3
]

c.mutate_batch(CUSTOMER_ID, mutate_ops, validate_only=True)
```

## CSV import patterns

### Bulk add keywords from CSV

Expected CSV columns: `customer_id, ad_group_id, keyword, match_type[, status]`

```bash
python3 scripts/bulk_keywords_from_csv.py keywords.csv --validate-only
python3 scripts/bulk_keywords_from_csv.py keywords.csv  # for real
```

The script:
1. Reads CSV
2. Groups by (customer_id, ad_group_id)
3. Sends one batch per ad group
4. Reports successes and failures

### Bulk negatives from CSV

Columns: `customer_id, level, parent_id, keyword, match_type`
- level = `AD_GROUP` or `CAMPAIGN`
- parent_id = ad_group_id or campaign_id

### Bulk pause matching campaigns

```bash
python3 scripts/bulk_status.py CUSTOMER_ID \
  --filter "campaign.name LIKE '%2025%'" \
  --status PAUSED \
  --validate-only
```

Internally this:
1. Runs a GAQL search to list matching campaigns
2. Builds an update operation per campaign with the new status
3. Submits as one mutate_resource call

## Export patterns

```bash
python3 scripts/run_gaql.py CUSTOMER_ID @queries/keywords-30d.sql --format=csv > out.csv
```

The lib's `fmt.to_csv()` and `fmt.flatten()` handle the conversion.

## Safety rules for bulk

1. **ALWAYS validate_only=True first**. Only proceed for real after dry run is clean.
2. **partial_failure=True for create-many**, so one bad row doesn't block the rest.
3. **For destructive bulk (remove, pause everything matching X)** - confirm with the user the exact GAQL filter before executing. Show a count of impacted rows first.
4. **No "fix everything"**. Do one logical change at a time. Don't combine "pause low-performing" with "add new keywords" in one batch - separate jobs.
5. **Snapshot before** - for risky removes, dump the current state to JSON in `output/` so you can rebuild.

## Common bulk errors

- `OPERATION_TOO_LARGE` - batch >10K ops; split.
- `RESOURCE_TEMPORARY_RESOURCE_NAME` errors - the temp negative ID syntax wrong; must be `customers/CID/RES/-N`, not just `-N`.
- `INVALID_OPERATION_OBJECT_NOT_SET` - missing the operation kind (create/update/remove).
- `MUTATE_OPERATIONS_ALL_FAILED` with partial_failure - check `partialFailureError` in response.

## Reference
- [reference/mutations-guide.md](../../reference/mutations-guide.md)
- [reference/errors-handbook.md](../../reference/errors-handbook.md#bulk-and-mutation-errors)
