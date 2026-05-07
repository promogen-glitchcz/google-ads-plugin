# Google Ads Plugin for Claude Code

Comprehensive Google Ads management plugin: read, edit, report, audit and optimize Google Ads accounts via Claude. Covers OAuth setup, GAQL queries, all common mutations (campaigns, ad groups, keywords, ads, budgets, bidding), performance reporting, recommendations, and change history.

Built for Claude Code's plugin system. Once installed, just talk to Claude in plain language - "what accounts do I have?", "show me wasted spend last month", "pause campaign X", "build me a dashboard".

## Quick start

```bash
# 1. Clone
git clone https://github.com/promogen-glitchcz/google-ads-plugin.git
cd google-ads-plugin

# 2. Set credentials
cp .secrets/.env.example .secrets/.env
# edit .secrets/.env with your client_id, client_secret, developer_token

# 3. Generate refresh token (one-time)
python3 scripts/oauth_setup.py
# - opens browser
# - sign in with the Google account that has Google Ads access
# - click Allow
# - refresh token is saved

# 4. Verify
python3 scripts/list_accounts.py
```

If `list_accounts.py` prints your customer IDs, you're done. Now ask Claude.

## What you can do

### Read / report
- "list my accounts" / "what's in this MCC"
- "show last 30 days for campaign X"
- "top keywords by cost"
- "search terms with no conversions"
- "performance by device / hour / country"
- "build me a dashboard for account 1234567890"

### Edit
- "pause campaign X" / "enable campaign Y"
- "rename campaign X to Y"
- "increase budget on campaign X to 100/day"
- "switch campaign X to maximize conversions"
- "add these keywords to ad group X (paste list)"
- "add these search terms as negatives campaign-wide"
- "create a new search campaign X with 50/day budget"
- "create RSA in ad group X with these headlines/descriptions"

### Audit / optimize
- "audit my account"
- "what does Google recommend"
- "find wasted spend"
- "find disapproved ads"
- "show recent changes"

## Architecture

```
google-ads-plugin/
├── .claude-plugin/plugin.json    plugin manifest
├── .secrets/.env                 credentials (gitignored)
├── lib/                          shared Python helpers
│   ├── env.py                    .env loader
│   ├── auth.py                   OAuth refresh
│   ├── client.py                 GAQL search + mutate
│   ├── format.py                 markdown / CSV / summaries
│   └── errors.py                 friendly error explanations
├── scripts/                      runnable CLI tools
│   ├── oauth_setup.py            one-time OAuth wizard
│   ├── list_accounts.py          discover accessible accounts
│   ├── account_overview.py       one-page account summary
│   ├── run_gaql.py               run any GAQL query
│   └── audit_account.py          structural audit
├── reference/                    reference docs Claude reads
│   ├── api-overview.md           versioning, headers, endpoints
│   ├── gaql-cookbook.md          50+ ready GAQL queries
│   ├── resources-catalog.md      all resources + their fields
│   ├── mutations-guide.md        full write/update/remove reference
│   ├── errors-handbook.md        every error with cause + fix
│   └── reporting-patterns.md     KPIs, anomalies, dashboards
└── skills/                       Claude Code skills
    ├── oauth-setup/
    ├── account-explorer/
    ├── data-query/
    ├── campaign-management/
    ├── keyword-operations/
    ├── ad-management/
    ├── budget-bidding/
    ├── performance-reporting/
    ├── bulk-operations/
    ├── audit-and-recommendations/
    └── change-history/
```

## Skills

Each skill has a `SKILL.md` that tells Claude when to use it and how. Claude picks the right skill automatically based on what you ask.

| skill | use when |
|---|---|
| oauth-setup | first-time setup, fixing 401 errors, refresh token expired |
| account-explorer | "what accounts can I see", picking which customer to operate on |
| data-query | any read - metrics, lists, performance, trends |
| campaign-management | create/pause/edit/remove campaigns, networks, geo, language |
| keyword-operations | add/pause/remove keywords, negatives, search-term mining |
| ad-management | RSA creation, PMax assets, sitelinks, callouts, policy review |
| budget-bidding | budget changes, bidding strategy switches, pacing |
| performance-reporting | KPI reports, dashboards, MoM comparison, anomalies |
| bulk-operations | CSV-driven mass edits, batch operations |
| audit-and-recommendations | structural audit, Google's recommendations, apply/dismiss |
| change-history | who-changed-what, audit log, risky recent changes |

## Reference docs

These are loaded as needed by Claude when reasoning about Google Ads operations:

- [api-overview.md](reference/api-overview.md) - versioning, headers, endpoints
- [gaql-cookbook.md](reference/gaql-cookbook.md) - 50+ ready GAQL queries
- [resources-catalog.md](reference/resources-catalog.md) - every resource and its fields
- [mutations-guide.md](reference/mutations-guide.md) - REST JSON for create/update/remove
- [errors-handbook.md](reference/errors-handbook.md) - every error with explanation and fix
- [reporting-patterns.md](reference/reporting-patterns.md) - KPI math, anomaly patterns, dashboard structure

## Credentials

You need 4 things (3 from you + 1 we generate):
1. **Client ID** - from Google Cloud Console -> Credentials -> OAuth 2.0 Client IDs
2. **Client Secret** - same place
3. **Developer Token** - from Google Ads UI -> Tools -> API Center (22-char string)
4. **Refresh Token** - generated by `scripts/oauth_setup.py`

Setup wizard requires your OAuth client to have `http://localhost:8765` in authorized redirect URIs.

For long-term automation, **publish** your OAuth consent screen (Testing-mode tokens expire after 7 days).

## Required Python

Python 3.9+. No external deps needed (uses stdlib only).

## API version

Targets Google Ads API **v20** by default. Override with `GOOGLE_ADS_API_VERSION` in `.env`. Note v20 sunsets June 10, 2026 - update to v23+ when ready.

## Manager / MCC

Set `GOOGLE_ADS_LOGIN_CUSTOMER_ID` in `.env` to your manager's customer ID (digits only). Then any operation on a sub-account works.

## Safety

- Mutations default to validate-first when called via skills
- Critical operations (delete, bulk pause) ask for confirmation
- Credentials never committed (`.gitignore` covers `.secrets/`, `.env`)
- All API calls retried with exponential backoff on 429 / 5xx

## Contributing

Open issues, send PRs. All skills are markdown - readable, editable.

## License

MIT
