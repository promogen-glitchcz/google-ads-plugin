# Google Ads API - Overview

## Versioning (May 2026)

Google moved to a **monthly** release cadence in January 2026. Versions are supported ~14 months.

| version | released | sunset |
|---|---|---|
| v20 | Jun 2025 | **Jun 10, 2026** (~5 weeks after May 2026) |
| v21 | Aug 2025 | ~Oct 2026 |
| v22 | Nov 2025 | ~Jan 2027 |
| v23 | Jan 28, 2026 | ~Mar 2027 |
| v23.1 | Feb 25, 2026 | (minor; tracks v23) |

This plugin targets **v20** by default. To use a newer version, set in `.secrets/.env`:
```
GOOGLE_ADS_API_VERSION=v23
```

## Endpoint base

```
https://googleads.googleapis.com/{version}
```

## Required headers (every API call)

```
Authorization: Bearer {ACCESS_TOKEN}
developer-token: {22_CHAR_DEVELOPER_TOKEN}
Content-Type: application/json
login-customer-id: {MANAGER_ID}   # only when querying via MCC
```

`login-customer-id`:
- digits only, no hyphens
- needed when authentication is via a manager and operating customer is a sub-account
- ignored / forbidden on `customers:listAccessibleCustomers`
- omit when operating customer == authenticated user's direct account

## Read endpoints

```
POST /{v}/customers/{customer_id}/googleAds:search
POST /{v}/customers/{customer_id}/googleAds:searchStream
GET  /{v}/customers:listAccessibleCustomers
```

| | search | searchStream |
|---|---|---|
| body | `{"query": "...", "pageSize": 10000, "pageToken": "..."}` | `{"query": "..."}` (no pageSize/pageToken) |
| response | `{"results": [...], "nextPageToken": "...", "fieldMask": "..."}` | streamed JSON array of chunks, each with `results` |
| best for | UI paging | bulk pulls |

Default in this plugin: `searchStream` via `client.search()`. For paginated reads use `client.search_paginated()`.

## Mutate endpoints

```
POST /{v}/customers/{customer_id}/{resource_plural}:mutate     # single-resource batch
POST /{v}/customers/{customer_id}/googleAds:mutate              # cross-resource batch
```

The batch endpoint accepts up to 10,000 operations and supports **temporary IDs** (negative numbers) so you can reference resources created earlier in the same batch.

Body shape (single-resource):
```json
{
  "operations": [{"create|update|remove": {...}, "updateMask": "field1,field2"}],
  "validateOnly": false,
  "partialFailure": false,
  "responseContentType": "RESOURCE_NAME_ONLY"
}
```

## OAuth scopes

The Google Ads API needs exactly:
```
https://www.googleapis.com/auth/adwords
```

For the OAuth flow itself: redirect URI must be on the OAuth client's authorized list. This plugin's setup wizard uses `http://localhost:8765`.

## GAQL essentials

```
SELECT field1, field2, metrics.X, segments.Y
FROM resource
WHERE condition AND condition
ORDER BY metrics.X DESC
LIMIT N
```

Six clauses, in this order: SELECT, FROM, WHERE, ORDER BY, LIMIT, PARAMETERS. No JOIN, no GROUP BY, no UNION. One resource in FROM.

Field categories:
- **resource attributes**: `campaign.id`, `ad_group.name`
- **metrics**: `metrics.cost_micros`, `metrics.conversions`
- **segments**: `segments.date`, `segments.device`

When you SELECT a date segment, you MUST also filter it in WHERE. Adding any segment splits each row by that segment.

## Customer ID rules

- Always strip dashes: `123-456-7890` -> `1234567890`
- Always 10 digits
- Operating customer (URL path) = the account whose data you want
- Login customer (header) = the manager you authenticate through, if any

## Money

All money fields end in `_micros`. Divide by 1,000,000 for display. The lib helpers `c.micros(amount)` and `c.from_micros(value)` handle this.

## Pitfalls

- Selecting a date segment without a WHERE filter on it -> error
- Querying historical data without `... AND <resource>.status != 'REMOVED'` -> includes removed entities
- Using PHRASE-like patterns in `LIKE`: `%` and `_` are wildcards; escape with brackets `[%]`
- `change_event` requires `change_event.change_date_time` filter and is capped at 30 days
- `click_view` requires single-day filter and 90-day max history
- Period segments (week/month/quarter) require the FIRST DAY of the period

## Authentication errors at a glance

| error | what it means |
|---|---|
| `unauthorized_client` (OAuth2) | refresh_token doesn't match client_id/secret |
| `invalid_grant` | refresh_token revoked or expired |
| `AUTHENTICATION_ERROR` (Google Ads) | access token rejected |
| `DEVELOPER_TOKEN_NOT_APPROVED` | developer token not whitelisted for production traffic |
| `USER_PERMISSION_DENIED` | account user has no access to that customer |
| `MISSING_LOGIN_CUSTOMER_ID` | needed login-customer-id header but didn't send it |

Full guide: [errors-handbook.md](errors-handbook.md)

## Sources
- https://developers.google.com/google-ads/api/docs/concepts/call-structure
- https://developers.google.com/google-ads/api/docs/query/overview
- https://developers.google.com/google-ads/api/rest/common/search
