---
name: audit-and-recommendations
description: Run a structured account audit (waste, missed opportunities, policy issues, structural problems) and surface Google's own recommendations from the Recommendations API. Use for "audit my account", "what should I fix", "find low-hanging fruit", "what does Google recommend", "apply recommendation X", "dismiss recommendation Y", "give me a health check".
---

# Audit and Recommendations

## Two layers

1. **Structural / waste audit** - things Claude can find by querying the account.
2. **Google's recommendations** - the `recommendation` resource exposes Google's own optimization ideas.

## Run a full audit

```bash
python3 scripts/audit_account.py CUSTOMER_ID --days 30
```

This currently checks:
- Campaigns limited by budget (search_budget_lost_impression_share > 10%)
- Disapproved or limited-approval ads
- Search terms wasting spend (cost > 0, zero conversions)
- Low quality score keywords (QS < 5) with traffic
- Conversion actions enabled (presence check)

For deeper checks, run the queries below.

## Audit checklist (each is a separate GAQL query)

### Conversion tracking missing
```sql
SELECT customer.id, customer.descriptive_name,
       customer.conversion_tracking_setting.conversion_tracking_id,
       customer.conversion_tracking_setting.cross_account_conversion_tracking_id
FROM customer
```
If both IDs are empty, conversions are not tracked at all.

### Conversion actions list
```sql
SELECT conversion_action.id, conversion_action.name, conversion_action.status,
       conversion_action.category, conversion_action.type,
       conversion_action.primary_for_goal, conversion_action.counting_type,
       conversion_action.click_through_lookback_window_days,
       conversion_action.value_settings.default_value
FROM conversion_action
WHERE conversion_action.status = 'ENABLED'
```
Flag: no `primary_for_goal=true` actions; weird counting types; missing values.

### Campaigns with zero ad groups (broken structure)
```sql
SELECT campaign.id, campaign.name FROM campaign WHERE campaign.status = 'ENABLED'
```
Then for each, query ad_group with `WHERE campaign = '...'`. Empty -> orphan.

### Ad groups with no enabled ads
```sql
SELECT ad_group.id, ad_group.name, campaign.name
FROM ad_group
WHERE ad_group.status = 'ENABLED'
```
For each, query `ad_group_ad WHERE ad_group_ad.status = 'ENABLED'`. Empty -> won't serve.

### Single-keyword ad groups (legacy SKAG)
```sql
SELECT ad_group.id, ad_group.name, COUNT(ad_group_criterion.criterion_id)
FROM keyword_view WHERE ad_group_criterion.status = 'ENABLED'
```
GAQL has no GROUP BY - aggregate in Python by ad_group.id.

### Ads without sitelinks
```sql
SELECT campaign.id, campaign.name FROM campaign_asset WHERE campaign_asset.field_type = 'SITELINK'
```
Cross-reference with all enabled campaigns; ones not in this list have no sitelinks.

### Search campaigns with display network targeting on
```sql
SELECT campaign.id, campaign.name,
       campaign.network_settings.target_content_network,
       campaign.network_settings.target_partner_search_network
FROM campaign
WHERE campaign.advertising_channel_type = 'SEARCH'
  AND campaign.status = 'ENABLED'
  AND campaign.network_settings.target_content_network = TRUE
```
Most accounts should have content_network=false on Search.

### Broad match without smart bidding
```sql
SELECT ad_group_criterion.keyword.text, ad_group.name, campaign.name,
       campaign.bidding_strategy_type
FROM keyword_view
WHERE ad_group_criterion.keyword.match_type = 'BROAD'
  AND ad_group_criterion.status = 'ENABLED'
  AND campaign.status = 'ENABLED'
```
Cross-check `bidding_strategy_type` - broad is risky on manual_cpc.

## Recommendations API

Google scores and surfaces optimization ideas via `recommendation` resource.

### List all current recommendations

```sql
SELECT recommendation.resource_name, recommendation.type,
       recommendation.impact.base_metrics.cost_micros,
       recommendation.impact.potential_metrics.cost_micros,
       recommendation.impact.base_metrics.conversions,
       recommendation.impact.potential_metrics.conversions,
       recommendation.campaign,
       recommendation.dismissed
FROM recommendation
WHERE recommendation.dismissed = FALSE
```

Common types: `KEYWORD`, `RESPONSIVE_SEARCH_AD`, `RESPONSIVE_SEARCH_AD_ASSET`, `USE_BROAD_MATCH_KEYWORD`, `MAXIMIZE_CONVERSIONS_OPT_IN`, `MAXIMIZE_CONVERSION_VALUE_OPT_IN`, `TARGET_CPA_OPT_IN`, `TARGET_ROAS_OPT_IN`, `ENHANCED_CPC_OPT_IN`, `MOVE_UNUSED_BUDGET`, `IMPROVE_GOOGLE_TAG_COVERAGE`, `OPTIMIZE_AD_ROTATION`, `FORECASTING_*`, `KEYWORD_MATCH_TYPE` (broad change), `CAMPAIGN_BUDGET`, `MIGRATE_DYNAMIC_SEARCH_ADS_CAMPAIGN_TO_PERFORMANCE_MAX`.

### Apply a recommendation

```python
ops = [{
    "resourceName": "customers/.../recommendations/...",
    # the apply_parameters depend on type, see docs - many recs apply with no parameters:
}]
url = f"{c.base}/customers/{CUSTOMER_ID}/recommendations:apply"
body = {"operations": ops}
c._request("POST", url, body)
```

For recommendations that need parameters (e.g. `CAMPAIGN_BUDGET` to set a specific amount, or `KEYWORD` to choose which keyword to add), include the corresponding `*_recommendation` field in each op:

```python
ops = [{
    "resourceName": "customers/.../recommendations/X",
    "campaignBudgetRecommendation": {
        "budgetMicros": str(c.micros(60)),
    },
}]
```

### Dismiss a recommendation

```python
url = f"{c.base}/customers/{CUSTOMER_ID}/recommendations:dismiss"
body = {"operations": [{"resourceName": "customers/.../recommendations/X"}]}
c._request("POST", url, body)
```

### Bulk-apply many recommendations

`recommendations:apply` accepts up to 100 operations per call. Always confirm with the user before applying anything that changes spending or messaging - some recommendations (e.g. broad match opt-in) materially change campaign behavior.

## Audit output format

Default to a markdown report saved to `output/audit-{customer_id}-{date}.md` with sections:
1. Executive summary (counts of issues by severity)
2. Wasted spend (search terms, low QS)
3. Missed opportunities (search terms not yet keywords, missing extensions)
4. Policy / approval issues
5. Structural issues (orphan ad groups, broken targeting)
6. Google recommendations awaiting decision

For each issue, include: a one-line description, the affected entities, the GAQL query that surfaced it (so the user can re-run), and a suggested action.

## Reference
- [reference/reporting-patterns.md](../../reference/reporting-patterns.md)
- Google's docs on Recommendations: https://developers.google.com/google-ads/api/docs/recommendations/overview
