---
name: campaign-management
description: Pause, resume, rename, edit and remove Google Ads campaigns; manage campaign-level settings (network targeting, geo, language, ad rotation, ad schedule). For CREATING a NEW campaign, hand off to the channel-specific guided wizards - pmax-campaign-builder for PMax, search-campaign-builder for Search. Use this skill for "pause campaign X", "enable campaign", "rename campaign", "change network settings", "add geo X to campaign Y", "change campaign status". For budget changes use budget-bidding; for keywords use keyword-operations.
---

# Campaign management

Edit existing campaigns and their settings. **For creating NEW campaigns, ALWAYS use the guided wizards** - they interview the user and prevent missing required fields:

- **Performance Max** -> [pmax-campaign-builder](../pmax-campaign-builder/SKILL.md)
- **Search** -> [search-campaign-builder](../search-campaign-builder/SKILL.md)
- **Other channels** (Display, Demand Gen, Video, Shopping): no dedicated wizard yet - interview the user manually using the same pattern (basics → goal → bidding → assets → preview → validate-only → apply).

**Never assume defaults silently.** Ask the user, propose defaults, let them confirm.

## Always-do safety checklist

Before ANY mutation:

1. **Confirm intent** - read back what you're about to do, especially for create/remove
2. **Validate first** - run with `validate_only=true`, fix any errors, then run for real
3. **Single account at a time** - never apply the same change to multiple customer_ids without explicit ask
4. **Status REMOVED is permanent** - cannot be reversed; prefer PAUSED unless user explicitly says delete

## Common operations

### Pause a campaign

```python
import sys; sys.path.insert(0, '.')
from lib import GoogleAdsClient
c = GoogleAdsClient()
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "status": "PAUSED",
    },
    "updateMask": "status",
}]
print(c.mutate_resource(CUSTOMER_ID, "campaigns", ops))
```

### Resume (re-enable) a campaign

Same as pause but `"status": "ENABLED"`.

### Rename

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "name": "New name",
    },
    "updateMask": "name",
}]
```

### Remove

```python
ops = [{"remove": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID)}]
```
WARNING: irreversible; campaign is gone (entity itself, not its history).

### Create a Search campaign with a budget (two-step batch)

A campaign requires a budget. Either reference an existing budget, or create both in one batched mutate using temporary IDs.

```python
import sys; sys.path.insert(0, '.')
from lib import GoogleAdsClient
c = GoogleAdsClient()
CUSTOMER_ID = "1234567890"

mutate_ops = [
    {
        "campaignBudgetOperation": {
            "create": {
                "resourceName": f"customers/{CUSTOMER_ID}/campaignBudgets/-1",
                "name": "Budget for new campaign",
                "amountMicros": str(c.micros(50)),  # 50 in account currency / day
                "deliveryMethod": "STANDARD",
                "explicitlyShared": False,
            }
        }
    },
    {
        "campaignOperation": {
            "create": {
                "name": "New search campaign",
                "advertisingChannelType": "SEARCH",
                "status": "PAUSED",  # always start paused
                "manualCpc": {"enhancedCpcEnabled": False},  # or use targetSpend, maximizeConversions, etc.
                "campaignBudget": f"customers/{CUSTOMER_ID}/campaignBudgets/-1",
                "networkSettings": {
                    "targetGoogleSearch": True,
                    "targetSearchNetwork": True,
                    "targetContentNetwork": False,
                    "targetPartnerSearchNetwork": False,
                },
            }
        }
    },
]
print(c.mutate_batch(CUSTOMER_ID, mutate_ops, validate_only=True))  # always test first
```

The negative resource name (`-1`) is a temporary ID - the second op references the not-yet-created budget. After validate passes, run again with `validate_only=False`.

### Create a Performance Max campaign

For PMax always use the guided wizard: [pmax-campaign-builder](../pmax-campaign-builder/SKILL.md). It walks the user through asset groups, headlines, images, audience signals, listing groups, etc. - all the things you'd otherwise miss.

### Edit network targeting

```python
ops = [{
    "update": {
        "resourceName": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "networkSettings": {
            "targetGoogleSearch": True,
            "targetSearchNetwork": False,  # disable search partners
            "targetContentNetwork": False,
            "targetPartnerSearchNetwork": False,
        },
    },
    "updateMask": "network_settings.target_search_network,network_settings.target_content_network",
}]
```

The `updateMask` MUST list every field you set. Path is the snake_case path to the field.

## Geo and language targeting

These are `campaign_criterion` resources (not on the campaign itself). See:
- Add geo target: criterion `location` with `geo_target_constant`
- Add language: criterion `language` with `language_constant`
- Negative geo: `negative: true` on the criterion

```python
geo_ops = [{
    "create": {
        "campaign": c.resource_name(CUSTOMER_ID, "campaigns", CAMPAIGN_ID),
        "location": {"geoTargetConstant": "geoTargetConstants/2203"},  # 2203 = Czech Republic
        "status": "ENABLED",
    }
}]
print(c.mutate_resource(CUSTOMER_ID, "campaignCriteria", geo_ops))
```

Useful geo target constants (Slovakia=2703, Czech Republic=2203, Germany=2276, Austria=2040, Hungary=2348, Poland=2616, USA=2840, UK=2826).

## Bidding strategy

Inline bidding strategies (set on campaign):
- `manualCpc: {}` - manual CPC
- `targetSpend: {targetSpendMicros: ..., cpcBidCeilingMicros: ...}` - max clicks
- `targetCpa: {targetCpaMicros: ...}` - target CPA
- `targetRoas: {targetRoas: 4.0}` - target ROAS
- `maximizeConversions: {targetCpaMicros?: ...}` - max conversions
- `maximizeConversionValue: {targetRoas?: ...}` - max conv value

When changing bidding strategy via update, set ONLY the new strategy field and update_mask = that field. The old strategy is replaced.

## Reference

- Full mutation reference: [reference/mutations-guide.md](../../reference/mutations-guide.md)
- Campaign field catalog: [reference/resources-catalog.md](../../reference/resources-catalog.md#campaign)
- Errors specific to mutations: [reference/errors-handbook.md](../../reference/errors-handbook.md#mutation-errors)
