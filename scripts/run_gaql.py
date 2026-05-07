#!/usr/bin/env python3
"""Generic GAQL query runner.

Usage:
  python3 scripts/run_gaql.py CUSTOMER_ID "SELECT campaign.id, campaign.name FROM campaign LIMIT 10"
  python3 scripts/run_gaql.py CUSTOMER_ID @path/to/query.sql
  python3 scripts/run_gaql.py CUSTOMER_ID -      # reads query from stdin

Env (optional):
  GOOGLE_ADS_LOGIN_CUSTOMER_ID - manager id when CUSTOMER_ID is a sub-account
  --format=table|csv|json (default: table)
  --max-rows=N (default 200 for table, all for csv/json)
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib import GoogleAdsClient, GoogleAdsError, fmt, errors  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("customer_id")
    p.add_argument("query", help="GAQL query, @file path, or - for stdin")
    p.add_argument("--login-customer-id", default=None)
    p.add_argument("--format", choices=["table", "csv", "json"], default="table")
    p.add_argument("--max-rows", type=int, default=200)
    args = p.parse_args()

    if args.query == "-":
        query = sys.stdin.read()
    elif args.query.startswith("@"):
        query = Path(args.query[1:]).read_text(encoding="utf-8")
    else:
        query = args.query

    try:
        client = GoogleAdsClient(login_customer_id=args.login_customer_id)
        rows = list(client.search(args.customer_id, query))
    except GoogleAdsError as e:
        print(errors.explain(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    records = fmt.rows_to_records(rows)

    if args.format == "json":
        print(json.dumps(records, indent=2, default=str))
    elif args.format == "csv":
        print(fmt.to_csv(records))
    else:
        print(fmt.to_markdown_table(records, max_rows=args.max_rows))
    print(f"\n{len(records)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
