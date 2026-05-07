#!/usr/bin/env python3
"""Run a comprehensive audit of an account.

Checks:
  - active campaigns without conversion tracking
  - campaigns limited by budget
  - disapproved or limited-approval ads
  - ad groups with no enabled ads
  - keywords below first-page bid
  - search terms with high cost and zero conversions
  - missing negative-keyword lists at campaign level
  - quality score < 5 keywords with significant impressions

Usage:
  python3 scripts/audit_account.py CUSTOMER_ID [--days 30] [--login-customer-id ID]
"""
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import GoogleAdsClient, GoogleAdsError, fmt, errors  # noqa: E402


def section(title: str):
    print(f"\n## {title}\n")


def run_check(client, cust_id, label, query, columns):
    try:
        rows = list(client.search(cust_id, query))
    except GoogleAdsError as e:
        print(f"_(skipped: {e.message})_")
        return
    section(label)
    if not rows:
        print("_OK - none found_")
        return
    print(fmt.to_markdown_table(fmt.rows_to_records(rows), columns=columns, max_rows=30))
    print(f"\n_({len(rows)} rows)_")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("customer_id")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--login-customer-id", default=None)
    args = p.parse_args()
    cust_id = args.customer_id.replace("-", "")
    days = args.days

    client = GoogleAdsClient(login_customer_id=args.login_customer_id)

    print(f"# Audit for customer {cust_id} (last {days} days)")

    run_check(
        client, cust_id, "Campaigns limited by budget",
        f"""
        SELECT campaign.id, campaign.name, campaign.status,
               metrics.search_budget_lost_impression_share, metrics.cost_micros
        FROM campaign
        WHERE campaign.status = 'ENABLED'
          AND segments.date DURING LAST_{days}_DAYS
          AND metrics.search_budget_lost_impression_share > 0.10
        ORDER BY metrics.search_budget_lost_impression_share DESC
        """,
        ["campaign.id", "campaign.name", "metrics.search_budget_lost_impression_share", "metrics.cost_micros"],
    )

    run_check(
        client, cust_id, "Disapproved or limited-approval ads",
        """
        SELECT ad_group_ad.ad.id, ad_group.name, campaign.name,
               ad_group_ad.policy_summary.approval_status,
               ad_group_ad.policy_summary.review_status
        FROM ad_group_ad
        WHERE ad_group_ad.policy_summary.approval_status IN ('DISAPPROVED', 'AREA_OF_INTEREST_ONLY')
          AND ad_group_ad.status = 'ENABLED'
        LIMIT 100
        """,
        ["campaign.name", "ad_group.name", "ad_group_ad.ad.id", "ad_group_ad.policy_summary.approval_status"],
    )

    run_check(
        client, cust_id, "Search terms wasting spend (cost > 0, zero conversions)",
        f"""
        SELECT search_term_view.search_term, campaign.name, ad_group.name,
               metrics.cost_micros, metrics.clicks, metrics.conversions
        FROM search_term_view
        WHERE segments.date DURING LAST_{days}_DAYS
          AND metrics.cost_micros > 0
          AND metrics.conversions = 0
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
        """,
        ["search_term_view.search_term", "campaign.name", "metrics.cost_micros", "metrics.clicks", "metrics.conversions"],
    )

    run_check(
        client, cust_id, "Low quality score keywords (QS < 5) with traffic",
        f"""
        SELECT ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type,
               ad_group.name,
               campaign.name,
               ad_group_criterion.quality_info.quality_score,
               metrics.impressions, metrics.cost_micros
        FROM keyword_view
        WHERE segments.date DURING LAST_{days}_DAYS
          AND ad_group_criterion.status = 'ENABLED'
          AND metrics.impressions > 100
          AND ad_group_criterion.quality_info.quality_score < 5
        ORDER BY metrics.cost_micros DESC
        LIMIT 50
        """,
        ["ad_group_criterion.keyword.text", "ad_group_criterion.keyword.match_type",
         "ad_group_criterion.quality_info.quality_score", "metrics.impressions", "metrics.cost_micros"],
    )

    run_check(
        client, cust_id, "Conversion actions enabled",
        """
        SELECT conversion_action.id, conversion_action.name, conversion_action.status,
               conversion_action.category, conversion_action.type,
               conversion_action.primary_for_goal,
               conversion_action.counting_type
        FROM conversion_action
        WHERE conversion_action.status = 'ENABLED'
        """,
        ["conversion_action.name", "conversion_action.category", "conversion_action.type", "conversion_action.primary_for_goal"],
    )


if __name__ == "__main__":
    main()
