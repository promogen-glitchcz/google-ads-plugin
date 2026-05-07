#!/usr/bin/env python3
"""Print a one-page overview of a Google Ads account.

Usage:
  python3 scripts/account_overview.py CUSTOMER_ID [--days 30] [--login-customer-id MANAGER_ID]
"""
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import GoogleAdsClient, GoogleAdsError, fmt, errors  # noqa: E402

CUSTOMER_QUERY = """
SELECT
  customer.id,
  customer.descriptive_name,
  customer.currency_code,
  customer.time_zone,
  customer.status,
  customer.test_account,
  customer.manager,
  customer.auto_tagging_enabled,
  customer.tracking_url_template,
  customer.conversion_tracking_setting.conversion_tracking_id,
  customer.conversion_tracking_setting.cross_account_conversion_tracking_id
FROM customer
LIMIT 1
"""

CAMPAIGN_QUERY_TMPL = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  campaign.bidding_strategy_type,
  campaign_budget.amount_micros,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM campaign
WHERE segments.date DURING LAST_{days}_DAYS
ORDER BY metrics.cost_micros DESC
LIMIT 200
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("customer_id")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--login-customer-id", default=None)
    args = p.parse_args()

    days = 30 if args.days not in (7, 14, 30, 90) else args.days
    cust_id = args.customer_id.replace("-", "")

    try:
        client = GoogleAdsClient(login_customer_id=args.login_customer_id)
        cust_rows = list(client.search(cust_id, CUSTOMER_QUERY))
        cmp_rows = list(client.search(cust_id, CAMPAIGN_QUERY_TMPL.format(days=days)))
    except GoogleAdsError as e:
        print(errors.explain(e), file=sys.stderr)
        sys.exit(2)

    cust = fmt.flatten(cust_rows[0]) if cust_rows else {}
    currency = cust.get("customer.currency_code", "")
    name = cust.get("customer.descriptive_name", "")
    cust_id_full = cust.get("customer.id", cust_id)

    print(f"# {name} ({cust_id_full})\n")
    print(f"- currency: {currency}")
    print(f"- timezone: {cust.get('customer.time_zone', '')}")
    print(f"- status:   {cust.get('customer.status', '')}")
    print(f"- test:     {cust.get('customer.test_account', False)}")
    print(f"- manager:  {cust.get('customer.manager', False)}")
    print(f"- auto tag: {cust.get('customer.auto_tagging_enabled', False)}")

    flat_cmp = fmt.rows_to_records(cmp_rows)
    totals = fmt.summarize_metrics(cmp_rows)

    print(f"\n## Last {days} days totals\n")
    print(f"- impressions: {int(totals.get('metrics.impressions', 0)):,}")
    print(f"- clicks:      {int(totals.get('metrics.clicks', 0)):,}")
    print(f"- cost:        {fmt.micros_to_currency(totals.get('metrics.cost_micros', 0), currency)}")
    print(f"- conversions: {totals.get('metrics.conversions', 0):.2f}")
    print(f"- conv value:  {totals.get('metrics.conversions_value', 0):,.2f} {currency}")
    print(f"- ctr:         {totals.get('metrics.ctr', 0)*100:.2f}%")
    if totals.get("metrics.average_cpc_micros"):
        print(f"- avg cpc:     {fmt.micros_to_currency(totals.get('metrics.average_cpc_micros'), currency)}")
    if totals.get("metrics.roas"):
        print(f"- roas:        {totals.get('metrics.roas'):.2f}x")

    print("\n## Top 20 campaigns by cost\n")
    cols = [
        "campaign.id",
        "campaign.name",
        "campaign.status",
        "campaign.advertising_channel_type",
        "campaign.bidding_strategy_type",
        "metrics.impressions",
        "metrics.clicks",
        "metrics.cost_micros",
        "metrics.conversions",
    ]
    print(fmt.to_markdown_table(flat_cmp[:20], columns=cols))


if __name__ == "__main__":
    main()
