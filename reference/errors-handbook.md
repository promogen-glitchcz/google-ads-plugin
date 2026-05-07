# Google Ads API Reference Doc

A reliability-focused reference for Google Ads API v20 (and adjacent versions v21-v23) covering authentication, rate limits, error handling, and operational best practices. Built for LLM-driven diagnosis and recovery.

> **Version status as of May 2026**
> - **v23** is the current latest version (released Jan 28, 2026 - monthly cadence kicked in)
> - **v20** sunsets **June 10, 2026** - migrate to v21 or higher before then
> - **v21** ships in monthly cadence (around Feb 2026), **v22** (Mar 2026), **v23** (Apr 2026 minor releases)
> - Each major version is supported for ~14 months from release

---

## 1. OAuth 2.0 Flow for Google Ads API

### Required scope
The Google Ads API requires exactly one OAuth scope:

```
https://www.googleapis.com/auth/adwords
```

This single scope governs all read/write access to the Google Ads API. There is no per-resource scope subdivision.

### The four credentials you need

To call the API, you assemble four pieces:

| Credential | Source | Purpose |
|------------|--------|---------|
| `client_id` | Google Cloud Console (OAuth 2.0 Client ID) | Identifies your application |
| `client_secret` | Google Cloud Console (paired with client_id) | Authenticates your application |
| `developer_token` | Google Ads UI: Tools and Settings -> API Center | Authenticates your developer organization |
| `refresh_token` | OAuth consent flow (one-time) | Long-lived credential that mints access tokens |

The `client_id` + `client_secret` form one inseparable pair issued from a single Google Cloud OAuth client. The `refresh_token` is **bound to that exact client_id+client_secret pair plus the consenting Google account plus the scope**. You cannot mix and match: a refresh token issued under client A will not work with client B's secret.

### Step-by-step provisioning

1. **Get a developer token**
   - Sign in to a **Google Ads manager account** (a regular ad-spending account does not qualify; you must convert it or create an MCC).
   - Tools and Settings -> Setup -> API Center -> request a token.
   - Initial token starts in **Test Access** state (sandbox-only, see section 7).

2. **Create OAuth client_id + client_secret**
   - Go to https://console.cloud.google.com/ -> APIs and Services -> Credentials.
   - Create OAuth 2.0 Client ID (Type: Desktop app for CLI tools, or Web application for hosted apps).
   - Configure the **OAuth consent screen** before issuing the client.
   - For an external user type and "Testing" publishing status, refresh tokens expire in **7 days**. Set the consent screen to **"In production"** for non-expiring refresh tokens.

3. **Run the consent flow to mint a refresh_token**
   - Send the user to:
     ```
     https://accounts.google.com/o/oauth2/v2/auth
       ?client_id=CLIENT_ID
       &redirect_uri=REDIRECT_URI
       &response_type=code
       &scope=https://www.googleapis.com/auth/adwords
       &access_type=offline
       &prompt=consent
     ```
   - `access_type=offline` is mandatory to receive a refresh token. For desktop apps, it is implicit; for web apps, it is explicit.
   - `prompt=consent` forces a fresh refresh token even if previously consented.
   - Exchange the returned `code` at `https://oauth2.googleapis.com/token`:
     ```
     POST https://oauth2.googleapis.com/token
     Content-Type: application/x-www-form-urlencoded
     code=AUTH_CODE
     &client_id=CLIENT_ID
     &client_secret=CLIENT_SECRET
     &redirect_uri=REDIRECT_URI
     &grant_type=authorization_code
     ```
   - Response body contains `refresh_token` (store securely) and `access_token` (use for ~1 hour).

### Refresh token expiration rules

| Project state | Refresh token TTL |
|---------------|-------------------|
| OAuth consent screen = **Testing**, External user type | **7 days** |
| OAuth consent screen = **In production** | **No expiration** (subject to revocation rules) |
| Internal-user-type project (Workspace) | No expiration |

A non-expiring refresh token can still be invalidated by:
- User revoking access at https://myaccount.google.com/permissions
- Token unused for **6 months**
- User changes password (only affects Gmail-scope tokens; Ads-scope is unaffected)
- 50-token-per-user-per-client cap exceeded - oldest token auto-revoked
- Google Cloud project deleted, OAuth client deleted, or scope changes

### access_token lifetime and refresh

`access_token` lives for **3600 seconds (1 hour)**. To refresh:

```
POST https://oauth2.googleapis.com/token
Content-Type: application/x-www-form-urlencoded
client_id=CLIENT_ID
&client_secret=CLIENT_SECRET
&refresh_token=REFRESH_TOKEN
&grant_type=refresh_token
```

Response: `{"access_token": "...", "expires_in": 3599, "token_type": "Bearer"}`

Cache the access_token; refresh proactively at ~55 minutes. Do not refresh on every request - it is rate limited at the OAuth endpoint and contributes to the 50-token-per-user-per-client cap.

### Common OAuth errors at the token endpoint

These errors come from `oauth2.googleapis.com/token`, not from the Ads API itself.

| Error | HTTP | Meaning | Fix |
|-------|------|---------|-----|
| `invalid_grant` | 400 | Refresh token expired/revoked, auth code reused, redirect_uri mismatch, or clock skew | Re-run consent flow to mint new refresh_token. Check system clock. |
| `invalid_client` | 401 | client_id or client_secret wrong, or wrong auth method (Basic header vs form body) | Verify both values from Google Cloud Console. The error message often says "The OAuth client was not found." |
| `unauthorized_client` | 400 | Client recognized but not allowed to use this grant type | Check OAuth client type (Desktop vs Web vs Service Account). Service accounts cannot use refresh_token grant. |
| `invalid_request` | 400 | Missing required parameter | Check `grant_type`, `refresh_token`, `client_id`, `client_secret` are all present. |
| `invalid_scope` | 400 | Scope not authorized for client | Make sure the scope is exactly `https://www.googleapis.com/auth/adwords`. |
| `access_denied` | 403 | User declined consent | User must approve in OAuth screen. |

---

## 2. Request Authentication Headers

Every Google Ads API request requires three headers (sometimes four):

```
Authorization: Bearer ya29.a0Af...   <- the access_token
developer-token: ABCdef1234ghIjkl56789mn   <- 22-char alphanumeric
login-customer-id: 1234567890   <- digits only, no dashes; required when using a manager
Content-Type: application/json   <- for REST calls
```

### When `login-customer-id` is required

- **Required**: when you make a request **on behalf of** a client account through a manager account hierarchy. Set it to the **MCC's customer ID** (10-digit, dashes stripped). The `customer_id` in the URL path stays as the **child** account.
- **Required**: when you call any service while authenticated via a Google account that has access only through MCC linkage rather than direct user permission.
- **Not required**: direct calls against an account where the authenticated user has direct user access.
- **Ignored**: by `customers.listAccessibleCustomers` - that endpoint always returns the accounts the OAuth user has direct access to, regardless of `login-customer-id`.

If you set `login-customer-id` to an MCC that does not actually manage the target customer in the URL path, you get `USER_PERMISSION_DENIED`.

### Customer ID formatting rules

- Strip all dashes: `123-456-7890` -> `1234567890`.
- Always 10 digits. Leading zeros allowed (rare but possible).
- Do not URL-encode.
- Wrong format triggers `INVALID_CUSTOMER_ID` or `CLIENT_CUSTOMER_ID_INVALID`.

---

## 3. API Quotas and Rate Limits

### Daily operation quotas by access level

| Access level | Production accounts | Test accounts | Monthly spend cap |
|--------------|---------------------|---------------|-------------------|
| **Test Account** | Cannot call production accounts | Unlimited | N/A |
| **Explorer Access** | 2,880 ops/day | 15,000 ops/day | $15,000 across all managed accounts |
| **Basic Access** | 15,000 ops/day | 15,000 ops/day | $15,000/month |
| **Standard Access** | Unlimited (subject to QPS) | 15,000 ops/day | No spending cap |

**Operation counting rules**:
- Each `mutate` operation in a request body counts as 1 op (so a `MutateAdGroupsRequest` with 50 operations = 50 ops).
- A `Search` or `SearchStream` request counts as **1 operation** regardless of how many rows are returned or how many pages are traversed (paginated follow-up requests with a valid page token do not count).
- Failed requests that return a `GoogleAdsFailure` still consume quota.
- Network-level failures (timeout, connection refused) do not consume quota.

### Per-request limits

| Limit | Value | Error |
|-------|-------|-------|
| Mutate operations per request | 10,000 | `TOO_MANY_MUTATE_OPERATIONS` |
| Action operations per request | 100 | `TOO_MANY_ACTION_OPERATIONS` |
| gRPC response size | 64 MB | `RESOURCE_EXHAUSTED` (gRPC 429) |
| Conversion uploads per request | 2,000 | `TOO_MANY_CONVERSIONS_IN_REQUEST` |
| Conversion adjustments per request | 2,000 | `TOO_MANY_ADJUSTMENTS_IN_REQUEST` |
| User identifiers per UserData | 20 | `TOO_MANY_USER_IDENTIFIERS` |
| Keyword Plan / forecast methods | 1 QPS | `RESOURCE_EXHAUSTED` |

### QPS and throttling

The API uses a **token bucket algorithm** scoped to **(developer token, customer ID)**. Effective QPS limit varies with overall server load - there is no published fixed number for non-Planning services. 1 QPS in the docs means 60 requests over a rolling 60-second window.

### Detecting throttling

Three error codes indicate rate limit hits:

| Error code | gRPC code | HTTP | Meaning |
|------------|-----------|------|---------|
| `RESOURCE_EXHAUSTED` | 8 | 429 | Daily quota exceeded or per-request size cap blown |
| `RESOURCE_TEMPORARILY_EXHAUSTED` | 8 | 429 | Short-term QPS spike, retry shortly |
| `QuotaError.ACCESS_PROHIBITED` | - | - | Token suspended pending review |

The gRPC status detail will contain a `QuotaError` enum and may include a `RetryDelay` value indicating suggested wait time.

### Backoff strategy (recommended)

```
attempt 1: immediate
attempt 2: wait 2s + jitter
attempt 3: wait 4s + jitter
attempt 4: wait 8s + jitter
attempt 5: wait 16s + jitter
attempt 6: wait 32s + jitter (cap)
```

Max retries: **5**. Add jitter of `random(0, 1000)ms` to avoid thundering herd. Stop retrying on:
- `RESOURCE_EXHAUSTED` with daily quota error -> wait until midnight Pacific time.
- Any non-retryable error code (`INVALID_ARGUMENT`, `PERMISSION_DENIED`, `FAILED_PRECONDITION`, `NOT_FOUND`, `ALREADY_EXISTS`, `OUT_OF_RANGE`).

Retryable codes: `UNAVAILABLE` (14), `DEADLINE_EXCEEDED` (4), `INTERNAL` (13), `RESOURCE_TEMPORARILY_EXHAUSTED`, transient `RESOURCE_EXHAUSTED`.

---

## 4. Error Response Structure

### The Status object (Google's standard API error format)

When a request fails, the API returns a `google.rpc.Status` with three fields:

```json
{
  "error": {
    "code": 400,
    "message": "Request contains an invalid argument.",
    "status": "INVALID_ARGUMENT",
    "details": [
      {
        "@type": "type.googleapis.com/google.ads.googleads.v20.errors.GoogleAdsFailure",
        "errors": [...],
        "requestId": "abc123XYZ-_=="
      }
    ]
  }
}
```

### gRPC status code mapping

| code | name | HTTP | retryable? |
|------|------|------|-----------|
| 3 | `INVALID_ARGUMENT` | 400 | No |
| 4 | `DEADLINE_EXCEEDED` | 504 | Yes |
| 5 | `NOT_FOUND` | 404 | No |
| 6 | `ALREADY_EXISTS` | 409 | No |
| 7 | `PERMISSION_DENIED` | 403 | No |
| 8 | `RESOURCE_EXHAUSTED` | 429 | Sometimes |
| 9 | `FAILED_PRECONDITION` | 400 | No |
| 13 | `INTERNAL` | 500 | Yes |
| 14 | `UNAVAILABLE` | 503 | Yes |
| 16 | `UNAUTHENTICATED` | 401 | After token refresh |

### GoogleAdsFailure proto

`GoogleAdsFailure` lives in `Status.details` as a packed `Any` message:

```proto
message GoogleAdsFailure {
  repeated GoogleAdsError errors = 1;
  string request_id = 2;
}

message GoogleAdsError {
  ErrorCode error_code = 1;       // one-of category, see below
  string message = 2;              // human-readable
  Value trigger = 3;               // the value that caused the failure
  ErrorLocation location = 4;      // field path in your request
  ErrorDetails details = 5;        // policy/violation specifics
}

message ErrorLocation {
  repeated FieldPathElement field_path_elements = 2;
}

message FieldPathElement {
  string field_name = 1;
  optional int32 index = 2;       // for repeated fields
}
```

### error_code one-of (top-level categories)

`GoogleAdsError.error_code` is a single message containing exactly one of ~150 sub-error enums. The most common categories you will diagnose:

- `authentication_error` (`AuthenticationError`)
- `authorization_error` (`AuthorizationError`)
- `request_error` (`RequestError`)
- `query_error` (`QueryError`) - GAQL parsing/syntax
- `quota_error` (`QuotaError`)
- `internal_error` (`InternalError`)
- `mutate_error` (`MutateError`)
- `partial_failure_error` (`PartialFailureError`)
- `header_error` (`HeaderError`)
- `customer_error` (`CustomerError`)
- `field_error` (`FieldError`)
- `range_error` (`RangeError`)
- `string_format_error` / `string_length_error`
- `policy_violation_error` (`PolicyViolationError`)
- `id_error`, `null_error`, `not_empty_error`, `not_allowlisted_error`
- `setting_error`, `criterion_error`, `ad_error`, `campaign_error`, `ad_group_error`

The full leaf enum value is the actual diagnostic. Example: `error_code.authentication_error == NOT_ADS_USER`. Always log `error_code` with both the category and the leaf enum.

### error_string mapping examples

```
AuthenticationError.NOT_ADS_USER:
  "User in the cookie is not a valid Ads user."

AuthorizationError.USER_PERMISSION_DENIED:
  "User doesn't have permission to access customer."

AuthorizationError.DEVELOPER_TOKEN_NOT_APPROVED:
  "The developer token is not approved. Non-approved developer tokens
   can only be used with test accounts."

QuotaError.RESOURCE_EXHAUSTED:
  "A system frequency limit has been exceeded."

CustomerError.CUSTOMER_NOT_ENABLED:
  "The customer can't be used because it isn't enabled."

QueryError.UNRECOGNIZED_FIELD:
  "Cannot find the field <name> in the type <resource>."

RequestError.RESOURCE_NAME_MALFORMED:
  "Resource name <name> doesn't match expected format."
```

### Where to find errors per call type

- **Unary REST**: error in HTTP response body under `error.details[]`.
- **gRPC unary**: error in trailing metadata (`grpc-status-details-bin`).
- **gRPC streaming (`SearchStream`)**: error closes the stream with status; check final status before processing buffered rows.
- **Partial failure mode**: errors are in `response.partial_failure_error` (a `Status` proto), and successful results coexist in `response.results[]` - inspect each result's `resource_name` to know which succeeded.
- **Batch jobs**: errors are in each operation's `BatchJobResult` after `BatchJob.status == DONE`.

---

## 5. Top 30 Common Errors and Fixes

### Authentication and authorization

#### 1. `AuthenticationError.NOT_ADS_USER`
- **HTTP**: 401 / `UNAUTHENTICATED`
- **Cause**: Authenticated Google account has never been associated with a Google Ads account.
- **Fix**: Sign in to https://ads.google.com with this account; create or accept invite to an Ads account. Or use a different Google account when minting the refresh token.

#### 2. `AuthenticationError.OAUTH_TOKEN_INVALID`
- **HTTP**: 401
- **Cause**: `Authorization: Bearer ...` token is malformed, expired, or revoked.
- **Fix**: Refresh the access token. If refresh fails with `invalid_grant`, re-run the consent flow.

#### 3. `AuthenticationError.OAUTH_TOKEN_EXPIRED`
- **HTTP**: 401
- **Cause**: Access token past 1-hour TTL.
- **Fix**: Use refresh_token grant to mint a new access_token. Should be automatic in client libraries.

#### 4. `AuthenticationError.OAUTH_TOKEN_REVOKED`
- **HTTP**: 401
- **Cause**: User revoked your app at myaccount.google.com/permissions.
- **Fix**: User must re-authorize. Re-run consent flow.

#### 5. `AuthenticationError.GOOGLE_ACCOUNT_COOKIE_INVALID`
- **HTTP**: 401
- **Cause**: Stale OAuth credentials. Often surfaces after password reset on Gmail-scope tokens (rare for Ads-only tokens).
- **Fix**: Re-run consent flow.

#### 6. `AuthenticationError.DEVELOPER_TOKEN_INVALID`
- **HTTP**: 401
- **Cause**: `developer-token` header has typo, has dashes/spaces, or is missing.
- **Fix**: Copy token verbatim from Ads UI -> API Center. 22 chars, alphanumeric, no separators.

#### 7. `AuthenticationError.ORGANIZATION_NOT_ASSOCIATED_WITH_DEVELOPER_TOKEN`
- **HTTP**: 401
- **Cause**: Developer token belongs to a different Google Cloud project / organization than the OAuth client_id.
- **Fix**: Use the developer token from the manager account whose users own this OAuth client. Or request a new developer token from a manager that matches.

#### 8. `AuthorizationError.DEVELOPER_TOKEN_NOT_APPROVED`
- **HTTP**: 403
- **Cause**: Trying to call a **production** account with a Test Access developer token.
- **Fix**: Either call only test accounts, or apply for Basic/Standard access at the Ads UI and wait for approval. See section 8.

#### 9. `AuthorizationError.DEVELOPER_TOKEN_NOT_WHITELISTED`
- **HTTP**: 403
- **Cause**: Token is not approved for the requested feature/service (legacy phrasing of #8 in some libraries).
- **Fix**: Check approval status in Ads UI -> Tools -> API Center. Submit the API token application form.

#### 10. `AuthorizationError.DEVELOPER_TOKEN_PROHIBITED`
- **HTTP**: 403
- **Cause**: Token is paired with a different Google Cloud project than the one your OAuth credentials originate from.
- **Fix**: Use OAuth credentials from the matching project, or re-pair the token.

#### 11. `AuthorizationError.USER_PERMISSION_DENIED`
- **HTTP**: 403
- **Cause**: Authenticated user does not have access to the customer ID in the URL, OR the wrong (or missing) `login-customer-id` is being used.
- **Fix**: (a) Ensure the user is added to the target Ads account or to a manager that links to it. (b) Set `login-customer-id` to the **highest manager** in the chain that the user has access to. (c) Check the manager-client link is `ACTIVE` not `PENDING`.

#### 12. `AuthorizationError.CUSTOMER_NOT_ENABLED`
- **HTTP**: 403
- **Cause**: Account has not finished signup, billing setup, or has been deactivated/cancelled.
- **Fix**: Sign in to ads.google.com as that customer, complete onboarding, add billing. Check account status.

#### 13. `AuthorizationError.CUSTOMER_NOT_FOUND`
- **HTTP**: 404
- **Cause**: Customer ID does not exist, or has not yet propagated to API backend (just-created accounts can take 5-15 min).
- **Fix**: Verify CID. Strip dashes. Wait a few minutes for new accounts. Check it has not been deleted.

#### 14. `AuthorizationError.LOGIN_CUSTOMER_ID_REQUIRED`
- **HTTP**: 400
- **Cause**: Calling on behalf of a customer through a manager but did not include `login-customer-id` header.
- **Fix**: Set `login-customer-id` to the manager's CID (digits only, no dashes).

#### 15. `HeaderError.INVALID_LOGIN_CUSTOMER_ID`
- **HTTP**: 400
- **Cause**: `login-customer-id` is not a valid CID format, or is not a manager account.
- **Fix**: Use a 10-digit CID without dashes. Verify it is a manager (`customer.manager == true`).

#### 16. `RequestError.INVALID_CUSTOMER_ID`
- **HTTP**: 400
- **Cause**: Customer ID in URL is not a number, has dashes, or has wrong digit count.
- **Fix**: 10 digits, no dashes. `123-456-7890` -> `1234567890`.

#### 17. `HeaderError.REQUEST_HEADER_NOT_ALLOWED`
- **HTTP**: 400
- **Cause**: Provided a header that is not permitted for this endpoint, or header name has a typo (case-sensitive: `developer-token`, lowercase, hyphenated).
- **Fix**: Match the documented header name exactly. Some endpoints (e.g., `listAccessibleCustomers`) reject `login-customer-id`.

#### 18. `RequestError.GRANT_INVALID`
- **HTTP**: 400
- **Cause**: OAuth grant flow problem - usually from `invalid_grant` at the token endpoint bubbling up.
- **Fix**: Refresh token revoked or expired. Re-run consent flow. Verify client_id+client_secret match the original consent.

### Quota and rate limits

#### 19. `QuotaError.RESOURCE_EXHAUSTED`
- **HTTP**: 429
- **Cause**: Daily op cap or per-request size cap hit.
- **Fix**: Wait until quota resets (midnight Pacific). Reduce operations per request. Apply for higher access tier.

#### 20. `QuotaError.RESOURCE_TEMPORARILY_EXHAUSTED`
- **HTTP**: 429
- **Cause**: Short-term QPS spike on the (developer_token, CID) bucket.
- **Fix**: Exponential backoff, then retry. Lower concurrency.

#### 21. `QuotaError.ACCESS_PROHIBITED`
- **HTTP**: 403
- **Cause**: Developer token has been suspended pending review (often after policy violation).
- **Fix**: Check email for Google's notification. Reply with required info or open a case.

### Request validation

#### 22. `QueryError.UNRECOGNIZED_FIELD`
- **HTTP**: 400
- **Cause**: GAQL `SELECT` references a field that does not exist on the resource (or was renamed/removed in this version).
- **Fix**: Check the GAQL Reference for the version. Common gotcha: field renamed between v19 and v20.

#### 23. `QueryError.INVALID_QUERY`
- **HTTP**: 400
- **Cause**: GAQL syntax broken - missing FROM clause, mismatched parens, invalid operator.
- **Fix**: Validate against grammar. Use `SELECT a, b FROM resource WHERE x = 'y' DURING LAST_30_DAYS`.

#### 24. `RequestError.RESOURCE_NAME_MALFORMED`
- **HTTP**: 400
- **Cause**: Resource name does not match the expected pattern, e.g. `customers/123/campaigns/456` is required and you sent `123/456`.
- **Fix**: Use full resource names. Format: `customers/{customer_id}/{resource}/{id}`.

#### 25. `RequestError.RESOURCE_NAME_MISSING`
- **HTTP**: 400
- **Cause**: Update operation did not include the `resource_name` of the entity being updated.
- **Fix**: Set `resource_name` and `update_mask` on update operations.

#### 26. `MutateError.RESOURCE_NOT_FOUND`
- **HTTP**: 404
- **Cause**: Trying to update/remove an entity that does not exist or has been removed.
- **Fix**: Check entity exists with a Search before mutation. Handle race condition with retry.

#### 27. `FieldMaskError.FIELD_HAS_SUBFIELDS`
- **HTTP**: 400
- **Cause**: `update_mask` includes a parent field name when it should specify a leaf, e.g. `bidding` instead of `bidding.target_cpa`.
- **Fix**: Use leaf-only paths in update_mask.

#### 28. `RequestError.INVALID_PAGE_TOKEN`
- **HTTP**: 400
- **Cause**: Page token from previous response is malformed or expired (page tokens are valid for ~1 hour).
- **Fix**: Restart pagination from the first page.

#### 29. `RequestError.TOO_MANY_MUTATE_OPERATIONS`
- **HTTP**: 400
- **Cause**: Single request body has more than 10,000 operations.
- **Fix**: Split into smaller batches.

#### 30. `InternalError.INTERNAL_ERROR`
- **HTTP**: 500
- **Cause**: Backend hiccup, often transient.
- **Fix**: Retry with exponential backoff (max 5 attempts). Persistent failures: log `request_id` and contact Google support.

---

## 6. Manager (MCC) Account Behavior

### Account hierarchy concepts

Google Ads is organized in a tree:
- **Manager (MCC)** account: cannot serve ads, manages others. Has `customer.manager == true`.
- **Client** account: leaf account that runs campaigns.
- An MCC can manage other MCCs (multi-level), up to roughly 6 levels deep in practice.

### When to set `login-customer-id`

Decision tree:
- Is the OAuth user added directly to the target customer? -> **No `login-customer-id` needed**.
- Is the OAuth user only a member of an MCC that links to the target? -> **`login-customer-id` = MCC's CID**.
- Are you traversing many accounts under one MCC (typical agency)? -> Always set `login-customer-id` to that MCC. Treat it as required.
- Calling `customers.listAccessibleCustomers`? -> Header is **ignored**, do not set.

The header tells Google "use this account's role to authorize the request." If the OAuth user has multiple paths to the target, the most-privileged matching path wins.

### `customers.listAccessibleCustomers`

```
GET https://googleads.googleapis.com/v20/customers:listAccessibleCustomers
Headers:
  Authorization: Bearer ...
  developer-token: ...
```

Returns:
```json
{
  "resourceNames": [
    "customers/1234567890",
    "customers/2345678901"
  ]
}
```

**Semantics**:
- Returns customers the **OAuth user has direct access to** - both managers and clients where the user is added as a member. NOT the full hierarchy under those managers.
- `login-customer-id` is ignored.
- Only requires Authorization + developer-token.
- Does not count against operations quota.

### Walking the hierarchy with `customer_client`

The `customer_client` resource virtually represents every account reachable from a given manager. Query it to enumerate the subtree:

```sql
SELECT
  customer_client.client_customer,
  customer_client.id,
  customer_client.descriptive_name,
  customer_client.currency_code,
  customer_client.time_zone,
  customer_client.manager,
  customer_client.level,
  customer_client.status
FROM customer_client
WHERE customer_client.status = 'ENABLED'
  AND customer_client.level <= 2
```

- `level = 0` is the queried account itself.
- `level = 1` is direct child.
- `manager = true` indicates an MCC; recurse into it for full traversal.
- Leaves of the BFS have `manager = false` and represent ad-running customers.

### Linked vs accessible

- **Accessible** = the OAuth user is added to the account (returned by `listAccessibleCustomers`).
- **Linked** = the account is in some MCC subtree (returned by `customer_client` query under that MCC).

A user can be linked through MCC but not directly accessible - this is the agency-managed pattern.

---

## 7. Test Accounts vs Production

### Test accounts

- Created in the Ads UI under a manager account labeled as a **test manager**.
- Cannot serve real ads or accept real budgets - everything is sandbox.
- Even Test Access developer tokens can hit them.
- Daily quota: 15,000 operations regardless of token tier.
- Useful for CI/CD, integration tests, breaking-change validation.
- Setup: at https://ads.google.com create a manager, then click "Create account" -> tick "Create a test account."

### Production accounts

- Real money, real ads.
- Require **Basic or Standard** developer token to access.
- Subject to the spending caps / op caps in section 3.

### Practical pattern

Most teams maintain a test MCC with 1-2 test client accounts. The production code path uses an environment variable like `ADS_ENV=production` vs `ADS_ENV=test` to swap (developer_token, login_customer_id, target_customer_id). Never share refresh_tokens between test and prod.

---

## 8. Production-Readiness Checklist

### Token tier progression

1. **Test Access** (default at signup)
   - Sandbox accounts only
   - 15,000 ops/day on test accounts
   - Free, instant

2. **Basic Access**
   - Production accounts
   - 15,000 ops/day, $15,000/month spend cap
   - Apply via Ads UI -> Tools -> API Center -> "Apply for Basic Access"
   - Approval: typically 2-5 business days
   - Requires: company name, valid public website, monitored email, descriptive use case

3. **Standard Access**
   - Production accounts
   - Unlimited daily ops, no spend cap
   - Higher QPS allowance
   - Granted on review, typically requires existing Basic-level usage history

### Mandatory pre-launch checks

- [ ] Developer token approved at Basic or Standard tier
- [ ] OAuth consent screen set to **In production** (not Testing)
- [ ] Refresh token stored encrypted at rest
- [ ] Access token cached and refreshed at ~55 min mark
- [ ] All mutations use `validate_only` for risky changes (see below)
- [ ] `partial_failure: true` set on bulk operations to avoid all-or-nothing rollbacks
- [ ] Exponential backoff with jitter on retryable codes
- [ ] Circuit breaker on persistent `RESOURCE_EXHAUSTED`
- [ ] All requests log `request_id` for support tickets
- [ ] Monitoring on error rate per error_code category
- [ ] Account hierarchy walk uses `level <= N` cap to avoid infinite loops
- [ ] Test account in a separate environment, never sharing creds with production
- [ ] Sunset alerting: monitor blog/release notes for upcoming version retirement (see section 9)

### Validate-only mode

Most mutate methods accept a `validate_only: true` flag. The server runs all validation - syntax, policy, business rules - but does NOT commit changes. Use it for:
- Risky bulk imports before flipping the switch.
- Pre-flight policy violation checks.
- CI/CD smoke tests against production accounts without side effects.

`validate_only` requests still consume quota. Plan accordingly.

### Partial failure mode

For bulk mutates, set `partial_failure: true`. Server commits successful operations and reports errors for failed ones in `partial_failure_error`. Without this, a single bad operation rolls back the entire batch.

```json
{
  "partial_failure": true,
  "operations": [...]
}
```

Response:
```json
{
  "results": [
    { "resource_name": "customers/.../campaigns/123" },
    { "resource_name": "" },           // operation 1 failed
    { "resource_name": "customers/.../campaigns/124" }
  ],
  "partial_failure_error": {
    "code": 3,
    "message": "Multiple errors in 'errors'.",
    "details": [{"@type": "...GoogleAdsFailure", "errors": [...]}]
  }
}
```

To map errors to operations, check `error.location.field_path_elements[0].index`.

### Logging recommendations

Always log on every API failure:
- `request_id` (from `GoogleAdsFailure.request_id` or response header `request-id`)
- HTTP status + gRPC status code
- `error_code` (category + leaf enum)
- `error.message`
- `error.location.field_path_elements`
- The customer_id and login-customer-id used
- The first 100 chars of the request body (sanitized - never log developer-token or access_token)

---

## 9. Versioning Policy

### Cadence (effective January 2026)

Google moved the Ads API from quarterly to **monthly** major releases starting January 2026 with v23. Each major version is supported for **~14 months** (announced "1 year+" in Google blog).

Numbering: `v{MAJOR}_{MINOR}` e.g. `v23_2`. Major bumps are breaking; minor bumps are backward-compatible and applied automatically to in-flight calls on the existing endpoint.

### Sunset schedule (current as of May 2026)

| Version | Released | Sunset |
|---------|----------|--------|
| v17 | June 2024 | August 2025 |
| v18 | October 2024 | November 2025 |
| v19 | February 2025 | March 2026 |
| **v20** | June 2025 | **June 10, 2026** |
| v21 | ~ September 2025 | ~ August 2026 |
| v22 | ~ November 2025 | ~ October 2026 |
| **v23** | January 28, 2026 | ~ March 2027 |

Pre-2026 versions had ~3-per-year cadence. From v23 onward expect ~12 versions per year.

### Migration handling

1. **Subscribe** to https://ads-developers.googleblog.com - sunset reminders post 3-6 months out.
2. **Watch the deprecation header**: starting ~30 days before sunset, responses include `WARNING: Version X will be sunset on YYYY-MM-DD.`
3. **Diff tool**: https://developers.google.com/google-ads/api/diff-tool/vNEW/versus-vOLD shows proto-level changes.
4. **Migration guide**: each major version has its own "What's new" + breaking changes doc.
5. **Pin the version in code** rather than always-latest; bumping is a deliberate action.
6. **Run integration tests against `vNEW`** in a test account 30 days before sunset.

### Hitting a sunset version

After the sunset date, requests to the retired version return:

```
gRPC code 3 (INVALID_ARGUMENT)
HTTP 400
Message: "Requested entity was not found." or "Version v20 has been deprecated and is no longer available."
```

There is no grace period.

---

## 10. Quick Recovery Cheat Sheet (for LLMs)

When you encounter an error, do this triage:

1. **Parse the response** - extract `error.code` (gRPC), `error.message`, `error.details[].errors[].error_code`.
2. **Look up the leaf enum** - that is the actual cause.
3. **Categorize**:
   - `authentication_error.*` -> token problem -> refresh access_token; if that fails, re-mint refresh_token.
   - `authorization_error.*` -> permissions/setup -> check developer token tier, login-customer-id, account status.
   - `quota_error.*` -> rate limit -> backoff and retry.
   - `query_error.*` -> GAQL bug -> fix query syntax/fields.
   - `request_error.*` -> validation -> fix request body.
   - `internal_error.*` / `UNAVAILABLE` -> retry with backoff.
4. **Always log `request_id`** - required for any Google support ticket.
5. **Never blindly retry** non-retryable codes - you will exhaust quota or trigger token suspension.

---

## Sources

- [Quick start - Google Ads API](https://developers.google.com/google-ads/api/docs/get-started/make-first-call)
- [Use OAuth 2.0 to Access Google Ads API](https://developers.google.com/google-ads/api/docs/oauth/overview)
- [OAuth 2.0 Internals for Google Ads API](https://developers.google.com/google-ads/api/docs/oauth/internals)
- [Developer Token policy](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)
- [API Limits and Quotas](https://developers.google.com/google-ads/api/docs/best-practices/quotas)
- [Rate limits - Google Ads API](https://developers.google.com/google-ads/api/docs/best-practices/rate-limits)
- [Understand API errors](https://developers.google.com/google-ads/api/docs/best-practices/understand-api-errors)
- [Handle API errors](https://developers.google.com/google-ads/api/docs/get-started/handle-errors)
- [Common Errors](https://developers.google.com/google-ads/api/docs/common-errors)
- [Error Types](https://developers.google.com/google-ads/api/docs/best-practices/error-types)
- [Troubleshooting](https://developers.google.com/google-ads/api/docs/best-practices/troubleshooting)
- [Linking to Manager Accounts](https://developers.google.com/google-ads/api/docs/account-management/linking-manager-accounts)
- [List Accessible Accounts](https://developers.google.com/google-ads/api/docs/account-management/listing-accounts)
- [Get Account Hierarchy](https://developers.google.com/google-ads/api/docs/account-management/get-account-hierarchy)
- [Partial Failure](https://developers.google.com/google-ads/api/docs/best-practices/partial-failures)
- [Versioning](https://developers.google.com/google-ads/api/docs/concepts/versioning)
- [Deprecation and sunset](https://developers.google.com/google-ads/api/docs/sunset-dates)
- [Google Ads API v20 sunset reminder (Apr 2026 dev blog)](https://ads-developers.googleblog.com/2026/04/google-ads-api-v20-sunset-reminder.html)
- [Announcing v23 of the Google Ads API (Jan 2026 dev blog)](https://ads-developers.googleblog.com/2026/01/announcing-v23-of-google-ads-api.html)
- [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
