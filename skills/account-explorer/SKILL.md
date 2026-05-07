---
name: account-explorer
description: Discover the Google Ads account hierarchy - list accessible accounts, walk MCC sub-account trees, get account-level settings (currency, time zone, conversion tracking, status). Use when the user asks "which accounts can I see", "list my customers", "what's the MCC structure", "show account settings", or before any operation that needs a customer_id and the user hasn't provided one.
---

# Account explorer

The first skill to run on any new Google Ads request when you don't yet know the customer_id.

## When to use

- User asks "what accounts do I have access to" / "list my Google Ads accounts"
- User asks about MCC structure or sub-accounts
- User asks for "account info" / "account settings" / "currency / timezone"
- You need a customer_id for another operation but the user hasn't given one
- After OAuth setup succeeds, run this to verify access

## How to do it

### List accessible accounts (always start here)

```bash
python3 scripts/list_accounts.py
```

This prints customer IDs the auth user can directly act on. Note: it does NOT include all accounts inside an MCC tree - just the accounts where this user has been added.

### Walk the MCC tree

If a returned account has `[MANAGER]`, walk its full client tree:

```bash
python3 scripts/list_accounts.py --tree
```

Internally this runs against `customer_client` resource:
```sql
SELECT
  customer_client.client_customer,
  customer_client.id,
  customer_client.descriptive_name,
  customer_client.currency_code,
  customer_client.time_zone,
  customer_client.manager,
  customer_client.test_account,
  customer_client.level,
  customer_client.status
FROM customer_client
WHERE customer_client.status != 'CLOSED'
```
With `login-customer-id` header set to the manager id.

### Account overview (one-page summary)

```bash
python3 scripts/account_overview.py CUSTOMER_ID --days 30
```

Returns currency, time zone, status, manager flag, conversion tracking ID, plus last-30-days totals and top campaigns.

For a sub-account under an MCC, pass the manager:
```bash
python3 scripts/account_overview.py CUSTOMER_ID --days 30 --login-customer-id MANAGER_ID
```

## Customer ID rules

- Always strip dashes: `123-456-7890` -> `1234567890`
- Customer IDs are 10 digits
- A test customer id starts the same way; the test_account flag tells you it's a test
- For sub-accounts, you must set `login-customer-id` header to a manager that owns it (set `GOOGLE_ADS_LOGIN_CUSTOMER_ID` env var or pass `--login-customer-id`)

## Picking which account the user means

If the user says something vague like "my account" and there are multiple:
1. Run list_accounts and show them
2. Ask which one they mean
3. Optionally save the chosen one as default by setting `GOOGLE_ADS_DEFAULT_CUSTOMER_ID` in `.secrets/.env`

## Reference

- All resources you can read: [reference/resources-catalog.md](../../reference/resources-catalog.md)
- Errors specifically about customer access: [reference/errors-handbook.md](../../reference/errors-handbook.md) (USER_PERMISSION_DENIED, CUSTOMER_NOT_FOUND, MISSING_LOGIN_CUSTOMER_ID)
