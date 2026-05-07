# Reporting and Analytics Patterns

How to turn GAQL data into useful reports, KPIs, anomaly detection, and dashboards.

## KPI definitions

| KPI | Formula | API field (when direct) |
|---|---|---|
| CTR | clicks / impressions | `metrics.ctr` (already a ratio) |
| CPC | cost / clicks | `metrics.average_cpc` (in micros) |
| CPM | cost / (impressions / 1000) | `metrics.average_cpm` |
| CPA | cost / conversions | `metrics.cost_per_conversion` |
| ROAS | conv_value / cost | compute: `conversions_value / (cost_micros / 1e6)` |
| Conversion rate | conversions / clicks | `metrics.conversions_from_interactions_rate` |
| Search IS | got / eligible | `metrics.search_impression_share` (0-1) |

Always divide `cost_micros` by 1,000,000 for display. Currency from `customer.currency_code`.

## Impression share - what each one means

| metric | meaning |
|---|---|
| `search_impression_share` | got / eligible. Lower = missed opportunities. |
| `search_top_impression_share` | of eligible-for-top, share won |
| `search_absolute_top_impression_share` | of eligible-for-position-1, share won |
| `search_budget_lost_impression_share` | lost because daily budget capped you |
| `search_rank_lost_impression_share` | lost because your bid * QS too low |
| `search_exact_match_impression_share` | among queries that match exactly, share won |

Diagnosis rule of thumb:
- High `search_budget_lost_*` (>10%) -> raise budget
- High `search_rank_lost_*` (>20%) -> raise bids or improve QS
- Both low + IS still <90% -> targeting too narrow

## Quality score components

On `ad_group_criterion`:
- `quality_info.quality_score` (1-10)
- `quality_info.creative_quality_score` - "ad relevance"
- `quality_info.post_click_quality_score` - "landing page experience"
- `quality_info.search_predicted_ctr` - "expected CTR"

Each component returns `BELOW_AVERAGE`, `AVERAGE`, `ABOVE_AVERAGE`, or `UNKNOWN`.

For historical QS over time: `keyword_view` with `metrics.historical_quality_score`, `metrics.historical_creative_quality_score`, `metrics.historical_landing_page_quality_score`, `metrics.historical_search_predicted_ctr` segmented by `segments.date`.

## Comparison periods

### Last 7 days vs prior 7 days
1. Run query A: `WHERE segments.date DURING LAST_7_DAYS`
2. Compute the prior 7-day window: today - 14 days to today - 8 days
3. Run query B: `WHERE segments.date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`
4. Diff in code: `delta = current - prior`, `pct = delta / prior * 100` (mark prior=0 explicitly)

### Last 30 days vs prior 30 days
Same pattern, 30-day windows.

### Month-over-month
A = `THIS_MONTH`, B = `LAST_MONTH`. Note: THIS_MONTH includes only completed days; for fair comparison, restrict B to same number of days.

### YTD
`segments.date BETWEEN 'YYYY-01-01' AND 'YYYY-MM-DD'`

## Anomaly detection patterns

For each, run two windows (current and prior) and diff in code.

### Cost spike (campaign WoW)
Pull campaign perf for current 7 days and prior 7 days. Flag campaigns where `cost_now > cost_prior * 1.30 AND cost_now > $threshold` (set threshold to avoid noise on small campaigns).

### Conversion drop
Flag where `conv_now < conv_prior * 0.7 AND clicks_now >= clicks_prior * 0.9` - clicks held but conversions fell, often a tracking break or LP issue.

### CPC creep
Flag where `cpc_now / cpc_prior > 1.25`. Cross-reference with rising `search_rank_lost_impression_share` -> usually competitor entered.

### QS regression
Daily QS snapshots; flag any keyword whose QS dropped >=2 points week-over-week and has material impressions.

### High-cost no-conv keywords
```sql
SELECT campaign.name, ad_group.name, ad_group_criterion.keyword.text,
       metrics.cost_micros, metrics.clicks, metrics.conversions
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.conversions = 0
  AND metrics.cost_micros > 50000000  -- 50 currency units
ORDER BY metrics.cost_micros DESC
```

### Disapproved ads (Section 1.7 of resources catalog)

### Limited by budget (>10% lost IS to budget) - see gaql-cookbook.md

### Dead but enabled keywords
```sql
SELECT ad_group_criterion.keyword.text, ad_group.name, campaign.name
FROM keyword_view
WHERE ad_group_criterion.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
  AND metrics.impressions = 0
```

## Audit checklist (full review)

- Conversion tracking present? Check `customer.conversion_tracking_setting.conversion_tracking_id`.
- Primary-for-goal conversion actions exist? Filter `conversion_action WHERE primary_for_goal = TRUE`.
- All Search campaigns have `target_content_network = FALSE`?
- All campaigns have at least one negative keyword?
- Are sitelinks attached to enabled Search campaigns? (cross-ref `campaign_asset` with field_type=SITELINK)
- Auto-tagging on? Check `customer.auto_tagging_enabled`.
- Bidding strategies aligned with goals? (count by `bidding_strategy_type`)
- Any QS<5 keywords with material spend?
- Any disapproved ads in active groups?
- Any single-keyword ad groups (legacy SKAG)?
- Any orphan ad groups (no enabled ads)?

## Dashboard layout

Suggested widgets for an HTML dashboard:

1. **KPI strip** - Cost, Conv, CPA, ROAS, CTR, IS - all with WoW arrows
2. **Daily trend** - line: cost (left axis) + conversions (right axis) over 30 days
3. **Top 10 campaigns by cost** - bar chart
4. **Bottom 10 campaigns by ROAS** - bar chart
5. **Device split** - donut
6. **Hour-of-day heatmap** - 7x24 grid
7. **Quality score histogram** - bucket 1-10
8. **Top 20 wasted-spend search terms** - table
9. **Lost IS to budget vs rank** - stacked bar per campaign
10. **Recent changes feed** - last 7 days of change_event
11. **Open recommendations with potential lift** - table from recommendation resource
12. **Disapproved ads alert** - if any

## Output format guidance

- "Show me numbers" -> markdown table inline
- "Export" / "Spreadsheet" / "CSV" -> CSV file in `output/`
- "Dashboard" -> self-contained HTML (Chart.js via CDN) saved to `output/`
- "JSON" / "for code" -> JSON file in `output/`

## Cost / conversions math for reporting

Always compute on raw values:
```python
total_cost = sum(int(r['metrics.cost_micros']) for r in rows) / 1_000_000
total_conv = sum(float(r['metrics.conversions']) for r in rows)
total_value = sum(float(r['metrics.conversions_value'] or 0) for r in rows)
cpa = total_cost / total_conv if total_conv else None
roas = total_value / total_cost if total_cost else None
```

Don't average ratios; recompute from sums.

## Notes on metric availability

Not every metric exists on every resource. When you see "Cannot select metrics.X with resource Y", the metric isn't denormalized to that resource. Common alternatives:
- For impression share metrics, query at `campaign` level (not ad_group)
- For per-keyword historical QS, use `keyword_view` with `metrics.historical_quality_score`
- For PMax per-asset metrics: use `performance_label` (PMax does NOT expose per-asset cost/clicks/conversions; use asset_group_asset's performance_label which is BEST/GOOD/LOW/LEARNING/PENDING)
