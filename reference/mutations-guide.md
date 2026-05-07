# Google Ads API v20 - Mutations Reference (REST)

> Reference for an LLM driving safe write operations against the Google Ads API v20 (current stable as of May 2026). All examples use the REST/JSON interface. Snake_case proto field names are mapped to lowerCamelCase in JSON.

API base: `https://googleads.googleapis.com/v20`
Released: June 2025 (current stable in May 2026; v21+ exists but v20 still supported per Google's 14-month support window).

---

## 1. Mutation request structure

### 1.1 Two parallel ways to mutate

| Approach | URL | Use when |
|---|---|---|
| Resource-specific | `POST /v20/customers/{customer_id}/{resource}:mutate` | Mutating ONE resource type per request |
| Bulk (cross-resource) | `POST /v20/customers/{customer_id}/googleAds:mutate` | Mutating MULTIPLE resource types in one transaction (e.g. campaign + ad group + ad) |

Resource-specific mutate is simpler. Bulk mutate (`googleAds:mutate`) is the only way to atomically create dependent resources with **temporary resource names** in a single round-trip.

### 1.2 Required HTTP headers

```
Content-Type: application/json
Authorization: Bearer {OAUTH2_ACCESS_TOKEN}
developer-token: {DEVELOPER_TOKEN}
login-customer-id: {MANAGER_CUSTOMER_ID}   # only when calling through an MCC
```

`login-customer-id` is the manager (MCC) account ID; `customer_id` in the URL is the actual ad account being mutated. Both are 10-digit numbers, no dashes.

### 1.3 Request body shape (resource-specific)

```json
{
  "operations": [
    { "create": { /* full resource */ } },
    { "update": { /* resource w/ resourceName */ }, "updateMask": "field1,field2.subfield" },
    { "remove": "customers/123/campaigns/456" }
  ],
  "partialFailure": false,
  "validateOnly": false,
  "responseContentType": "RESOURCE_NAME_ONLY"
}
```

### 1.4 The Operation object - exactly one of:

- **`create`**: full resource JSON, NO `resourceName` field. Server assigns the ID and returns the new resource name.
- **`update`**: resource JSON that MUST include `resourceName`. Pair with `updateMask` listing fields to change. Fields not in the mask are ignored even if you send them.
- **`remove`**: just the resource name string (`customers/{cid}/campaigns/{cmpid}`). The status flips to `REMOVED`. Note - removed objects in Google Ads are tombstoned, not hard-deleted.

You CANNOT have `create` + `update` in the same operation. One operation = one of the three.

### 1.5 `updateMask` (FieldMask)

- Comma-separated list of paths in lowerCamelCase.
- Paths are relative to the resource being updated (no root prefix).
- `"name,status"` or nested `"networkSettings.targetSearchNetwork"`.
- **Required for every update**. An empty mask returns `FIELD_MASK_MISSING`.
- Fields you send that are NOT in the mask are silently ignored.
- For nested objects, the mask must include each subfield you want to change. Sending the parent path without subfields means "no subfields are being updated" - effectively a no-op for that branch.
- Use the helper pattern: build the resource with only the fields you want to change set, then include exactly those field paths in the mask.

### 1.6 `partialFailure`

- `false` (default): all-or-nothing. One bad operation = the whole batch fails, no resource is mutated, you get `GoogleAdsFailure` with per-op errors.
- `true`: good operations apply, bad ones return errors. The response has `partialFailureError` with details. Use for bulk imports where you want to keep going.
- Not all services support `partialFailure: true` - check the service docs. `customers.googleAds:mutate` (bulk mutate) supports it.

### 1.7 `validateOnly`

- `false` (default): execute.
- `true`: validate the request and return the same errors you'd get on real execution, but **don't write anything**. Costs 0 ops against the daily quota in most cases. **Run validate_only=true first when in doubt.**

### 1.8 `responseContentType`

- `RESOURCE_NAME_ONLY` (default): only `resourceName` returned per result. Smallest response.
- `MUTABLE_RESOURCE`: returns the full mutated resource for each op. Avoids a follow-up search query but the payload is bigger.

---

## 2. Resource-by-resource REST examples

For all examples below, replace `{CID}` with the 10-digit customer ID (no dashes).

### 2.1 Campaign budget

`POST https://googleads.googleapis.com/v20/customers/{CID}/campaignBudgets:mutate`

**Create (daily, standard delivery, not shared):**

```json
{
  "operations": [
    {
      "create": {
        "name": "My Daily Budget 2026-05-07",
        "amountMicros": "10000000",
        "deliveryMethod": "STANDARD",
        "explicitlyShared": false,
        "period": "DAILY"
      }
    }
  ]
}
```

`amountMicros: "10000000"` = 10 currency units/day. Note: large 64-bit ints are sent as strings in JSON.

**Update budget amount only:**

```json
{
  "operations": [
    {
      "update": {
        "resourceName": "customers/{CID}/campaignBudgets/123456789",
        "amountMicros": "20000000"
      },
      "updateMask": "amountMicros"
    }
  ]
}
```

**Remove:**

```json
{
  "operations": [
    { "remove": "customers/{CID}/campaignBudgets/123456789" }
  ]
}
```

A budget can only be removed if no campaign references it; otherwise you get `OPERATION_NOT_PERMITTED_FOR_REMOVED_RESOURCE` or `CANNOT_OPERATE_ON_REMOVED_CAMPAIGN_BUDGET`.

For total budgets (PMax, app campaigns can use total): set `period: "CUSTOM_PERIOD"`, `totalAmountMicros`, and `explicitlyShared: false`.

### 2.2 Campaign

`POST https://googleads.googleapis.com/v20/customers/{CID}/campaigns:mutate`

**Search campaign with manual CPC:**

```json
{
  "operations": [
    {
      "create": {
        "name": "Search - Brand - 2026-05",
        "advertisingChannelType": "SEARCH",
        "status": "PAUSED",
        "manualCpc": { "enhancedCpcEnabled": false },
        "campaignBudget": "customers/{CID}/campaignBudgets/123456789",
        "networkSettings": {
          "targetGoogleSearch": true,
          "targetSearchNetwork": true,
          "targetContentNetwork": false,
          "targetPartnerSearchNetwork": false
        },
        "geoTargetTypeSetting": {
          "positiveGeoTargetType": "PRESENCE_OR_INTEREST",
          "negativeGeoTargetType": "PRESENCE"
        },
        "startDate": "2026-05-08",
        "endDate": "2026-12-31"
      }
    }
  ]
}
```

**ALWAYS create campaigns as `PAUSED`** so ads don't immediately serve before keywords/ads are attached.

**Search campaign with Maximize Conversions:**

```json
{
  "operations": [
    {
      "create": {
        "name": "Search - MaxConv - 2026-05",
        "advertisingChannelType": "SEARCH",
        "status": "PAUSED",
        "maximizeConversions": {
          "targetCpaMicros": "5000000"
        },
        "campaignBudget": "customers/{CID}/campaignBudgets/123456789",
        "networkSettings": {
          "targetGoogleSearch": true,
          "targetSearchNetwork": false,
          "targetContentNetwork": false,
          "targetPartnerSearchNetwork": false
        }
      }
    }
  ]
}
```

`targetCpaMicros` is optional; omit for pure spend-out maximize.

**Display campaign:**

```json
{
  "operations": [
    {
      "create": {
        "name": "Display - Remarketing - 2026-05",
        "advertisingChannelType": "DISPLAY",
        "status": "PAUSED",
        "manualCpc": {},
        "campaignBudget": "customers/{CID}/campaignBudgets/123456789"
      }
    }
  ]
}
```

**Performance Max campaign:**

```json
{
  "operations": [
    {
      "create": {
        "name": "PMax - Catalog - 2026-05",
        "advertisingChannelType": "PERFORMANCE_MAX",
        "status": "PAUSED",
        "campaignBudget": "customers/{CID}/campaignBudgets/123456789",
        "maximizeConversionValue": { "targetRoas": 4.0 },
        "urlExpansionOptOut": false
      }
    }
  ]
}
```

PMax requires a `maximize_conversions` or `maximize_conversion_value` strategy and at least one asset group attached after creation.

**Update bidding strategy on existing campaign:**

```json
{
  "operations": [
    {
      "update": {
        "resourceName": "customers/{CID}/campaigns/9876543210",
        "maximizeConversions": { "targetCpaMicros": "8000000" }
      },
      "updateMask": "maximizeConversions.targetCpaMicros,maximizeConversions"
    }
  ]
}
```

You CAN switch strategy types (e.g. from `manualCpc` to `maximizeConversions`) by setting the new strategy field and including its path in the mask. This is one of the few oneof switches the API allows.

**Pause / enable campaign:**

```json
{
  "operations": [
    {
      "update": {
        "resourceName": "customers/{CID}/campaigns/9876543210",
        "status": "ENABLED"
      },
      "updateMask": "status"
    }
  ]
}
```

Allowed transitions: `ENABLED <-> PAUSED`. To `REMOVED` is one-way (use `remove` op for that).

### 2.3 Ad group

`POST https://googleads.googleapis.com/v20/customers/{CID}/adGroups:mutate`

```json
{
  "operations": [
    {
      "create": {
        "name": "Brand exact",
        "campaign": "customers/{CID}/campaigns/9876543210",
        "status": "ENABLED",
        "type": "SEARCH_STANDARD",
        "cpcBidMicros": "1500000"
      }
    }
  ]
}
```

`type` must match the channel: `SEARCH_STANDARD`, `DISPLAY_STANDARD`, `SHOPPING_PRODUCT_ADS`. For PMax, asset groups replace ad groups - do not create ad groups in PMax campaigns.

### 2.4 Ad group keyword (positive + negative)

`POST https://googleads.googleapis.com/v20/customers/{CID}/adGroupCriteria:mutate`

**Positive keyword (phrase match, paused):**

```json
{
  "operations": [
    {
      "create": {
        "adGroup": "customers/{CID}/adGroups/1111222333",
        "status": "ENABLED",
        "keyword": {
          "text": "running shoes",
          "matchType": "PHRASE"
        },
        "cpcBidMicros": "2000000"
      }
    }
  ]
}
```

`matchType` values: `EXACT`, `PHRASE`, `BROAD`. (`BROAD_MATCH_MODIFIER` was deprecated.) `text` is max 80 chars / 10 words.

**Negative keyword at ad group level:**

```json
{
  "operations": [
    {
      "create": {
        "adGroup": "customers/{CID}/adGroups/1111222333",
        "negative": true,
        "keyword": {
          "text": "free",
          "matchType": "BROAD"
        }
      }
    }
  ]
}
```

For negatives do NOT set `cpcBidMicros` or `status` (negatives are always implicitly active and don't bid).

### 2.5 Campaign-level negative keyword

`POST https://googleads.googleapis.com/v20/customers/{CID}/campaignCriteria:mutate`

```json
{
  "operations": [
    {
      "create": {
        "campaign": "customers/{CID}/campaigns/9876543210",
        "negative": true,
        "keyword": {
          "text": "wholesale",
          "matchType": "BROAD"
        }
      }
    }
  ]
}
```

**v20 added campaign-level negative keywords for Performance Max** - same JSON, just point `campaign` at a PMax campaign.

### 2.6 Geo targeting (campaign criterion)

```json
{
  "operations": [
    {
      "create": {
        "campaign": "customers/{CID}/campaigns/9876543210",
        "location": { "geoTargetConstant": "geoTargetConstants/2203" }
      }
    }
  ]
}
```

`2203` = Czech Republic. Find IDs via the `geoTargetConstants` resource search or Google's static reference. For exclusion, add `"negative": true`.

**Proximity targeting:**

```json
{
  "operations": [
    {
      "create": {
        "campaign": "customers/{CID}/campaigns/9876543210",
        "proximity": {
          "geoPoint": { "longitudeInMicroDegrees": 14418540, "latitudeInMicroDegrees": 50087810 },
          "radius": 5.0,
          "radiusUnits": "KILOMETERS"
        }
      }
    }
  ]
}
```

### 2.7 Audience targeting (ad group criterion)

```json
{
  "operations": [
    {
      "create": {
        "adGroup": "customers/{CID}/adGroups/1111222333",
        "userList": { "userList": "customers/{CID}/userLists/444555666" }
      }
    }
  ]
}
```

Or with the unified Audience resource:

```json
{
  "operations": [
    {
      "create": {
        "adGroup": "customers/{CID}/adGroups/1111222333",
        "audience": { "audience": "customers/{CID}/audiences/777888999" }
      }
    }
  ]
}
```

### 2.8 Responsive Search Ad

`POST https://googleads.googleapis.com/v20/customers/{CID}/adGroupAds:mutate`

```json
{
  "operations": [
    {
      "create": {
        "adGroup": "customers/{CID}/adGroups/1111222333",
        "status": "PAUSED",
        "ad": {
          "finalUrls": ["https://example.com/landing"],
          "finalMobileUrls": [],
          "responsiveSearchAd": {
            "headlines": [
              { "text": "Buy Running Shoes Online", "pinnedField": "HEADLINE_1" },
              { "text": "Free Shipping Over $50" },
              { "text": "30-Day Returns" },
              { "text": "Top Brands - Big Selection" },
              { "text": "Fast Delivery to Your Door" }
            ],
            "descriptions": [
              { "text": "Shop the latest running shoes from top brands. Free shipping on orders over $50." },
              { "text": "Discover comfortable, durable shoes for every runner. Try them risk-free for 30 days." }
            ],
            "path1": "shoes",
            "path2": "running"
          }
        }
      }
    }
  ]
}
```

Constraints:
- `headlines`: 3-15, each <= 30 chars.
- `descriptions`: 2-4, each <= 90 chars.
- `path1`, `path2`: optional, <= 15 chars each, no spaces.
- `finalUrls`: at least 1; final URL domain must match the display URL.
- `pinnedField`: optional. Values: `HEADLINE_1`, `HEADLINE_2`, `HEADLINE_3`, `DESCRIPTION_1`, `DESCRIPTION_2`. Pinning forces a slot - use sparingly because it limits Google's optimization.
- Always create with `status: "PAUSED"` first, verify, then enable.

**Update an RSA's headlines** - the WHOLE `responsiveSearchAd` must be re-sent because list fields can't be partial-updated:

```json
{
  "operations": [
    {
      "update": {
        "resourceName": "customers/{CID}/adGroupAds/1111222333~9999888777",
        "ad": {
          "responsiveSearchAd": {
            "headlines": [
              { "text": "New Headline 1" },
              { "text": "New Headline 2" },
              { "text": "New Headline 3" }
            ],
            "descriptions": [
              { "text": "Updated description 1." },
              { "text": "Updated description 2." }
            ]
          }
        }
      },
      "updateMask": "ad.responsiveSearchAd.headlines,ad.responsiveSearchAd.descriptions"
    }
  ]
}
```

`adGroupAd` resource names use the `~` separator: `adGroupAds/{adGroupId}~{adId}`.

### 2.9 Asset (text, image, video)

`POST https://googleads.googleapis.com/v20/customers/{CID}/assets:mutate`

**Image asset** (image must be uploaded inline as base64):

```json
{
  "operations": [
    {
      "create": {
        "name": "Hero - 1200x628",
        "type": "IMAGE",
        "imageAsset": {
          "data": "{BASE64_BYTES}",
          "fileSize": "245678",
          "mimeType": "IMAGE_JPEG",
          "fullSize": {
            "heightPixels": "628",
            "widthPixels": "1200",
            "url": "https://example.com/hero.jpg"
          }
        }
      }
    }
  ]
}
```

Allowed `mimeType`: `IMAGE_JPEG`, `IMAGE_PNG`, `IMAGE_GIF`. Max size depends on slot - 5120 KB for most placements.

**Text asset** (headline / description for PMax):

```json
{
  "operations": [
    {
      "create": {
        "name": "Headline - Free Shipping",
        "type": "TEXT",
        "textAsset": { "text": "Free Shipping on Orders $50+" }
      }
    }
  ]
}
```

**YouTube video asset** (video must already be on YouTube; you reference its ID):

```json
{
  "operations": [
    {
      "create": {
        "name": "Brand video 30s",
        "type": "YOUTUBE_VIDEO",
        "youtubeVideoAsset": { "youtubeVideoId": "dQw4w9WgXcQ" }
      }
    }
  ]
}
```

Once created, an asset is reusable across campaigns/asset groups. Attempting to upload an image with identical bytes returns `DUPLICATE_ASSET` - reuse the existing resource name.

### 2.10 Performance Max asset group + asset_group_asset

PMax MUST use `googleAds:mutate` (bulk mutate) with temporary names because Google enforces "asset group + minimum required assets in the SAME request" for non-retail PMax.

`POST https://googleads.googleapis.com/v20/customers/{CID}/googleAds:mutate`

```json
{
  "mutateOperations": [
    {
      "assetOperation": {
        "create": {
          "resourceName": "customers/{CID}/assets/-1",
          "name": "PMax Headline 1",
          "type": "TEXT",
          "textAsset": { "text": "Premium Running Gear" }
        }
      }
    },
    {
      "assetOperation": {
        "create": {
          "resourceName": "customers/{CID}/assets/-2",
          "name": "PMax Headline 2",
          "type": "TEXT",
          "textAsset": { "text": "Shop the Latest Drops" }
        }
      }
    },
    {
      "assetOperation": {
        "create": {
          "resourceName": "customers/{CID}/assets/-3",
          "name": "PMax Description",
          "type": "TEXT",
          "textAsset": { "text": "Top brands, fast shipping, 30-day returns." }
        }
      }
    },
    {
      "assetGroupOperation": {
        "create": {
          "resourceName": "customers/{CID}/assetGroups/-100",
          "name": "PMax Asset Group 2026-05",
          "campaign": "customers/{CID}/campaigns/9876543210",
          "finalUrls": ["https://example.com/store"],
          "status": "PAUSED"
        }
      }
    },
    {
      "assetGroupAssetOperation": {
        "create": {
          "assetGroup": "customers/{CID}/assetGroups/-100",
          "asset": "customers/{CID}/assets/-1",
          "fieldType": "HEADLINE"
        }
      }
    },
    {
      "assetGroupAssetOperation": {
        "create": {
          "assetGroup": "customers/{CID}/assetGroups/-100",
          "asset": "customers/{CID}/assets/-2",
          "fieldType": "HEADLINE"
        }
      }
    },
    {
      "assetGroupAssetOperation": {
        "create": {
          "assetGroup": "customers/{CID}/assetGroups/-100",
          "asset": "customers/{CID}/assets/-3",
          "fieldType": "DESCRIPTION"
        }
      }
    }
  ],
  "partialFailure": false,
  "validateOnly": true
}
```

Key points:
- `mutateOperations` (not `operations`) for `googleAds:mutate`.
- Each entry is wrapped in a typed operation: `assetOperation`, `assetGroupOperation`, `assetGroupAssetOperation`, `campaignOperation`, etc.
- **Negative-ID resource names** (`assets/-1`, `assetGroups/-100`) are temporary and only valid within this request. Each must be unique across the whole request, even across types.
- Order matters: define a temporary resource BEFORE referencing it.
- PMax minimum assets: 3 headlines, 1 long headline, 2 descriptions, 1 business name, 1 logo (square), 1 marketing image (landscape), 1 square marketing image. Optional: video, portrait images, more text. Without the minimums you get `ASSET_GROUP_REQUIRED_ASSET_TYPES_MISSING` or `ASSET_LINK_REQUIRED_ASSET_FIELD_TYPES_MISSING`.
- `fieldType` enum: `HEADLINE`, `LONG_HEADLINE`, `DESCRIPTION`, `BUSINESS_NAME`, `MARKETING_IMAGE`, `SQUARE_MARKETING_IMAGE`, `PORTRAIT_MARKETING_IMAGE`, `LOGO`, `LANDSCAPE_LOGO`, `YOUTUBE_VIDEO`, `CALL_TO_ACTION_SELECTION`.

### 2.11 Conversion action

`POST https://googleads.googleapis.com/v20/customers/{CID}/conversionActions:mutate`

```json
{
  "operations": [
    {
      "create": {
        "name": "Purchase - Web - 2026",
        "type": "WEBPAGE",
        "category": "PURCHASE",
        "status": "ENABLED",
        "primaryForGoal": true,
        "countingType": "ONE_PER_CLICK",
        "clickThroughLookbackWindowDays": "30",
        "viewThroughLookbackWindowDays": "1",
        "valueSettings": {
          "defaultValue": 25.00,
          "defaultCurrencyCode": "USD",
          "alwaysUseDefaultValue": false
        },
        "attributionModelSettings": {
          "attributionModel": "GOOGLE_ADS_DATA_DRIVEN"
        }
      }
    }
  ]
}
```

`type` is **immutable** after create. Common types: `WEBPAGE`, `UPLOAD_CLICKS`, `UPLOAD_CALLS`, `WEBSITE_CALL`, `GOOGLE_ANALYTICS_4_CUSTOM`. Names must be unique per account or you get `DUPLICATE_NAME`.

### 2.12 Bidding strategy update on campaign

(Already shown in 2.2 - update via `customers/{CID}/campaigns:mutate` with the new bidding oneof and the corresponding mask path.)

You can also create a **portfolio** bidding strategy and assign it:

```json
// Step 1 - POST /v20/customers/{CID}/biddingStrategies:mutate
{
  "operations": [
    {
      "create": {
        "name": "Portfolio Target ROAS - eCom",
        "targetRoas": { "targetRoas": 5.0 }
      }
    }
  ]
}

// Step 2 - POST /v20/customers/{CID}/campaigns:mutate
{
  "operations": [
    {
      "update": {
        "resourceName": "customers/{CID}/campaigns/9876543210",
        "biddingStrategy": "customers/{CID}/biddingStrategies/12345"
      },
      "updateMask": "biddingStrategy"
    }
  ]
}
```

Note: a campaign uses EITHER a portfolio (`biddingStrategy`) OR a campaign-level oneof (`manualCpc`, `maximizeConversions`, etc.) - never both.

---

## 3. REST endpoint URL summary

| Resource | URL |
|---|---|
| Campaign budget | `/v20/customers/{cid}/campaignBudgets:mutate` |
| Campaign | `/v20/customers/{cid}/campaigns:mutate` |
| Ad group | `/v20/customers/{cid}/adGroups:mutate` |
| Ad group ad | `/v20/customers/{cid}/adGroupAds:mutate` |
| Ad group criterion (kw, audience) | `/v20/customers/{cid}/adGroupCriteria:mutate` |
| Campaign criterion (geo, lang, neg) | `/v20/customers/{cid}/campaignCriteria:mutate` |
| Asset | `/v20/customers/{cid}/assets:mutate` |
| Asset group | `/v20/customers/{cid}/assetGroups:mutate` |
| Asset group asset | `/v20/customers/{cid}/assetGroupAssets:mutate` |
| Conversion action | `/v20/customers/{cid}/conversionActions:mutate` |
| Bidding strategy (portfolio) | `/v20/customers/{cid}/biddingStrategies:mutate` |
| User list (audience) | `/v20/customers/{cid}/userLists:mutate` |
| Customer (label, settings) | `/v20/customers/{cid}:mutate` |
| Bulk / cross-resource | `/v20/customers/{cid}/googleAds:mutate` |

All are `POST`. JSON in, JSON out.

---

## 4. Resource name patterns

Resource names are opaque-looking strings the API uses everywhere. Format:

```
customers/{customer_id}/{resource}/{id}
```

Examples:
- `customers/1234567890/campaigns/9876543210`
- `customers/1234567890/campaignBudgets/111222333`
- `customers/1234567890/adGroups/4445556667`

Composite IDs use `~`:
- `customers/{cid}/adGroupAds/{ad_group_id}~{ad_id}`
- `customers/{cid}/adGroupCriteria/{ad_group_id}~{criterion_id}`
- `customers/{cid}/campaignCriteria/{campaign_id}~{criterion_id}`
- `customers/{cid}/assetGroupAssets/{asset_group_id}~{asset_id}~{field_type}`

Constants (immutable references managed by Google):
- `geoTargetConstants/2203` (country, region, city)
- `languageConstants/1000`
- `productCategoryConstants/{id}`

You construct resource names by concatenation; you don't ask the API for them ahead of time. After a `create`, the response gives you the assigned resource name. Save it.

---

## 5. Micro amounts

All currency-typed fields end in `Micros` and are 1,000,000 x the actual currency unit. The API works in the account's currency (no auto-conversion on input).

| You want | Send |
|---|---|
| 0.50 USD bid | `cpcBidMicros: "500000"` |
| 1.00 USD/day budget | `amountMicros: "1000000"` |
| 100 EUR/day budget | `amountMicros: "100000000"` |
| 5.00 CZK CPC | `cpcBidMicros: "5000000"` |

Notes:
- Always send as strings in JSON (proto int64 -> JSON string).
- Some currencies have a minimum step. CPC bids must be multiples of the currency unit's smallest billable increment (often 10,000 micros = 0.01).
- Negative micros are invalid.

Conversion value is in regular floats (`defaultValue: 25.00`), not micros. Only fields literally named `*Micros` are micro-encoded.

---

## 6. Common errors and how to avoid them

The HTTP response body on failure has shape:

```json
{
  "error": {
    "code": 400,
    "message": "Request contains an invalid argument.",
    "status": "INVALID_ARGUMENT",
    "details": [
      {
        "@type": "type.googleapis.com/google.ads.googleads.v20.errors.GoogleAdsFailure",
        "errors": [
          {
            "errorCode": { "fieldError": "REQUIRED" },
            "message": "The required field was not present.",
            "trigger": { "stringValue": "" },
            "location": {
              "fieldPathElements": [
                { "fieldName": "operations", "index": 0 },
                { "fieldName": "create" },
                { "fieldName": "campaign_budget" }
              ]
            }
          }
        ]
      }
    ]
  }
}
```

The TOP-LEVEL `status` is the gRPC code; the per-error `errorCode` is the Google Ads-specific code. Always read `details[].errors[].location.fieldPathElements` to find the offending field.

| Error | Cause | Fix |
|---|---|---|
| `INVALID_ARGUMENT` | Malformed request, bad enum, wrong type | Check the field path in `location`; validate enum strings; use string for int64 |
| `RESOURCE_NOT_FOUND` / `MutateError.RESOURCE_NOT_FOUND` | Resource name points at something that doesn't exist or was removed | Re-fetch via search; check the customer ID in the path; verify the parent (campaign for ad group, etc.) |
| `REQUIRED_FIELD_MISSING` (FieldError.REQUIRED) | A required field is absent | The `location` shows which one. For ad group: `name`, `campaign`. For RSA: 3 headlines, 2 descriptions, 1 final URL |
| `FIELD_MASK_MISSING` / `FieldMaskError.FIELD_HAS_SUBFIELDS` | Empty mask, or you sent a parent path without subfields | Always send `updateMask` on update; for nested fields list each subfield path |
| `INVALID_STATUS_TRANSITION` (CampaignError.CANNOT_SET_STATUS) | Trying e.g. `REMOVED -> ENABLED` | Removed is one-way. Recreate. |
| `DUPLICATE_NAME` (CampaignError.DUPLICATE_CAMPAIGN_NAME, ConversionActionError.DUPLICATE_NAME) | Name already used (often for non-removed entities of the same type) | Append a suffix; or rename the old one; or reuse it |
| `POLICY_VIOLATION` (PolicyViolationError) | Ad copy / creative violates Google policy | Inspect `details.policyViolationKey`; rewrite text. Some violations are exemptable via `policy_validation_parameter.ignorable_policy_topics` on the operation |
| `RESOURCE_EXHAUSTED` | Daily op quota or per-second QPS exceeded | Exponential backoff; reduce QPS; check access level (Basic = 15k ops/day) |
| `OPERATION_NOT_PERMITTED_FOR_REMOVED_RESOURCE` | Operating on a tombstoned record | Check `status` first; re-create instead |
| `CANNOT_REMOVE_BUDGET_USED_BY_CAMPAIGN` | Budget still attached | Remove or repoint the campaign first |
| `BIDDING_STRATEGY_NOT_SUPPORTED_FOR_CHANNEL_TYPE` | e.g. `manualCpc` on PMax | Use a strategy compatible with the channel |
| `ASSET_LINK_REQUIRED_ASSET_FIELD_TYPES_MISSING` | PMax asset group below minimums | Add the missing field types in the same `googleAds:mutate` request |
| `CRITERION_DUPLICATED` | Same keyword + matchType already exists in the ad group | Skip or remove the existing one first |

When a request fails atomically (default `partialFailure: false`), NOTHING was written, even ops that look fine in your batch. Re-submit the corrected batch.

---

## 7. Safe mutation patterns

### 7.1 Always validate first

For any non-trivial change, run the **exact** request body once with `validateOnly: true`. The server applies the same validation pipeline (field shape, enum values, policy, dependency checks) without persisting. If it returns success, flip the flag and resubmit.

```json
{ "operations": [...], "validateOnly": true }
```

This catches ~95% of mistakes and costs effectively nothing.

### 7.2 When to use `partialFailure: true`

Use it when:
- You're bulk-importing (e.g. 200 keywords) and want the good ones in even if a few are duplicates.
- You're doing maintenance ops (e.g. pausing 50 ad groups) where the rest shouldn't fail because one is already removed.

Don't use it when:
- Operations are dependent on each other (a failed parent leaves orphans).
- You want strict atomicity (e.g. budget + campaign creation should be all-or-nothing).

With `partialFailure: true`, the response body has `partialFailureError.details[].googleAdsFailure` and the failing op's index in `errors[].location.fieldPathElements[index]`. Successful ops have populated results, failed ops have empty result objects at the same index.

### 7.3 Batch within a single mutate

Each resource-specific endpoint accepts up to **10,000 operations per request**. Group operations of the same kind (e.g. 500 keywords) into one call. The per-request HTTP overhead is significant; batching reduces wall-clock time by an order of magnitude.

### 7.4 `googleAds:mutate` for cross-resource transactions

Use the bulk endpoint when you need atomic creation of a graph of resources that reference each other:

- New campaign + budget + ad group + ad
- New PMax campaign + asset group + assets + asset_group_assets
- Pause ad group + remove all its keywords

Wrap each operation in the typed wrapper (`campaignOperation`, `adGroupOperation`, `adGroupAdOperation`, `assetOperation`, `assetGroupOperation`, `assetGroupAssetOperation`, `conversionActionOperation`, `campaignCriterionOperation`, `adGroupCriterionOperation`, `campaignBudgetOperation`, `biddingStrategyOperation`, etc.). Group same-type operations contiguously - the server batches consecutive same-type ops; interleaving multiplies internal RPCs and risks timeouts.

Use **negative-ID temporary resource names** (`customers/{cid}/campaignBudgets/-1`) to forward-reference resources created in the same request:

```json
{
  "mutateOperations": [
    {
      "campaignBudgetOperation": {
        "create": {
          "resourceName": "customers/{CID}/campaignBudgets/-1",
          "name": "Auto budget",
          "amountMicros": "5000000",
          "deliveryMethod": "STANDARD"
        }
      }
    },
    {
      "campaignOperation": {
        "create": {
          "resourceName": "customers/{CID}/campaigns/-2",
          "name": "Atomic Search Campaign",
          "advertisingChannelType": "SEARCH",
          "status": "PAUSED",
          "manualCpc": {},
          "campaignBudget": "customers/{CID}/campaignBudgets/-1"
        }
      }
    },
    {
      "adGroupOperation": {
        "create": {
          "resourceName": "customers/{CID}/adGroups/-3",
          "name": "Brand AG",
          "campaign": "customers/{CID}/campaigns/-2",
          "type": "SEARCH_STANDARD",
          "cpcBidMicros": "1000000"
        }
      }
    }
  ],
  "partialFailure": false,
  "validateOnly": true
}
```

Rules for temporary names:
- Each negative ID must be unique across the entire request, including across resource types.
- Define before reference (the budget must come before the campaign that uses it).
- Names are local to the request - they don't survive into later requests.

### 7.5 Response shape

Resource-specific mutate response (default):

```json
{
  "results": [
    { "resourceName": "customers/{CID}/campaignBudgets/123" },
    { "resourceName": "customers/{CID}/campaignBudgets/124" }
  ]
}
```

`googleAds:mutate` response:

```json
{
  "mutateOperationResponses": [
    { "campaignBudgetResult": { "resourceName": "..." } },
    { "campaignResult": { "resourceName": "..." } },
    { "adGroupResult": { "resourceName": "..." } }
  ],
  "partialFailureError": null
}
```

### 7.6 Idempotency and retries

Mutate is NOT idempotent by default - sending `create` twice creates two resources (or one + a duplicate-name error). For at-least-once delivery you need:
- Application-level dedup (check by name first via search).
- `partialFailure: true` + tolerate `DUPLICATE_NAME` as success.
- Rolling per-day suffixes in names for safe re-runs.

For transient errors (`UNAVAILABLE`, `DEADLINE_EXCEEDED`, `INTERNAL`), retry with exponential backoff: 1s, 2s, 4s, 8s, capped, with jitter. Never retry on `INVALID_ARGUMENT`, `FAILED_PRECONDITION`, or `PERMISSION_DENIED` - those need code/config fixes.

---

## 8. Rate limits and quotas

### 8.1 Per-request limits

- **10,000 operations per `:mutate` request**. Exceeding => `TOO_MANY_MUTATE_OPERATIONS`.
- **Some services cap at 100 ops** (action-type ops). Exceeding => `TOO_MANY_ACTION_OPERATIONS`.
- **gRPC response payload max 64 MB**. Big lists with `responseContentType: MUTABLE_RESOURCE` can blow this.

### 8.2 Daily operation quotas (per developer token)

Each `:mutate` operation in the `operations` array counts as one operation. Each `Search` query also counts as one. Sums across all customer IDs accessible via the token.

| Access level | Daily ops |
|---|---|
| Test (test accounts only) | 15,000 |
| Basic | 15,000 |
| Standard | Unlimited (subject to system rate limits) |

Hitting the daily cap returns `RESOURCE_EXHAUSTED` (gRPC code 8 / HTTP 429) until UTC midnight rollover.

### 8.3 Per-second QPS

Google enforces token-bucket rate limiting per (developer_token, customer_id) pair. There is no published fixed QPS - it varies with overall server load. Practical guidance:
- Plan for ~5-10 sustained QPS per customer ID for normal mutates.
- Specialty services have explicit caps: `KeywordPlanIdeaService` 1 QPS, `AudienceInsightsService` 2 QPS.
- On `RESOURCE_EXHAUSTED` mid-day (i.e. not the daily cap), implement exponential backoff. The bucket refills.

### 8.4 Backoff strategy

```
attempt 1: send
on 429 / RESOURCE_EXHAUSTED -> sleep 1s + jitter
attempt 2: send
on 429 -> sleep 2s + jitter
...
cap at 60s, max 6 attempts
```

Don't poll-spam. Respect `Retry-After` headers if present.

---

## Quick reference - safe mutate checklist for an LLM

Before submitting any mutate:

1. Build the JSON body offline.
2. Run with `validateOnly: true`. Read the response. Fix every error.
3. If validate is clean, set `validateOnly: false` and submit.
4. For multi-resource graphs, use `customers/{CID}/googleAds:mutate` with temporary `-N` resource names.
5. Default `status` to `PAUSED` on every newly created campaign and ad. Enable only after verification.
6. Use micros (string-encoded) for every `*Micros` field. Never mix in float currency.
7. On update, build `updateMask` with exactly the fields you set in the resource body, lowerCamelCase, comma-separated.
8. Save returned `resourceName` from each create - it's your handle for future updates/removes.
9. Respect 10,000 op cap per request. Page if larger.
10. On `RESOURCE_EXHAUSTED`, exponential backoff. On `INVALID_ARGUMENT`, fix and retry, do not loop.

---

## Sources

- [Mutating Resources Overview](https://developers.google.com/google-ads/api/docs/mutating/overview)
- [Mutate request structure](https://developers.google.com/google-ads/api/rest/common/mutate)
- [Mutate Best Practices](https://developers.google.com/google-ads/api/docs/mutating/best-practices)
- [Bulk Mutates (`googleAds:mutate`)](https://developers.google.com/google-ads/api/docs/mutating/bulk-mutate)
- [MutateOperation reference](https://developers.google.com/google-ads/api/rest/reference/rest/v20/MutateOperation)
- [Resource Names](https://developers.google.com/google-ads/api/rest/design/resource-names)
- [JSON Mappings](https://developers.google.com/google-ads/api/rest/design/json-mappings)
- [Create Campaign Budgets](https://developers.google.com/google-ads/api/docs/campaigns/budgets/create-budgets)
- [Create Campaigns](https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns)
- [Create Responsive Search Ads](https://developers.google.com/google-ads/api/docs/responsive-search-ads/create-responsive-search-ads)
- [PMax Asset Groups](https://developers.google.com/google-ads/api/performance-max/asset-groups)
- [PMax Create Campaign Criteria](https://developers.google.com/google-ads/api/performance-max/create-campaign-criteria)
- [Add Campaign Targeting Criteria](https://developers.google.com/google-ads/api/samples/add-campaign-targeting-criteria)
- [Upload Image Asset](https://developers.google.com/google-ads/api/samples/upload-image-asset)
- [Create Conversion Actions](https://developers.google.com/google-ads/api/docs/conversions/create-conversion-actions)
- [Asset creation and usage](https://developers.google.com/google-ads/api/docs/assets/working-with-assets)
- [Field Masks](https://developers.google.com/google-ads/api/docs/client-libs/python/field-masks)
- [Handle API errors](https://developers.google.com/google-ads/api/docs/get-started/handle-errors)
- [Common Errors](https://developers.google.com/google-ads/api/docs/common-errors)
- [API Limits and Quotas](https://developers.google.com/google-ads/api/docs/best-practices/quotas)
- [Rate Sheet](https://developers.google.com/google-ads/api/docs/api-policy/rate-sheet)
- [v20 Release Announcement (June 2025)](https://ads-developers.googleblog.com/2025/06/announcing-v20-of-google-ads-api.html)
