#!/usr/bin/env python3
"""List Google Ads accounts accessible with current refresh token.

Usage:
  python3 scripts/list_accounts.py
  python3 scripts/list_accounts.py --tree              # also walk MCC sub-accounts
  python3 scripts/list_accounts.py --json              # machine-readable
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import GoogleAdsClient, GoogleAdsError, errors, fmt  # noqa: E402

INFO_QUERY = """
SELECT
  customer.id,
  customer.descriptive_name,
  customer.currency_code,
  customer.time_zone,
  customer.manager,
  customer.test_account,
  customer.status
FROM customer
LIMIT 1
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tree", action="store_true", help="walk MCC tree")
    p.add_argument("--json", action="store_true", help="json output")
    args = p.parse_args()

    client = GoogleAdsClient()
    try:
        ids = client.list_accessible_customers()
    except GoogleAdsError as e:
        print(errors.explain(e), file=sys.stderr)
        sys.exit(2)

    accounts = []
    for cid in ids:
        info = {"id": cid}
        try:
            client.login_customer_id = None
            rows = list(client.search(cid, INFO_QUERY))
            if rows:
                info.update(fmt.flatten(rows[0]))
        except GoogleAdsError as e:
            info["error"] = e.message
        accounts.append(info)

    if args.tree:
        for a in list(accounts):
            if a.get("customer.manager"):
                try:
                    children = client.list_customer_clients(a["id"])
                    a["clients"] = [fmt.flatten(c) for c in children]
                except GoogleAdsError as e:
                    a["clients_error"] = e.message

    if args.json:
        print(json.dumps(accounts, indent=2, default=str))
        return

    print("\n=== Accessible accounts ===\n")
    for a in accounts:
        manager = " [MANAGER]" if a.get("customer.manager") else ""
        test = " [TEST]" if a.get("customer.test_account") else ""
        print(
            f"  {a['id']}{manager}{test}  {a.get('customer.descriptive_name', '')}  "
            f"{a.get('customer.currency_code', '')}  {a.get('customer.time_zone', '')}"
        )
        if a.get("error"):
            print(f"    ! {a['error']}")
        for c in a.get("clients", []):
            indent = "    " * (c.get("customer_client.level", 0) or 1)
            print(
                f"{indent}-> {c.get('customer_client.id', '')}  "
                f"{c.get('customer_client.descriptive_name', '')}  "
                f"{c.get('customer_client.currency_code', '')}"
            )
    print(f"\nTotal direct: {len(accounts)}\n")


if __name__ == "__main__":
    main()
