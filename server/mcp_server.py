#!/usr/bin/env python3
"""Google Ads MCP server.

Exposes the plugin's read+write capabilities as MCP tools so any MCP client
(Claude Code, Claude Desktop, Cursor, claude.ai Custom Connectors, etc.) can use it.

Run as stdio:
    python3 server/mcp_server.py

Configure in Claude Desktop's claude_desktop_config.json:
    {
      "mcpServers": {
        "google-ads": {
          "command": "python3",
          "args": ["/absolute/path/to/google-ads-plugin/server/mcp_server.py"]
        }
      }
    }
"""
import json
import sys
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from lib import GoogleAdsClient, GoogleAdsError, fmt, errors as err_mod  # noqa: E402
from lib.env import load_env  # noqa: E402

mcp = FastMCP("google-ads")


def _client(login_customer_id: Optional[str] = None) -> GoogleAdsClient:
    return GoogleAdsClient(login_customer_id=login_customer_id or None)


def _explain(e: GoogleAdsError) -> str:
    return "ERROR\n" + err_mod.explain(e)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@mcp.tool()
def check_credentials() -> str:
    """Verify the current OAuth credentials work. Returns the access-token prefix and accessible-customer count, or a structured error explaining what to fix."""
    try:
        env = load_env()
        missing = [k for k in ("GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_REFRESH_TOKEN") if not env.get(k)]
        if missing:
            return "MISSING:\n  " + "\n  ".join(missing) + "\n\nFix: cp .secrets/.env.example .secrets/.env, fill in values, then run scripts/oauth_setup.py"
        c = _client()
        ids = c.list_accessible_customers()
        return f"OK\n  api_version: {c.api_version}\n  accessible_accounts: {len(ids)}\n  customer_ids: {', '.join(ids[:10])}{'...' if len(ids) > 10 else ''}"
    except GoogleAdsError as e:
        return _explain(e)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


@mcp.tool()
def list_accounts(walk_mcc_tree: bool = False) -> str:
    """List Google Ads accounts the authenticated user can directly access.

    Args:
      walk_mcc_tree: if True, also walk each manager (MCC) and return its sub-accounts as nested entries.

    Returns markdown table.
    """
    try:
        c = _client()
        ids = c.list_accessible_customers()
        rows = []
        for cid in ids:
            info = {"id": cid}
            try:
                c.login_customer_id = None
                for r in c.search(cid, "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone, customer.manager, customer.test_account, customer.status FROM customer LIMIT 1"):
                    info.update(fmt.flatten(r))
            except GoogleAdsError as e:
                info["error"] = e.message
            rows.append(info)

        if walk_mcc_tree:
            for a in list(rows):
                if a.get("customer.manager"):
                    try:
                        children = c.list_customer_clients(a["id"])
                        a["clients"] = [fmt.flatten(ch) for ch in children]
                    except GoogleAdsError as e:
                        a["clients_error"] = e.message

        out = ["| customer_id | name | currency | timezone | type |", "|---|---|---|---|---|"]
        for a in rows:
            badges = []
            if a.get("customer.manager"): badges.append("MCC")
            if a.get("customer.test_account"): badges.append("TEST")
            out.append(f"| {a['id']} | {a.get('customer.descriptive_name', '?')} | {a.get('customer.currency_code', '')} | {a.get('customer.time_zone', '')} | {','.join(badges) or 'CLIENT'} |")
            for ch in a.get("clients", []):
                if ch.get("customer_client.status") == "CLOSED":
                    continue
                indent = "↳ "
                out.append(f"| {indent}{ch.get('customer_client.id', '')} | {ch.get('customer_client.descriptive_name', '')} | {ch.get('customer_client.currency_code', '')} | {ch.get('customer_client.time_zone', '')} | child of {a['id']} |")
        return "\n".join(out) + f"\n\n_{len(rows)} direct accounts_"
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def get_account_overview(customer_id: str, login_customer_id: str = "", days: int = 30) -> str:
    """One-page overview of an account: settings, last-N-days totals, and top 20 campaigns by cost.

    Args:
      customer_id: target customer ID (digits only, no dashes)
      login_customer_id: manager customer ID when target is a sub-account; empty when target is directly accessed
      days: lookback window. Allowed: 7, 14, 30, 90 (defaults to 30 if other)
    """
    try:
        days = days if days in (7, 14, 30, 90) else 30
        cid = customer_id.replace("-", "")
        c = _client(login_customer_id)

        cust_q = "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone, customer.status, customer.test_account, customer.manager, customer.auto_tagging_enabled, customer.optimization_score, customer.conversion_tracking_setting.conversion_tracking_id FROM customer LIMIT 1"
        cmp_q = f"""SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type,
            campaign.bidding_strategy_type, campaign_budget.amount_micros,
            metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value
        FROM campaign
        WHERE segments.date DURING LAST_{days}_DAYS
        ORDER BY metrics.cost_micros DESC LIMIT 200"""

        cust_rows = list(c.search(cid, cust_q))
        cmp_rows = list(c.search(cid, cmp_q))

        cust = fmt.flatten(cust_rows[0]) if cust_rows else {}
        currency = cust.get("customer.currency_code", "")
        out = [f"# {cust.get('customer.descriptive_name', '?')} ({cust.get('customer.id', cid)})"]
        out += [f"- currency: {currency}"]
        out += [f"- timezone: {cust.get('customer.time_zone', '')}"]
        out += [f"- status:   {cust.get('customer.status', '')}"]
        out += [f"- manager:  {cust.get('customer.manager', False)}"]
        out += [f"- test:     {cust.get('customer.test_account', False)}"]
        out += [f"- auto tag: {cust.get('customer.auto_tagging_enabled', False)}"]

        totals = fmt.summarize_metrics(cmp_rows)
        out += [f"\n## Last {days} days totals\n"]
        out += [f"- impressions: {int(totals.get('metrics.impressions', 0)):,}"]
        out += [f"- clicks:      {int(totals.get('metrics.clicks', 0)):,}"]
        out += [f"- cost:        {fmt.micros_to_currency(totals.get('metrics.cost_micros', 0), currency)}"]
        out += [f"- conversions: {totals.get('metrics.conversions', 0):.2f}"]
        out += [f"- conv value:  {totals.get('metrics.conversions_value', 0):,.2f} {currency}"]
        out += [f"- ctr:         {totals.get('metrics.ctr', 0)*100:.2f}%"]
        if totals.get("metrics.average_cpc_micros"):
            out += [f"- avg cpc:     {fmt.micros_to_currency(totals['metrics.average_cpc_micros'], currency)}"]
        if totals.get("metrics.roas"):
            out += [f"- roas:        {totals['metrics.roas']:.2f}x"]

        records = fmt.rows_to_records(cmp_rows)
        cols = ["campaign.id", "campaign.name", "campaign.status", "campaign.advertising_channel_type", "campaign.bidding_strategy_type", "metrics.impressions", "metrics.clicks", "metrics.cost_micros", "metrics.conversions"]
        out += ["\n## Top 20 campaigns by cost\n", fmt.to_markdown_table(records[:20], columns=cols)]

        return "\n".join(out)
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def run_gaql(customer_id: str, query: str, login_customer_id: str = "", format: str = "table", max_rows: int = 200) -> str:
    """Run any Google Ads Query Language (GAQL) query and return results.

    Args:
      customer_id: target customer ID (digits only)
      query: full GAQL query (SELECT ... FROM ... WHERE ...)
      login_customer_id: manager customer ID for MCC sub-account access
      format: 'table' (markdown), 'csv', or 'json'
      max_rows: limit display (server enforces; full data still in memory)

    See reference/gaql-cookbook.md for ready-made queries.
    """
    try:
        c = _client(login_customer_id)
        rows = list(c.search(customer_id.replace("-", ""), query))
        records = fmt.rows_to_records(rows)
        if format == "json":
            return json.dumps(records[:max_rows], indent=2, default=str) + f"\n// {len(records)} total rows"
        if format == "csv":
            return fmt.to_csv(records[:max_rows]) + f"\n# {len(records)} total rows"
        return fmt.to_markdown_table(records, max_rows=max_rows) + f"\n\n_{len(records)} total rows_"
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def list_campaigns(customer_id: str, login_customer_id: str = "", status: str = "ENABLED", days: int = 30) -> str:
    """List campaigns with their last-N-days performance.

    Args:
      customer_id: target customer ID
      login_customer_id: manager id when applicable
      status: ENABLED, PAUSED, REMOVED, or ALL
      days: 7, 14, 30, or 90
    """
    try:
        days = days if days in (7, 14, 30, 90) else 30
        status_filter = "" if status.upper() == "ALL" else f"AND campaign.status = '{status.upper()}'"
        q = f"""SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type,
            campaign.bidding_strategy_type, campaign_budget.amount_micros,
            metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value
        FROM campaign
        WHERE segments.date DURING LAST_{days}_DAYS {status_filter}
        ORDER BY metrics.cost_micros DESC"""
        return run_gaql(customer_id, q, login_customer_id, "table", 500)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def audit_account(customer_id: str, login_customer_id: str = "", days: int = 30) -> str:
    """Run structural audit: budget-limited campaigns, disapproved ads, low-QS keywords, wasted search terms, conversion tracking health."""
    try:
        cid = customer_id.replace("-", "")
        c = _client(login_customer_id)
        out = [f"# Audit {cid} (last {days} days)\n"]

        checks = [
            ("Budget-limited campaigns (>10% lost IS to budget)",
             f"SELECT campaign.id, campaign.name, metrics.search_budget_lost_impression_share, metrics.cost_micros FROM campaign WHERE campaign.status = 'ENABLED' AND segments.date DURING LAST_{days}_DAYS AND metrics.search_budget_lost_impression_share > 0.10 ORDER BY metrics.search_budget_lost_impression_share DESC"),
            ("Disapproved or limited-approval enabled ads",
             "SELECT campaign.name, ad_group.name, ad_group_ad.ad.id, ad_group_ad.policy_summary.approval_status FROM ad_group_ad WHERE ad_group_ad.policy_summary.approval_status IN ('DISAPPROVED', 'AREA_OF_INTEREST_ONLY') AND ad_group_ad.status = 'ENABLED' LIMIT 100"),
            ("Wasted search terms (cost > 0, zero conversions)",
             f"SELECT search_term_view.search_term, campaign.name, ad_group.name, metrics.cost_micros, metrics.clicks FROM search_term_view WHERE segments.date DURING LAST_{days}_DAYS AND metrics.cost_micros > 0 AND metrics.conversions = 0 ORDER BY metrics.cost_micros DESC LIMIT 50"),
            ("Low quality score keywords (QS < 5) with traffic",
             f"SELECT campaign.name, ad_group.name, ad_group_criterion.keyword.text, ad_group_criterion.quality_info.quality_score, metrics.impressions, metrics.cost_micros FROM keyword_view WHERE segments.date DURING LAST_{days}_DAYS AND ad_group_criterion.status = 'ENABLED' AND metrics.impressions > 100 AND ad_group_criterion.quality_info.quality_score < 5 ORDER BY metrics.cost_micros DESC LIMIT 50"),
            ("Active conversion actions",
             "SELECT conversion_action.id, conversion_action.name, conversion_action.category, conversion_action.type, conversion_action.primary_for_goal FROM conversion_action WHERE conversion_action.status = 'ENABLED'"),
        ]

        for label, query in checks:
            try:
                rows = list(c.search(cid, query))
                out += [f"## {label}", ""]
                if not rows:
                    out += ["_(none found - OK)_", ""]
                    continue
                records = fmt.rows_to_records(rows)
                out += [fmt.to_markdown_table(records, max_rows=20), ""]
                if len(records) > 20:
                    out += [f"_(showing 20 of {len(records)})_", ""]
            except GoogleAdsError as e:
                out += [f"## {label}", f"_(skipped: {e.message})_", ""]
        return "\n".join(out)
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def get_change_history(customer_id: str, login_customer_id: str = "", days: int = 7) -> str:
    """Recent change events - who changed what when. Window is hard-capped at 30 days."""
    try:
        days = min(days, 30)
        q = f"""SELECT change_event.change_date_time, change_event.user_email, change_event.client_type,
            change_event.change_resource_type, change_event.change_resource_name,
            change_event.resource_change_operation, change_event.changed_fields,
            campaign.name, ad_group.name
        FROM change_event
        WHERE change_event.change_date_time DURING LAST_{days}_DAYS
        ORDER BY change_event.change_date_time DESC LIMIT 500"""
        return run_gaql(customer_id, q, login_customer_id, "table", 100)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def list_recommendations(customer_id: str, login_customer_id: str = "") -> str:
    """List open Google Ads recommendations sorted by potential impact."""
    try:
        q = """SELECT recommendation.resource_name, recommendation.type,
            recommendation.impact.base_metrics.cost_micros,
            recommendation.impact.potential_metrics.cost_micros,
            recommendation.impact.base_metrics.conversions,
            recommendation.impact.potential_metrics.conversions,
            recommendation.campaign, recommendation.ad_group, recommendation.dismissed
        FROM recommendation
        WHERE recommendation.dismissed = FALSE"""
        return run_gaql(customer_id, q, login_customer_id, "table", 100)
    except Exception as e:
        return f"ERROR: {e}"


# ---------------------------------------------------------------------------
# Mutations - all default to validate_only=True
# ---------------------------------------------------------------------------


@mcp.tool()
def set_campaign_status(customer_id: str, campaign_id: str, status: str, login_customer_id: str = "", validate_only: bool = True) -> str:
    """Set a campaign's status to ENABLED, PAUSED, or REMOVED.

    Defaults to validate_only=True. Set validate_only=False to actually apply.
    REMOVED is permanent - prefer PAUSED.
    """
    if status.upper() not in ("ENABLED", "PAUSED", "REMOVED"):
        return "ERROR: status must be ENABLED, PAUSED, or REMOVED"
    try:
        c = _client(login_customer_id)
        ops = [{
            "update": {
                "resourceName": c.resource_name(customer_id, "campaigns", campaign_id),
                "status": status.upper(),
            },
            "updateMask": "status",
        }]
        resp = c.mutate_resource(customer_id.replace("-", ""), "campaigns", ops, validate_only=validate_only)
        return f"{'VALIDATE' if validate_only else 'APPLIED'} - status -> {status.upper()}\n{json.dumps(resp, indent=2, default=str)}"
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def update_campaign_budget(customer_id: str, budget_id: str, daily_amount: float, login_customer_id: str = "", validate_only: bool = True) -> str:
    """Change a campaign budget's daily amount.

    Args:
      budget_id: the campaign_budget.id (find via list_campaigns or run_gaql against campaign_budget)
      daily_amount: new daily amount in account currency (e.g. 50.0 for 50 CZK/day)
      validate_only: True (default) just tests; False applies
    """
    try:
        c = _client(login_customer_id)
        ops = [{
            "update": {
                "resourceName": c.resource_name(customer_id, "campaignBudgets", budget_id),
                "amountMicros": str(c.micros(daily_amount)),
            },
            "updateMask": "amount_micros",
        }]
        resp = c.mutate_resource(customer_id.replace("-", ""), "campaignBudgets", ops, validate_only=validate_only)
        return f"{'VALIDATE' if validate_only else 'APPLIED'} - budget {budget_id} -> {daily_amount}/day\n{json.dumps(resp, indent=2, default=str)}"
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def add_negative_keywords(customer_id: str, level: str, parent_id: str, keywords: List[str], match_type: str = "PHRASE", login_customer_id: str = "", validate_only: bool = True) -> str:
    """Add negative keywords at ad-group or campaign level.

    Args:
      level: 'AD_GROUP' or 'CAMPAIGN'
      parent_id: ad_group_id or campaign_id
      keywords: list of keyword text strings
      match_type: 'EXACT', 'PHRASE' (default), or 'BROAD'
    """
    level = level.upper()
    if level not in ("AD_GROUP", "CAMPAIGN"):
        return "ERROR: level must be AD_GROUP or CAMPAIGN"
    if match_type.upper() not in ("EXACT", "PHRASE", "BROAD"):
        return "ERROR: match_type must be EXACT, PHRASE, or BROAD"
    try:
        c = _client(login_customer_id)
        cid = customer_id.replace("-", "")
        if level == "AD_GROUP":
            ops = [{"create": {
                "adGroup": c.resource_name(cid, "adGroups", parent_id),
                "status": "ENABLED",
                "negative": True,
                "keyword": {"text": kw, "matchType": match_type.upper()},
            }} for kw in keywords]
            resp = c.mutate_resource(cid, "adGroupCriteria", ops, validate_only=validate_only, partial_failure=True)
        else:
            ops = [{"create": {
                "campaign": c.resource_name(cid, "campaigns", parent_id),
                "negative": True,
                "keyword": {"text": kw, "matchType": match_type.upper()},
            }} for kw in keywords]
            resp = c.mutate_resource(cid, "campaignCriteria", ops, validate_only=validate_only, partial_failure=True)
        return f"{'VALIDATE' if validate_only else 'APPLIED'} - {len(keywords)} negatives at {level} {parent_id}\n{json.dumps(resp, indent=2, default=str)}"
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def add_positive_keywords(customer_id: str, ad_group_id: str, keywords_with_match_types: List[List[str]], login_customer_id: str = "", validate_only: bool = True) -> str:
    """Add positive keywords to an ad group.

    Args:
      ad_group_id: the ad group ID
      keywords_with_match_types: list of [text, match_type] pairs, e.g. [["running shoes", "EXACT"], ["buy shoes", "PHRASE"]]
    """
    try:
        c = _client(login_customer_id)
        cid = customer_id.replace("-", "")
        ops = []
        for pair in keywords_with_match_types:
            if len(pair) != 2:
                return f"ERROR: each entry must be [text, match_type], got {pair}"
            text, mt = pair
            if mt.upper() not in ("EXACT", "PHRASE", "BROAD"):
                return f"ERROR: bad match_type: {mt}"
            ops.append({"create": {
                "adGroup": c.resource_name(cid, "adGroups", ad_group_id),
                "status": "ENABLED",
                "keyword": {"text": text, "matchType": mt.upper()},
            }})
        resp = c.mutate_resource(cid, "adGroupCriteria", ops, validate_only=validate_only, partial_failure=True)
        return f"{'VALIDATE' if validate_only else 'APPLIED'} - {len(ops)} keywords to ad group {ad_group_id}\n{json.dumps(resp, indent=2, default=str)}"
    except GoogleAdsError as e:
        return _explain(e)


@mcp.tool()
def mutate_raw(customer_id: str, resource_plural: str, operations_json: str, login_customer_id: str = "", validate_only: bool = True, partial_failure: bool = True) -> str:
    """Escape hatch: send a raw mutate request. Use only when no specific tool fits.

    Args:
      resource_plural: e.g. 'campaigns', 'adGroups', 'adGroupAds', 'adGroupCriteria', 'campaignBudgets'
      operations_json: JSON-stringified list of operations, each {create|update|remove[, updateMask]}

    See reference/mutations-guide.md for shapes.
    """
    try:
        ops = json.loads(operations_json)
        if not isinstance(ops, list):
            return "ERROR: operations_json must be a JSON array"
        c = _client(login_customer_id)
        resp = c.mutate_resource(customer_id.replace("-", ""), resource_plural, ops, validate_only=validate_only, partial_failure=partial_failure)
        return f"{'VALIDATE' if validate_only else 'APPLIED'} - {len(ops)} ops on {resource_plural}\n{json.dumps(resp, indent=2, default=str)}"
    except GoogleAdsError as e:
        return _explain(e)
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON in operations_json: {e}"


# ---------------------------------------------------------------------------
# Resources (read-only data exposure)
# ---------------------------------------------------------------------------


@mcp.resource("file://reference/{name}")
def get_reference_doc(name: str) -> str:
    """Read one of the bundled reference docs:
       api-overview, gaql-cookbook, resources-catalog, mutations-guide, errors-handbook, reporting-patterns
    """
    safe = name.replace("/", "").replace("..", "")
    p = REPO_ROOT / "reference" / f"{safe}.md"
    if not p.exists():
        return f"unknown reference: {name}. Available: api-overview, gaql-cookbook, resources-catalog, mutations-guide, errors-handbook, reporting-patterns"
    return p.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()
