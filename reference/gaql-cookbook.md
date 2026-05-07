# GAQL Cookbook

Copy-pasteable queries for the most-asked Google Ads tasks. All against `googleAds:searchStream`.

## Account-level

### Account info
```sql
SELECT customer.id, customer.descriptive_name, customer.currency_code,
       customer.time_zone, customer.status, customer.test_account, customer.manager,
       customer.auto_tagging_enabled, customer.optimization_score,
       customer.conversion_tracking_setting.conversion_tracking_id,
       customer.conversion_tracking_setting.cross_account_conversion_tracking_id
FROM customer
LIMIT 1
```

### MCC sub-accounts (run with login-customer-id = manager)
```sql
SELECT customer_client.id, customer_client.descriptive_name,
       customer_client.client_customer, customer_client.level,
       customer_client.manager, customer_client.test_account,
       customer_client.currency_code, customer_client.time_zone,
       customer_client.status
FROM customer_client
WHERE customer_client.status != 'CLOSED'
ORDER BY customer_client.level, customer_client.descriptive_name
```

### Account daily trend (last 90 days)
```sql
SELECT segments.date,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM customer
WHERE segments.date DURING LAST_90_DAYS
ORDER BY segments.date
```

## Campaigns

### All active campaigns + last 30d performance
```sql
SELECT campaign.id, campaign.name, campaign.status,
       campaign.advertising_channel_type, campaign.bidding_strategy_type,
       campaign_budget.amount_micros,
       metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc,
       metrics.cost_micros, metrics.conversions, metrics.conversions_value,
       metrics.cost_per_conversion,
       metrics.search_impression_share,
       metrics.search_budget_lost_impression_share,
       metrics.search_rank_lost_impression_share
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
```

### Campaigns with no spend in 30 days
```sql
SELECT campaign.id, campaign.name, campaign.status,
       metrics.cost_micros, metrics.impressions
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
HAVING metrics.cost_micros = 0
```
(Note: GAQL doesn't actually support HAVING. Filter `metrics.cost_micros = 0` in WHERE or post-filter in code.)

### Campaign daily trend
```sql
SELECT campaign.name, segments.date,
       metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY campaign.name, segments.date
```

## Ad groups

### Ad group performance
```sql
SELECT campaign.name, ad_group.id, ad_group.name, ad_group.status, ad_group.type,
       metrics.impressions, metrics.clicks, metrics.ctr, metrics.cost_micros,
       metrics.conversions, metrics.average_cpc
FROM ad_group
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
```

### Ad groups with no enabled ads (broken structure)
First list ad groups, then per ad group check ads. The fast way:
```sql
SELECT ad_group.id, ad_group.name, campaign.name,
       ad_group_ad.ad.id, ad_group_ad.status
FROM ad_group_ad
WHERE ad_group.status = 'ENABLED'
  AND campaign.status = 'ENABLED'
ORDER BY ad_group.id
```
Group rows by ad_group.id in code, flag groups where no ad has status ENABLED.

## Keywords

### Top keywords by cost
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
       ad_group_criterion.status,
       ad_group_criterion.quality_info.quality_score,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions,
       metrics.cost_per_conversion
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status != 'REMOVED'
  AND campaign.status = 'ENABLED'
  AND ad_group_criterion.negative = FALSE
ORDER BY metrics.cost_micros DESC
LIMIT 100
```

### Quality score distribution
```sql
SELECT ad_group_criterion.quality_info.quality_score,
       ad_group_criterion.quality_info.creative_quality_score,
       ad_group_criterion.quality_info.post_click_quality_score,
       ad_group_criterion.quality_info.search_predicted_ctr,
       ad_group_criterion.keyword.text,
       campaign.name, ad_group.name,
       metrics.impressions, metrics.cost_micros
FROM keyword_view
WHERE ad_group_criterion.status = 'ENABLED'
  AND ad_group_criterion.quality_info.quality_score IS NOT NULL
  AND segments.date DURING LAST_30_DAYS
ORDER BY ad_group_criterion.quality_info.quality_score ASC
```

### Below first-page bid
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.keyword.text,
       ad_group_criterion.effective_cpc_bid_micros,
       ad_group_criterion.position_estimates.first_page_cpc_micros,
       ad_group_criterion.position_estimates.top_of_page_cpc_micros
FROM keyword_view
WHERE ad_group_criterion.status = 'ENABLED'
  AND ad_group_criterion.position_estimates.first_page_cpc_micros > ad_group_criterion.effective_cpc_bid_micros
```

### Negative keywords (ad group level)
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type
FROM ad_group_criterion
WHERE ad_group_criterion.negative = TRUE
  AND ad_group_criterion.type = 'KEYWORD'
ORDER BY campaign.name, ad_group.name
```

### Negative keywords (campaign level)
```sql
SELECT campaign.name,
       campaign_criterion.keyword.text, campaign_criterion.keyword.match_type
FROM campaign_criterion
WHERE campaign_criterion.negative = TRUE
  AND campaign_criterion.type = 'KEYWORD'
```

## Search terms

### Top search terms
```sql
SELECT campaign.name, ad_group.name,
       search_term_view.search_term, search_term_view.status,
       segments.keyword.info.text, segments.keyword.info.match_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
LIMIT 1000
```

### Search terms with NO matched keyword (they fall through wide match)
```sql
SELECT search_term_view.search_term, search_term_view.status,
       campaign.name, ad_group.name,
       metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND search_term_view.status = 'NONE'
  AND metrics.clicks > 0
ORDER BY metrics.cost_micros DESC
```

### Negative keyword candidates (high cost, no conversions)
```sql
SELECT search_term_view.search_term, campaign.name, ad_group.name,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.clicks >= 10
  AND metrics.conversions = 0
  AND metrics.cost_micros > 5000000
ORDER BY metrics.cost_micros DESC
LIMIT 200
```

### Search terms that converted but aren't keywords yet
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

## Ads

### All RSAs with policy status
```sql
SELECT campaign.name, ad_group.name,
       ad_group_ad.ad.id, ad_group_ad.status,
       ad_group_ad.ad_strength,
       ad_group_ad.ad.responsive_search_ad.headlines,
       ad_group_ad.ad.responsive_search_ad.descriptions,
       ad_group_ad.ad.responsive_search_ad.path1,
       ad_group_ad.ad.responsive_search_ad.path2,
       ad_group_ad.ad.final_urls,
       ad_group_ad.policy_summary.approval_status,
       ad_group_ad.policy_summary.review_status
FROM ad_group_ad
WHERE ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
  AND ad_group_ad.status != 'REMOVED'
ORDER BY campaign.name, ad_group.name
```

### Disapproved ads
```sql
SELECT campaign.name, ad_group.name,
       ad_group_ad.ad.id, ad_group_ad.ad.type,
       ad_group_ad.policy_summary.approval_status,
       ad_group_ad.policy_summary.review_status,
       ad_group_ad.policy_summary.policy_topic_entries
FROM ad_group_ad
WHERE ad_group_ad.policy_summary.approval_status IN ('DISAPPROVED', 'AREA_OF_INTEREST_ONLY')
  AND ad_group_ad.status != 'REMOVED'
```

### Underperforming ads (low CTR, decent volume)
```sql
SELECT campaign.name, ad_group.name,
       ad_group_ad.ad.id, ad_group_ad.ad.type, ad_group_ad.ad_strength,
       metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.conversions, metrics.cost_micros
FROM ad_group_ad
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_ad.status = 'ENABLED'
  AND metrics.impressions > 1000
  AND metrics.ctr < 0.02
ORDER BY metrics.impressions DESC
```

### RSA headline / description performance
```sql
SELECT ad_group_ad.ad.id, asset.text_asset.text,
       ad_group_ad_asset_view.field_type,
       ad_group_ad_asset_view.performance_label,
       ad_group_ad_asset_view.pinned_field,
       metrics.impressions, metrics.clicks, metrics.cost_micros
FROM ad_group_ad_asset_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
```

## Performance Max

### PMax campaign perf
```sql
SELECT campaign.id, campaign.name, campaign.status,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value,
       metrics.all_conversions, metrics.all_conversions_value
FROM campaign
WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
  AND segments.date DURING LAST_30_DAYS
```

### PMax asset performance (by performance_label since per-asset metrics aren't exposed)
```sql
SELECT campaign.name, asset_group.name,
       asset_group_asset.field_type, asset_group_asset.performance_label,
       asset.type, asset.text_asset.text,
       asset.image_asset.full_size.url,
       asset.youtube_video_asset.youtube_video_id,
       asset.call_to_action_asset.call_to_action
FROM asset_group_asset
WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
  AND asset_group_asset.status != 'REMOVED'
```

### PMax asset group health
```sql
SELECT campaign.name, asset_group.id, asset_group.name,
       asset_group.status, asset_group.primary_status, asset_group.ad_strength,
       asset_group.final_urls,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM asset_group
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.advertising_channel_type = 'PERFORMANCE_MAX'
ORDER BY metrics.cost_micros DESC
```

### PMax shopping listing groups
```sql
SELECT
  asset_group_listing_group_filter.case_value.product_item_id.value,
  asset_group_listing_group_filter.case_value.product_brand.value,
  asset_group_listing_group_filter.case_value.product_category.category_id,
  metrics.impressions, metrics.clicks, metrics.cost_micros,
  metrics.conversions, metrics.conversions_value
FROM asset_group_listing_group_filter
WHERE segments.date DURING LAST_30_DAYS
```

## Geographic and demographic

### Country / region performance
```sql
SELECT campaign.name,
       segments.geo_target_country, segments.geo_target_region,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM geographic_view
WHERE segments.date DURING LAST_30_DAYS
  AND geographic_view.location_type = 'LOCATION_OF_PRESENCE'
ORDER BY metrics.cost_micros DESC
LIMIT 500
```

### Age range performance
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.age_range.type,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM age_range_view
WHERE segments.date DURING LAST_30_DAYS
```

### Gender performance
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.gender.type,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM gender_view
WHERE segments.date DURING LAST_30_DAYS
```

## Device, hour, day-of-week

### Device split per campaign
```sql
SELECT campaign.name, segments.device,
       metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.cost_micros, metrics.conversions, metrics.cost_per_conversion
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
```

### Hour-of-day x day-of-week heatmap
```sql
SELECT segments.day_of_week, segments.hour,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
```

### Network breakdown
```sql
SELECT campaign.name, segments.ad_network_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
```

## Conversions

### Conversions by action
```sql
SELECT segments.conversion_action_name,
       segments.conversion_action_category,
       metrics.conversions, metrics.conversions_value,
       metrics.all_conversions, metrics.all_conversions_value,
       metrics.cost_per_conversion, metrics.value_per_conversion
FROM customer
WHERE segments.date DURING LAST_30_DAYS
```

### Conversion action setup audit
```sql
SELECT conversion_action.id, conversion_action.name, conversion_action.status,
       conversion_action.type, conversion_action.category,
       conversion_action.primary_for_goal, conversion_action.counting_type,
       conversion_action.attribution_model_settings.attribution_model,
       conversion_action.click_through_lookback_window_days,
       conversion_action.view_through_lookback_window_days,
       conversion_action.value_settings.default_value,
       conversion_action.value_settings.always_use_default_value
FROM conversion_action
WHERE conversion_action.status != 'REMOVED'
```

## Audiences

### Audience performance
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.criterion_id, ad_group_criterion.type,
       ad_group_criterion.user_list.user_list,
       ad_group_criterion.user_interest.user_interest_category,
       ad_group_criterion.custom_audience.custom_audience,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM ad_group_audience_view
WHERE segments.date DURING LAST_30_DAYS
```

## Budgets and bidding

### Limited by budget
```sql
SELECT campaign.id, campaign.name, campaign.status,
       campaign_budget.amount_micros,
       metrics.cost_micros,
       metrics.search_budget_lost_impression_share,
       metrics.search_budget_lost_top_impression_share,
       metrics.search_budget_lost_absolute_top_impression_share
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
  AND campaign.status = 'ENABLED'
  AND metrics.search_budget_lost_impression_share > 0.10
ORDER BY metrics.search_budget_lost_impression_share DESC
```

### Bidding strategy distribution
```sql
SELECT campaign.bidding_strategy_type, campaign.id
FROM campaign
WHERE campaign.status = 'ENABLED'
```
GAQL has no COUNT/GROUP BY - aggregate by bidding_strategy_type in code.

### Campaigns spending today
```sql
SELECT campaign.name, campaign.status,
       campaign_budget.amount_micros, metrics.cost_micros,
       metrics.impressions, metrics.clicks
FROM campaign
WHERE segments.date = TODAY
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
```

## Recommendations

### Open recommendations sorted by potential impact
```sql
SELECT recommendation.resource_name, recommendation.type,
       recommendation.impact.base_metrics.cost_micros,
       recommendation.impact.potential_metrics.cost_micros,
       recommendation.impact.base_metrics.conversions,
       recommendation.impact.potential_metrics.conversions,
       recommendation.campaign, recommendation.ad_group,
       recommendation.dismissed
FROM recommendation
WHERE recommendation.dismissed = FALSE
```

### Specific recommendation type detail
For e.g. CAMPAIGN_BUDGET:
```sql
SELECT recommendation.resource_name, recommendation.type, recommendation.campaign,
       recommendation.campaign_budget_recommendation.current_budget_amount_micros,
       recommendation.campaign_budget_recommendation.recommended_budget_amount_micros
FROM recommendation
WHERE recommendation.type = 'CAMPAIGN_BUDGET'
  AND recommendation.dismissed = FALSE
```

For KEYWORD:
```sql
SELECT recommendation.resource_name, recommendation.type,
       recommendation.keyword_recommendation.keyword.text,
       recommendation.keyword_recommendation.keyword.match_type,
       recommendation.keyword_recommendation.recommended_cpc_bid_micros
FROM recommendation
WHERE recommendation.type = 'KEYWORD'
  AND recommendation.dismissed = FALSE
```

## Change events

### Recent changes (last 7 days)
```sql
SELECT change_event.change_date_time, change_event.user_email,
       change_event.client_type, change_event.change_resource_type,
       change_event.change_resource_name,
       change_event.resource_change_operation, change_event.changed_fields,
       campaign.name, ad_group.name
FROM change_event
WHERE change_event.change_date_time DURING LAST_7_DAYS
ORDER BY change_event.change_date_time DESC
LIMIT 1000
```

### Risky recent changes (budgets/bidding)
```sql
SELECT change_event.change_date_time, change_event.user_email,
       change_event.change_resource_type, change_event.changed_fields,
       change_event.old_resource, change_event.new_resource
FROM change_event
WHERE change_event.change_date_time DURING LAST_14_DAYS
  AND change_event.change_resource_type IN ('CampaignBudget', 'Campaign', 'ConversionAction')
ORDER BY change_event.change_date_time DESC
LIMIT 5000
```

## User access (who can see this account)
```sql
SELECT customer_user_access.user_id, customer_user_access.email_address,
       customer_user_access.access_role,
       customer_user_access.access_creation_date_time,
       customer_user_access.inviter_user_email_address
FROM customer_user_access
```
