---
name: data-query
description: Run any Google Ads Query Language (GAQL) query against an account. Use whenever the user asks for data, metrics, lists, or anything that requires reading from Google Ads - "get me clicks for campaign X", "show keywords with cost", "which ads are running", "search terms report", "list all enabled campaigns", "performance by device". This is the workhorse skill for reads. For mutations, use the resource-specific management skills.
---

# Data query (GAQL)

The general-purpose READ skill. Anything the user wants to see goes through here.

## Decision tree

1. User asks for data -> figure out which resource (campaign, ad_group, keyword_view, search_term_view, etc.)
2. Figure out which fields and metrics
3. Figure out date range and filters
4. Run the query
5. Format output (markdown table by default; CSV if user asked for export; JSON for programmatic)

## How to run a query

```bash
python3 scripts/run_gaql.py CUSTOMER_ID "QUERY" [--format=table|csv|json] [--max-rows=200]
```

For multi-line queries, save to a `.sql` file and pass `@path/to/file.sql`. For piped queries, pass `-` and read from stdin.

```bash
python3 scripts/run_gaql.py 1234567890 "
SELECT campaign.id, campaign.name, metrics.cost_micros
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
LIMIT 50
"
```

## GAQL essentials

### Anatomy of a query
```sql
SELECT field1, field2, metrics.X, segments.Y
FROM resource
WHERE condition AND condition
ORDER BY metrics.X DESC
LIMIT N
```

### Date range options (in WHERE)
- `segments.date DURING LAST_7_DAYS` (also LAST_14_DAYS, LAST_30_DAYS, LAST_BUSINESS_WEEK, THIS_MONTH, LAST_MONTH, THIS_QUARTER, LAST_QUARTER, YESTERDAY, TODAY)
- `segments.date BETWEEN '2026-01-01' AND '2026-01-31'`
- `segments.date >= '2026-04-01'`

### Most-used resources (FROM)
| resource | what for |
|---|---|
| `customer` | account-level info, currency, status |
| `customer_client` | MCC sub-accounts |
| `campaign` | campaigns + their metrics |
| `campaign_budget` | budget settings |
| `ad_group` | ad groups + metrics |
| `ad_group_ad` | individual ads (RSA, image, etc.) and policy status |
| `ad_group_criterion` | targeting items: keywords, audiences, demographics |
| `keyword_view` | keyword performance with quality_info |
| `search_term_view` | actual queries that matched - find negatives, find new keywords |
| `geographic_view` | performance by location |
| `age_range_view`, `gender_view` | demographic perf |
| `click_view` | click-level data (last 90 days only) |
| `conversion_action` | conversion goals defined in account |
| `change_event` | audit log of recent changes (last 30 days) |
| `recommendation` | Google's optimization suggestions |
| `asset`, `asset_group`, `asset_group_asset` | PMax / RSA assets |
| `campaign_asset`, `ad_group_asset` | asset attachments |

For the full catalog with fields per resource: [reference/resources-catalog.md](../../reference/resources-catalog.md)

### Metrics that work on most resources
- `metrics.impressions`, `metrics.clicks`, `metrics.cost_micros`
- `metrics.conversions`, `metrics.conversions_value`, `metrics.all_conversions`
- `metrics.ctr`, `metrics.average_cpc`, `metrics.average_cpm`
- `metrics.search_impression_share`, `metrics.search_top_impression_share`
- `metrics.search_budget_lost_impression_share`, `metrics.search_rank_lost_impression_share`

### Useful segments (cause one row per combination)
- `segments.date` - daily breakdown
- `segments.device` - MOBILE, TABLET, DESKTOP, CONNECTED_TV, OTHER
- `segments.network` / `segments.ad_network_type` - SEARCH, SEARCH_PARTNERS, CONTENT, etc.
- `segments.hour` - 0..23
- `segments.day_of_week`
- `segments.conversion_action` - per-conversion-goal split
- `segments.geo_target_country`, `segments.geo_target_region`, etc.

## Recipe library (most-asked patterns)

For 30+ ready-to-use queries: [reference/gaql-cookbook.md](../../reference/gaql-cookbook.md). Below are the most common.

### Active campaigns last 30 days
```sql
SELECT campaign.id, campaign.name, campaign.status,
       campaign.advertising_channel_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
```

### Top keywords by cost
```sql
SELECT ad_group_criterion.keyword.text,
       ad_group_criterion.keyword.match_type,
       ad_group.name, campaign.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 100
```

### Search terms that converted but aren't existing keywords
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

### Performance by device
```sql
SELECT campaign.name, segments.device,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY campaign.name, segments.device
```

### Daily cost trend
```sql
SELECT segments.date, metrics.cost_micros, metrics.conversions
FROM customer
WHERE segments.date DURING LAST_30_DAYS
ORDER BY segments.date
```

## Output formatting

- Default: markdown table (good for chat)
- `--format=csv` for the user to copy into a spreadsheet
- `--format=json` for further processing in code

## Important conversions

- `metrics.cost_micros` is in **micros** - divide by 1,000,000 to get currency. The lib's `fmt.micros_to_currency()` handles this.
- Times in segments are in the customer's time zone.
- Money fields with `_micros` suffix: ALWAYS divide by 1M.

## Pagination

Most queries return everything in one stream call (`searchStream`). For very large result sets, use `client.search_paginated()` from the lib instead.

## Troubleshooting

- "Cannot select metrics.X with resource Y" -> not all metrics exist on all resources. Read [reference/resources-catalog.md](../../reference/resources-catalog.md).
- "Field is not selectable" -> the field exists but can't appear in SELECT for that resource. Look for an alternative on `*_view` resources.
- Empty result with no error -> filter is too restrictive (segments.date not set is a common cause - cost without date defaults to All Time and may simply have no rows).

## Reference

- Full GAQL cookbook: [reference/gaql-cookbook.md](../../reference/gaql-cookbook.md)
- Resource and field catalog: [reference/resources-catalog.md](../../reference/resources-catalog.md)
