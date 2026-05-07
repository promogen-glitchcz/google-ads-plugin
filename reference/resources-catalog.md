# Google Ads Resource Catalog (v20)

The 25 most useful resources with their key fields. Use this as a lookup when writing GAQL queries.

## customer

Account-level info.

Fields: `customer.id`, `customer.descriptive_name`, `customer.currency_code`, `customer.time_zone`, `customer.status`, `customer.manager`, `customer.test_account`, `customer.auto_tagging_enabled`, `customer.tracking_url_template`, `customer.final_url_suffix`, `customer.optimization_score`, `customer.optimization_score_weight`, `customer.has_partners_badge`, `customer.conversion_tracking_setting.conversion_tracking_id`, `customer.conversion_tracking_setting.cross_account_conversion_tracking_id`, `customer.remarketing_setting.google_global_site_tag`.

## customer_client

MCC tree (sub-accounts visible from a manager).

Fields: `customer_client.id`, `customer_client.client_customer`, `customer_client.level` (0=self, 1=direct child), `customer_client.manager`, `customer_client.descriptive_name`, `customer_client.currency_code`, `customer_client.time_zone`, `customer_client.status`, `customer_client.hidden`, `customer_client.test_account`, `customer_client.applied_labels`.

## campaign

Fields: `campaign.id`, `campaign.name`, `campaign.status` (ENABLED, PAUSED, REMOVED), `campaign.serving_status`, `campaign.primary_status`, `campaign.advertising_channel_type` (SEARCH, DISPLAY, SHOPPING, VIDEO, PERFORMANCE_MAX, DISCOVERY, LOCAL, SMART, MULTI_CHANNEL, LOCAL_SERVICES, DEMAND_GEN, TRAVEL), `campaign.advertising_channel_sub_type`, `campaign.bidding_strategy_type`, `campaign.bidding_strategy`, `campaign.start_date`, `campaign.end_date`, `campaign.campaign_budget`, `campaign.optimization_score`, `campaign.experiment_type`, `campaign.network_settings.target_google_search`, `campaign.network_settings.target_search_network`, `campaign.network_settings.target_content_network`, `campaign.network_settings.target_partner_search_network`, `campaign.geo_target_type_setting.positive_geo_target_type`, `campaign.tracking_url_template`, `campaign.url_custom_parameters`, `campaign.frequency_caps`, `campaign.target_cpa.target_cpa_micros`, `campaign.target_roas.target_roas`, `campaign.maximize_conversions.target_cpa_micros`, `campaign.maximize_conversion_value.target_roas`.

## campaign_budget

Fields: `campaign_budget.id`, `campaign_budget.name`, `campaign_budget.amount_micros` (daily), `campaign_budget.total_amount_micros`, `campaign_budget.delivery_method` (STANDARD, ACCELERATED), `campaign_budget.explicitly_shared`, `campaign_budget.reference_count`, `campaign_budget.has_recommended_budget`, `campaign_budget.recommended_budget_amount_micros`, `campaign_budget.period` (DAILY, CUSTOM_PERIOD), `campaign_budget.status`, `campaign_budget.type`.

## ad_group

Fields: `ad_group.id`, `ad_group.name`, `ad_group.status`, `ad_group.type` (SEARCH_STANDARD, DISPLAY_STANDARD, SHOPPING_PRODUCT_ADS, VIDEO_BUMPER, etc.), `ad_group.campaign`, `ad_group.cpc_bid_micros`, `ad_group.cpm_bid_micros`, `ad_group.target_cpa_micros`, `ad_group.target_roas`, `ad_group.percent_cpc_bid_micros`, `ad_group.effective_target_cpa_micros`, `ad_group.effective_target_roas`, `ad_group.labels`, `ad_group.tracking_url_template`, `ad_group.ad_rotation_mode`, `ad_group.optimized_targeting_enabled`.

## ad_group_ad

Fields: `ad_group_ad.ad.id`, `ad_group_ad.ad.name`, `ad_group_ad.ad.type` (RESPONSIVE_SEARCH_AD, RESPONSIVE_DISPLAY_AD, IMAGE_AD, VIDEO_AD, APP_AD, etc.), `ad_group_ad.status`, `ad_group_ad.policy_summary.approval_status` (APPROVED, APPROVED_LIMITED, AREA_OF_INTEREST_ONLY, DISAPPROVED, UNDER_REVIEW), `ad_group_ad.policy_summary.review_status`, `ad_group_ad.policy_summary.policy_topic_entries`, `ad_group_ad.ad_strength` (PENDING, NO_ADS, POOR, AVERAGE, GOOD, EXCELLENT), `ad_group_ad.ad.final_urls`, `ad_group_ad.ad.final_mobile_urls`, `ad_group_ad.ad.tracking_url_template`, `ad_group_ad.ad.responsive_search_ad.headlines`, `ad_group_ad.ad.responsive_search_ad.descriptions`, `ad_group_ad.ad.responsive_search_ad.path1`, `ad_group_ad.ad.responsive_search_ad.path2`, `ad_group_ad.ad.image_ad.image_url`, `ad_group_ad.ad.video_ad.video.asset`.

## ad_group_criterion (keywords, audiences, demographics)

Fields: `ad_group_criterion.criterion_id`, `ad_group_criterion.ad_group`, `ad_group_criterion.type` (KEYWORD, USER_LIST, USER_INTEREST, AGE_RANGE, GENDER, AUDIENCE), `ad_group_criterion.status`, `ad_group_criterion.negative`, `ad_group_criterion.cpc_bid_micros`, `ad_group_criterion.effective_cpc_bid_micros`, `ad_group_criterion.bid_modifier`, `ad_group_criterion.final_urls`, `ad_group_criterion.tracking_url_template`, `ad_group_criterion.keyword.text`, `ad_group_criterion.keyword.match_type` (EXACT, PHRASE, BROAD), `ad_group_criterion.quality_info.quality_score`, `ad_group_criterion.quality_info.creative_quality_score`, `ad_group_criterion.quality_info.post_click_quality_score`, `ad_group_criterion.quality_info.search_predicted_ctr`, `ad_group_criterion.position_estimates.first_page_cpc_micros`, `ad_group_criterion.position_estimates.first_position_cpc_micros`, `ad_group_criterion.position_estimates.top_of_page_cpc_micros`, `ad_group_criterion.user_list.user_list`, `ad_group_criterion.age_range.type`, `ad_group_criterion.gender.type`.

## keyword_view

Join helper for keyword performance. Distinct field: `keyword_view.resource_name`. Use it as FROM and select fields from `ad_group_criterion`, `ad_group`, `campaign` plus metrics.

## search_term_view

Fields: `search_term_view.search_term`, `search_term_view.status` (ADDED, EXCLUDED, ADDED_EXCLUDED, NONE, UNKNOWN), `search_term_view.ad_group`. Pair with `segments.keyword.info.text`, `segments.keyword.info.match_type`, `campaign.name`, `ad_group.name`. Window: 30 days max per query.

## asset

Fields: `asset.id`, `asset.name`, `asset.type` (TEXT, IMAGE, YOUTUBE_VIDEO, MEDIA_BUNDLE, CALLOUT, SITELINK, STRUCTURED_SNIPPET, PROMOTION, PRICE, CALL, CALL_TO_ACTION, BOOK_ON_GOOGLE, LEAD_FORM, MOBILE_APP), `asset.text_asset.text`, `asset.image_asset.full_size.url`, `asset.image_asset.full_size.width_pixels`, `asset.image_asset.full_size.height_pixels`, `asset.image_asset.file_size`, `asset.image_asset.mime_type`, `asset.youtube_video_asset.youtube_video_id`, `asset.youtube_video_asset.youtube_video_title`, `asset.policy_summary.approval_status`, `asset.final_urls`.

## asset_group (PMax)

Fields: `asset_group.id`, `asset_group.name`, `asset_group.campaign`, `asset_group.status`, `asset_group.primary_status`, `asset_group.primary_status_reasons`, `asset_group.final_urls`, `asset_group.final_mobile_urls`, `asset_group.path1`, `asset_group.path2`, `asset_group.ad_strength`.

## asset_group_asset, customer_asset, campaign_asset, ad_group_asset

Linkers between an asset and its parent. Fields: `<linker>.asset`, `<linker>.field_type` (HEADLINE, LONG_HEADLINE, DESCRIPTION, MARKETING_IMAGE, SQUARE_MARKETING_IMAGE, PORTRAIT_MARKETING_IMAGE, LOGO, LANDSCAPE_LOGO, CALLOUT, SITELINK, STRUCTURED_SNIPPET, CALL, PROMOTION, PRICE, BUSINESS_LOGO, BUSINESS_NAME, YOUTUBE_VIDEO, BOOK_ON_GOOGLE, LEAD_FORM, MOBILE_APP), `<linker>.status`, `<linker>.performance_label` (PENDING, LEARNING, LOW, GOOD, BEST), `<linker>.policy_summary`.

## conversion_action

Fields: `conversion_action.id`, `conversion_action.name`, `conversion_action.status`, `conversion_action.type` (WEBPAGE, AD_CALL, CLICK_TO_CALL, GOOGLE_PLAY_DOWNLOAD, GOOGLE_PLAY_IN_APP_PURCHASE, UPLOAD_CALLS, UPLOAD_CLICKS), `conversion_action.category` (DEFAULT, PAGE_VIEW, PURCHASE, SIGNUP, LEAD, DOWNLOAD, ADD_TO_CART, BEGIN_CHECKOUT, SUBSCRIBE_PAID, PHONE_CALL_LEAD), `conversion_action.primary_for_goal`, `conversion_action.click_through_lookback_window_days`, `conversion_action.view_through_lookback_window_days`, `conversion_action.counting_type` (ONE_PER_CLICK, MANY_PER_CLICK), `conversion_action.value_settings.default_value`, `conversion_action.value_settings.default_currency_code`, `conversion_action.value_settings.always_use_default_value`, `conversion_action.attribution_model_settings.attribution_model`, `conversion_action.include_in_conversions_metric`.

## audience

Fields: `audience.id`, `audience.name`, `audience.description`, `audience.status`, `audience.dimensions`, `audience.exclusion_dimension`.

## geographic_view

Fields: `geographic_view.country_criterion_id`, `geographic_view.location_type` (LOCATION_OF_PRESENCE, AREA_OF_INTEREST). Always pair with `segments.geo_target_*`.

## age_range_view, gender_view, parental_status_view

Join helpers for demographic queries. Select `ad_group_criterion.age_range.type` (AGE_RANGE_18_24, AGE_RANGE_25_34, AGE_RANGE_35_44, AGE_RANGE_45_54, AGE_RANGE_55_64, AGE_RANGE_65_UP, AGE_RANGE_UNDETERMINED), `ad_group_criterion.gender.type` (MALE, FEMALE, UNDETERMINED), or `ad_group_criterion.parental_status.type`.

## click_view

Per-click row, last 90 days only, requires `segments.date = 'YYYY-MM-DD'` (single day).

Fields: `click_view.gclid`, `click_view.ad_group_ad`, `click_view.area_of_interest.country`, `click_view.area_of_interest.city`, `click_view.location_of_presence.country`, `click_view.user_list`, `click_view.page_number`, `click_view.keyword`, `click_view.keyword_info.text`, `click_view.keyword_info.match_type`, `click_view.device_info.device_type`.

## change_event

30-day window only, max 10,000 rows per query, requires `change_event.change_date_time` filter.

Fields: `change_event.change_date_time`, `change_event.change_resource_type` (Campaign, AdGroup, AdGroupAd, AdGroupAsset, AdGroupBidModifier, AdGroupCriterion, Asset, AssetSet, CampaignAsset, CampaignBudget, CampaignCriterion, CustomerAsset, CustomerLabel, Feed, FeedItem, Label), `change_event.change_resource_name`, `change_event.client_type` (GOOGLE_ADS_WEB_CLIENT, GOOGLE_ADS_API, GOOGLE_ADS_EDITOR, GOOGLE_ADS_SCRIPTS, GOOGLE_ADS_BULK_UPLOAD, GOOGLE_ADS_AUTOMATED_RULE, GOOGLE_ADS_RECOMMENDATIONS), `change_event.user_email`, `change_event.old_resource`, `change_event.new_resource`, `change_event.resource_change_operation` (CREATE, UPDATE, REMOVE), `change_event.changed_fields`, `change_event.campaign`, `change_event.ad_group`.

## recommendation

Fields: `recommendation.resource_name`, `recommendation.type` (KEYWORD, RESPONSIVE_SEARCH_AD, USE_BROAD_MATCH_KEYWORD, MAXIMIZE_CONVERSIONS_OPT_IN, MAXIMIZE_CONVERSION_VALUE_OPT_IN, TARGET_CPA_OPT_IN, TARGET_ROAS_OPT_IN, ENHANCED_CPC_OPT_IN, MOVE_UNUSED_BUDGET, FORECASTING_CAMPAIGN_BUDGET, KEYWORD_MATCH_TYPE, CAMPAIGN_BUDGET, RESPONSIVE_SEARCH_AD_ASSET, MIGRATE_DYNAMIC_SEARCH_ADS_CAMPAIGN_TO_PERFORMANCE_MAX, OPTIMIZE_AD_ROTATION, IMPROVE_GOOGLE_TAG_COVERAGE, plus 50+ more), `recommendation.impact.base_metrics.impressions`, `recommendation.impact.base_metrics.clicks`, `recommendation.impact.base_metrics.cost_micros`, `recommendation.impact.base_metrics.conversions`, `recommendation.impact.potential_metrics.*` (same shape), `recommendation.campaign`, `recommendation.ad_group`, `recommendation.dismissed`.

Type-specific oneof fields: `recommendation.campaign_budget_recommendation.current_budget_amount_micros`, `recommendation.campaign_budget_recommendation.recommended_budget_amount_micros`, `recommendation.keyword_recommendation.keyword.text`, `recommendation.keyword_recommendation.keyword.match_type`, `recommendation.keyword_recommendation.recommended_cpc_bid_micros`, `recommendation.text_ad_recommendation.ad`, `recommendation.target_cpa_opt_in_recommendation.recommended_target_cpa_micros`.

## customer_user_access

Fields: `customer_user_access.user_id`, `customer_user_access.email_address`, `customer_user_access.access_role` (ADMIN, STANDARD, READ_ONLY, EMAIL_ONLY), `customer_user_access.access_creation_date_time`, `customer_user_access.inviter_user_email_address`.

---

## Universal metrics

| field | notes |
|---|---|
| `metrics.impressions` | int |
| `metrics.clicks` | int |
| `metrics.cost_micros` | int; / 1,000,000 for currency |
| `metrics.ctr` | float (clicks / impressions) |
| `metrics.average_cpc` | float in micros |
| `metrics.average_cpm` | float in micros |
| `metrics.conversions` | float; only Primary For Goal |
| `metrics.conversions_value` | float |
| `metrics.all_conversions` | float; includes secondary |
| `metrics.all_conversions_value` | float |
| `metrics.cost_per_conversion` | float |
| `metrics.value_per_conversion` | float |
| `metrics.search_impression_share` | 0.0-1.0 |
| `metrics.search_top_impression_share` | 0.0-1.0 |
| `metrics.search_absolute_top_impression_share` | 0.0-1.0 |
| `metrics.search_budget_lost_impression_share` | 0.0-1.0 |
| `metrics.search_rank_lost_impression_share` | 0.0-1.0 |
| `metrics.search_exact_match_impression_share` | 0.0-1.0 |
| `metrics.absolute_top_impression_percentage` | 0.0-1.0 |
| `metrics.top_impression_percentage` | 0.0-1.0 |
| `metrics.video_views` | int (Video / Demand Gen) |
| `metrics.video_view_rate` | float |
| `metrics.engagements` | int |
| `metrics.interactions` | int |
| `metrics.interaction_rate` | float |
| `metrics.average_cost` | float |

## Universal segments

**Time:** `segments.date` (YYYY-MM-DD), `segments.hour` (0-23), `segments.day_of_week` (MONDAY..SUNDAY), `segments.week`, `segments.month`, `segments.quarter`, `segments.year`.

**Device & network:** `segments.device` (MOBILE, TABLET, DESKTOP, CONNECTED_TV, OTHER); `segments.ad_network_type` (SEARCH, SEARCH_PARTNERS, CONTENT, YOUTUBE_SEARCH, YOUTUBE_WATCH, MIXED).

**Conversions:** `segments.conversion_action`, `segments.conversion_action_name`, `segments.conversion_action_category`, `segments.conversion_attribution_event_type` (IMPRESSION, INTERACTION).

**Geo:** `segments.geo_target_country`, `segments.geo_target_region`, `segments.geo_target_metro`, `segments.geo_target_city`, `segments.geo_target_postal_code`. Values are resource names like `geoTargetConstants/2840` (USA), `2203` (CZ), `2703` (SK).

**Search-specific:** `segments.keyword.info.text`, `segments.keyword.info.match_type`, `segments.search_term_match_type`, `segments.click_type`.

**Asset/PMax:** `segments.asset_interaction_target.asset`, `segments.asset_interaction_target.interaction_on_this_asset`.

**Click & touchpoint:** `segments.click_type`, `segments.slot` (SEARCH_SIDE, SEARCH_TOP, SEARCH_OTHER, CONTENT, SEARCH_PARTNER_TOP, SEARCH_PARTNER_OTHER, MIXED).

**Shopping (with `shopping_performance_view`):** `segments.product_item_id`, `segments.product_title`, `segments.product_brand`, `segments.product_type_l1..l5`, `segments.product_channel`, `segments.product_country`, `segments.product_language`.

## Common geo target constants

| ID | Country |
|---|---|
| 2203 | Czech Republic |
| 2703 | Slovakia |
| 2276 | Germany |
| 2040 | Austria |
| 2348 | Hungary |
| 2616 | Poland |
| 2840 | USA |
| 2826 | UK |
| 2250 | France |
| 2380 | Italy |
| 2724 | Spain |
| 2528 | Netherlands |
| 2056 | Belgium |
| 2208 | Denmark |
| 2752 | Sweden |
| 2246 | Finland |
| 2578 | Norway |

For specific cities/regions, query `geo_target_constant` resource with name LIKE.
