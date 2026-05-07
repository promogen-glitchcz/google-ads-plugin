---
name: performance-reporting
description: Build performance reports - daily/weekly KPIs, campaign performance, trend analysis, anomaly detection, dashboards. Use for "give me a report on", "performance dashboard", "weekly summary", "trend over last 90 days", "compare this month vs last month", "anomalies in this account", "build me an HTML dashboard", "export data to spreadsheet".
---

# Performance reporting

## Output formats

| user wants | what to do |
|---|---|
| "show me numbers" | markdown table |
| "export" / "spreadsheet" / "csv" | CSV file under `output/` |
| "dashboard" | self-contained HTML with charts (`output/dashboard-{id}-{date}.html`) |
| "json" / "for code" | JSON file |

## Standard reports

### 1. Account daily trend (last 90 days)

```sql
SELECT segments.date,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM customer
WHERE segments.date DURING LAST_90_DAYS
ORDER BY segments.date
```

### 2. Campaign performance with QoQ comparison

```sql
SELECT campaign.id, campaign.name, campaign.status,
       campaign.advertising_channel_type, campaign.bidding_strategy_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value,
       metrics.search_impression_share,
       metrics.search_budget_lost_impression_share,
       metrics.search_rank_lost_impression_share
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
```

For comparison: run again with `BETWEEN 'A' AND 'B'` for prior period, diff in Python.

### 3. Weekly KPI cards (last 7 days)

Show: total cost, conversions, ROAS, CTR, CPC, vs same metric prior 7 days.

### 4. Search terms triage

```sql
SELECT search_term_view.search_term,
       campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.impressions > 10
ORDER BY metrics.cost_micros DESC
LIMIT 500
```

Bucket by Python: high-cost-zero-conv (negatives), high-conv-not-keyword (add as positive), high-impressions-low-CTR (review match types).

### 5. Geographic breakdown

```sql
SELECT geographic_view.country_criterion_id,
       segments.geo_target_city, segments.geo_target_region, segments.geo_target_country,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM geographic_view
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
LIMIT 200
```

### 6. Device + hour-of-day

```sql
SELECT segments.device, segments.hour,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
```

### 7. Conversion attribution

```sql
SELECT segments.conversion_action_name,
       segments.conversion_action,
       metrics.conversions, metrics.conversions_value,
       metrics.cost_per_conversion, metrics.value_per_conversion
FROM customer
WHERE segments.date DURING LAST_30_DAYS
```

### 8. Quality score distribution

```sql
SELECT ad_group_criterion.quality_info.quality_score, COUNT(ad_group_criterion.criterion_id)
FROM keyword_view
WHERE ad_group_criterion.status = 'ENABLED'
```
GAQL has no COUNT/GROUP BY - bucket in Python.

### 9. Auction insights (where supported)

GAQL doesn't expose auction insights yet (still UI-only as of mid-2026 - check current docs).

### 10. PMax asset performance

```sql
SELECT asset.id, asset.name, asset.text_asset.text, asset.image_asset.full_size.url,
       asset_group_asset.field_type, asset_group_asset.performance_label,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM asset_group_asset
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.impressions DESC
```

`performance_label` is BEST / GOOD / LOW / PENDING / LEARNING.

## Anomaly detection patterns

For each pattern, Claude should:
1. Run the diagnostic query
2. Identify rows that match the anomaly definition
3. Report findings with the exact campaign/keyword/etc. names

### Cost spike (week over week)
Pull last 14 days by campaign-day. Compare last-7-days cost vs prior-7-days cost. Flag campaigns where current is >150% of prior AND prior > 0.

### Conversion drop
Same as cost spike but on conversions and looking for <50% of prior.

### CPC creep
Average CPC up >25% week over week.

### Quality score regression
Compare current QS to last 30-day average; flag drops >=2 points with material impressions.

### Limited-by-budget campaigns
`metrics.search_budget_lost_impression_share > 0.10` (see budget-bidding skill).

### Disapproved ads
See ad-management skill.

### Dead keywords (no impressions in 30 days, but still ENABLED)
```sql
SELECT ad_group_criterion.keyword.text, ad_group.name, campaign.name
FROM keyword_view
WHERE ad_group_criterion.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
  AND metrics.impressions = 0
```

## HTML dashboard pattern

```bash
python3 scripts/build_dashboard.py CUSTOMER_ID --days 30 --out output/dashboard.html
```

The dashboard is a single self-contained HTML with embedded data and Chart.js (CDN). Sections:
1. KPI header (cost, conv, ROAS, CTR, CPC) with arrows vs prior period
2. Daily trend line chart (cost + conv on dual axis)
3. Top 10 campaigns by cost (bar)
4. Device split (donut)
5. Top wasteful search terms (table)
6. Top converting search terms not yet keywords (table)
7. Disapproved ads (table)
8. Limited-by-budget campaigns (table)

## Comparison periods

For "vs last week" / "vs last month":
- Last 7 days vs prior 7 days: `LAST_7_DAYS` then `BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'` (compute in Python)
- Last 30 days vs prior 30 days: same pattern
- Month-over-month: `THIS_MONTH` vs `LAST_MONTH`

Always show absolute diff and % diff. Use the previous period's value as denominator; clearly mark "(no data prior)" when prior is 0.

## Reference
- [reference/reporting-patterns.md](../../reference/reporting-patterns.md)
- [reference/gaql-cookbook.md](../../reference/gaql-cookbook.md)
