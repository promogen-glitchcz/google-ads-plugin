---
name: change-history
description: Audit recent changes in the Google Ads account - who changed what and when, suspicious recent edits, before/after values. Use for "show recent changes", "what changed yesterday/this week", "audit log", "who edited campaign X", "find risky recent changes", "rollback last change" (note - rollback is manual).
---

# Change history

The `change_event` resource is Google Ads' audit log. Visibility window: last 30 days.

## Basic recent changes query

```sql
SELECT change_event.change_date_time,
       change_event.user_email,
       change_event.client_type,
       change_event.change_resource_type,
       change_event.change_resource_name,
       change_event.changed_fields,
       change_event.old_resource,
       change_event.new_resource,
       change_event.resource_change_operation
FROM change_event
WHERE change_event.change_date_time >= '2026-04-01 00:00:00'
ORDER BY change_event.change_date_time DESC
LIMIT 500
```

Note: `change_event` requires a date filter (`change_date_time` >= some recent timestamp), and a LIMIT. The window is hard-capped to 30 days.

## What `change_event` returns

- `change_date_time` - server timestamp
- `user_email` - who did it (UI user, API user, or system if Google's automation)
- `client_type` - GOOGLE_ADS_WEB_CLIENT, GOOGLE_ADS_API, GOOGLE_ADS_EDITOR, GOOGLE_ADS_MOBILE_APP, GOOGLE_ADS_AUTOMATED_RULE, etc.
- `change_resource_type` - CAMPAIGN, AD_GROUP, AD_GROUP_AD, AD_GROUP_CRITERION, CAMPAIGN_CRITERION, CAMPAIGN_BUDGET, AD_GROUP_BID_MODIFIER, ASSET, etc.
- `change_resource_name` - the resource that was changed
- `changed_fields` - field mask of what changed
- `old_resource` / `new_resource` - the snapshots; can be diffed
- `resource_change_operation` - CREATE / UPDATE / REMOVE

## Common timeframes

```sql
WHERE change_event.change_date_time DURING LAST_7_DAYS
WHERE change_event.change_date_time DURING TODAY
WHERE change_event.change_date_time DURING YESTERDAY
WHERE change_event.change_date_time BETWEEN '2026-04-01 00:00:00' AND '2026-04-30 23:59:59'
```

## Filter by user

```sql
WHERE change_event.change_date_time DURING LAST_7_DAYS
  AND change_event.user_email = 'someone@example.com'
```

## Filter by resource type

```sql
WHERE change_event.change_date_time DURING LAST_7_DAYS
  AND change_event.change_resource_type = 'CAMPAIGN_BUDGET'
```

## Spot risky recent changes

Things to flag:
- Budget increases >30% on a single campaign in the last 7 days
- Bidding strategy changes (UPDATE on campaign, changed_fields contains a bidding strategy field)
- Ad-group cpc_bid_micros increases
- New campaigns going from PAUSED to ENABLED late at night
- Mass removes (REMOVE operations clustered in time)

These all come from the same query above filtered/grouped in Python.

## Before/after diff

`old_resource` and `new_resource` are JSON strings of the partial resource snapshot. Diff:
```python
import json
def diff(old: str, new: str):
    o = json.loads(old or "{}")
    n = json.loads(new or "{}")
    keys = set(o) | set(n)
    return [{"field": k, "old": o.get(k), "new": n.get(k)} for k in keys if o.get(k) != n.get(k)]
```

## Rollback

The API has no automatic rollback. To revert:
1. Find the change_event for the resource
2. Read `old_resource`
3. Construct an `update` mutation that sets each field back to the old value
4. Run with `validate_only=True` first

For REMOVE operations, you cannot undo - the resource must be re-created.

## Limitations

- Visibility: 30 days max (older history not accessible via API)
- Granularity: not every Google internal optimization is logged here. Auto-applied recommendations show as `client_type=GOOGLE_ADS_RECOMMENDATIONS_AUTO_APPLY`.
- For PMax asset group changes, `change_resource_type` is `ASSET_GROUP`, etc.

## Reference
- [reference/gaql-cookbook.md](../../reference/gaql-cookbook.md#change-events)
