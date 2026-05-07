---
name: ad-management
description: Create, edit, pause, remove ads. Includes Responsive Search Ads (RSA), image ads, Performance Max asset groups (headlines, descriptions, images, videos), final URLs, ad extensions/assets (sitelinks, callouts, structured snippets, call). Use for "create new ad", "add headline to RSA", "swap image asset", "create PMax asset group", "edit ad copy", "pause ads with low CTR", "add sitelink".
---

# Ad management

## Ad types in Google Ads (2026)
- `RESPONSIVE_SEARCH_AD` - the only Search ad type now (ETAs are gone). Up to 15 headlines, 4 descriptions.
- `RESPONSIVE_DISPLAY_AD` - for Display campaigns
- `APP_AD`, `LOCAL_AD`, `DISCOVERY_*`, `VIDEO_*`
- Performance Max uses `asset_group` + assets, not `ad_group_ad`.

## Create a Responsive Search Ad

```python
import sys; sys.path.insert(0, '.')
from lib import GoogleAdsClient
c = GoogleAdsClient()
CUSTOMER_ID, AD_GROUP_ID = "1234567890", "111222333"

ad = {
    "responsiveSearchAd": {
        "headlines": [
            {"text": "Buy Running Shoes"},
            {"text": "Free Shipping"},
            {"text": "30-Day Returns"},
            {"text": "Top Brands"},
            {"text": "Shop Today"},
        ],
        "descriptions": [
            {"text": "Premium running shoes from top brands. Order now."},
            {"text": "Fast shipping and easy returns. Quality guaranteed."},
        ],
        "path1": "shop",
        "path2": "running",
    },
    "finalUrls": ["https://example.com/running-shoes"],
}

ops = [{
    "create": {
        "adGroup": c.resource_name(CUSTOMER_ID, "adGroups", AD_GROUP_ID),
        "status": "PAUSED",  # start paused, enable after review
        "ad": ad,
    }
}]
print(c.mutate_resource(CUSTOMER_ID, "adGroupAds", ops, validate_only=True))
```

### RSA constraints
- Headlines: 30 chars max each, 3-15 of them, at least 3 required
- Descriptions: 90 chars max each, 2-4 of them, at least 2 required
- Path1, Path2: 15 chars max each, optional
- Final URLs: required, can be multiple, all must use same domain

### Pinning (force a headline/description into a slot)
```python
{"text": "Brand Name", "pinnedField": "HEADLINE_1"}
```
Pinning reduces RSA performance - use sparingly and only when the user insists (e.g. legal must-have).

### Ad strength
RSAs get an "Ad Strength" rating (POOR -> EXCELLENT) based on text variety. Aim for "GOOD" or better. The lib has helpers to score before save.

## Edit an existing RSA

You can't update headlines/descriptions in place. To change copy, you must:
1. Create a new ad in the same ad group
2. Verify it's serving
3. Remove the old ad

This is the official Google approach. Don't try to update headlines via mutate.

You CAN update the ad-group-ad's `status` and metadata (e.g. labels), and the ad's `final_urls` and `tracking_url_template`.

## Pause / remove an ad

```python
# pause
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "adGroupAds", f"{AD_GROUP_ID}~{AD_ID}"),
        "status": "PAUSED",
    },
    "updateMask": "status",
}]

# remove
ops = [{"remove": c.resource_name(CUSTOMER_ID, "adGroupAds", f"{AD_GROUP_ID}~{AD_ID}")}]
```

## Find disapproved ads

```sql
SELECT ad_group_ad.ad.id, ad_group.name, campaign.name,
       ad_group_ad.policy_summary.approval_status,
       ad_group_ad.policy_summary.review_status,
       ad_group_ad.policy_summary.policy_topic_entries
FROM ad_group_ad
WHERE ad_group_ad.policy_summary.approval_status IN ('DISAPPROVED', 'AREA_OF_INTEREST_ONLY')
  AND ad_group_ad.status = 'ENABLED'
```

`policy_topic_entries` lists the policy topics violated.

## Image and video assets (used by RSA, PMax, Display)

### Upload an image asset

```python
import base64
img_bytes = open("logo.png", "rb").read()
ops = [{
    "create": {
        "name": "Logo 1200x628",
        "type": "IMAGE",
        "imageAsset": {
            "data": base64.b64encode(img_bytes).decode(),
        },
    }
}]
print(c.mutate_resource(CUSTOMER_ID, "assets", ops))
```

Returns `customers/.../assets/{ASSET_ID}`. Save that ID; you'll attach it to ad groups, campaigns, or asset groups.

### Attach as sitelink to a campaign

A sitelink is `text_asset + sitelink_asset` - here's the full pattern:

```python
# 1. Create a sitelink asset
ops_asset = [{
    "create": {
        "name": "Shop now sitelink",
        "type": "SITELINK",
        "sitelinkAsset": {
            "linkText": "Shop now",
            "description1": "30-day returns",
            "description2": "Free shipping",
        },
        "finalUrls": ["https://example.com/shop"],
    }
}]
asset_resp = c.mutate_resource(CUSTOMER_ID, "assets", ops_asset)
asset_resource = asset_resp["results"][0]["resourceName"]

# 2. Link to campaign
link_ops = [{
    "create": {
        "campaign": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "asset": asset_resource,
        "fieldType": "SITELINK",
    }
}]
c.mutate_resource(CUSTOMER_ID, "campaignAssets", link_ops)
```

Other asset field types: `CALLOUT`, `STRUCTURED_SNIPPET`, `CALL`, `PROMOTION`, `PRICE`, `BUSINESS_LOGO`, `BUSINESS_NAME`, `HEADLINE`, `DESCRIPTION`, `MARKETING_IMAGE`, `LOGO`, `VIDEO`.

## Performance Max asset groups

PMax bundles assets into asset groups. Create flow:

1. Create the campaign with `advertisingChannelType=PERFORMANCE_MAX`
2. Create an `assetGroup` linked to that campaign
3. Create assets (text/image/video)
4. Link via `assetGroupAsset` with field types: HEADLINE, LONG_HEADLINE, DESCRIPTION, MARKETING_IMAGE, SQUARE_MARKETING_IMAGE, LOGO, BUSINESS_NAME, YOUTUBE_VIDEO

```python
# all in one batch
mutate_ops = [
    {
        "campaignOperation": {"create": {
            "name": "PMax 2026", "advertisingChannelType": "PERFORMANCE_MAX",
            "status": "PAUSED", "campaignBudget": ...,
            "maximizeConversionValue": {"targetRoas": 4.0},
        }}
    },
    {
        "assetGroupOperation": {"create": {
            "resourceName": f"customers/{CUSTOMER_ID}/assetGroups/-2",
            "campaign": f"customers/{CUSTOMER_ID}/campaigns/-1",  # references prev step
            "name": "Asset Group 1",
            "finalUrls": ["https://example.com"],
            "status": "ENABLED",
        }}
    },
    # ... assetGroupAssetOperation entries linking each asset
]
```

Building PMax via API is verbose. Prefer the helper script:
```bash
python3 scripts/create_pmax.py --customer ID --name "X" --budget 50 \
  --final-url https://example.com \
  --headlines "H1|H2|H3" --long-headlines "LH1|LH2" \
  --descriptions "D1|D2" \
  --images img1.jpg,img2.jpg,square1.jpg
```

## RSA performance analysis (asset-level)

```sql
SELECT asset.id, asset.name, asset.text_asset.text,
       asset_group.name, campaign.name,
       metrics.impressions, metrics.clicks
FROM asset_group_asset
WHERE segments.date DURING LAST_30_DAYS
  AND asset_group_asset.field_type IN ('HEADLINE', 'DESCRIPTION')
ORDER BY metrics.impressions DESC
```

For RSA-level: query `ad_group_ad_asset_view`.

## Reference

- [reference/mutations-guide.md](../../reference/mutations-guide.md) - asset/ad creation patterns
- [reference/resources-catalog.md](../../reference/resources-catalog.md) - asset, ad_group_ad, asset_group fields
