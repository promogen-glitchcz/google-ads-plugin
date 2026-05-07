"""Formatting helpers: turn API responses into markdown tables, CSV, summaries.

The Google Ads REST API returns JSON with camelCase keys (descriptiveName, costMicros)
while GAQL queries use snake_case (descriptive_name, cost_micros). flatten() normalizes
back to snake_case so the data uses one consistent naming throughout.
"""
import csv
import io
import re
from typing import Any, Dict, Iterable, List, Optional

_CAMEL_RX = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_RX2 = re.compile(r"([a-z0-9])([A-Z])")


def to_snake(name: str) -> str:
    s = _CAMEL_RX.sub(r"\1_\2", name)
    return _CAMEL_RX2.sub(r"\1_\2", s).lower()


def flatten(row: Dict, prefix: str = "") -> Dict[str, Any]:
    """Flattens nested dicts using dot notation, normalizes camelCase -> snake_case.
    {'campaign': {'descriptiveName': 'X'}} -> {'campaign.descriptive_name': 'X'}.
    """
    out: Dict[str, Any] = {}
    for k, v in row.items():
        snake_k = to_snake(k)
        key = f"{prefix}{snake_k}" if not prefix else f"{prefix}.{snake_k}"
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out


def rows_to_records(rows: Iterable[Dict]) -> List[Dict[str, Any]]:
    """Each Google Ads search row is a dict with resource keys.
    Returns a list of flat records, one per row.
    """
    return [flatten(r) for r in rows]


def to_markdown_table(records: List[Dict], columns: Optional[List[str]] = None, max_rows: int = 50) -> str:
    if not records:
        return "_(no rows)_"
    columns = columns or sorted({k for r in records for k in r.keys()})
    head = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    def cell(v):
        s = "" if v is None else str(v)
        return s.replace("|", "\\|").replace("\n", " ")
    body_rows = []
    for r in records[:max_rows]:
        body_rows.append("| " + " | ".join(cell(r.get(c, "")) for c in columns) + " |")
    note = ""
    if len(records) > max_rows:
        note = f"\n\n_(showing {max_rows} of {len(records)} rows)_"
    return "\n".join([head, sep] + body_rows) + note


def to_csv(records: List[Dict], columns: Optional[List[str]] = None) -> str:
    if not records:
        return ""
    columns = columns or sorted({k for r in records for k in r.keys()})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    for r in records:
        w.writerow(r)
    return buf.getvalue()


def micros_to_currency(value, currency: str = "") -> str:
    if value is None or value == "":
        return ""
    try:
        amount = int(value) / 1_000_000.0
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:,.2f} {currency}".strip()


def pct(numerator, denominator, digits: int = 2) -> str:
    try:
        n = float(numerator or 0)
        d = float(denominator or 0)
        if d == 0:
            return "-"
        return f"{(n / d) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def summarize_metrics(rows: List[Dict]) -> Dict[str, float]:
    """Sums standard metrics across rows: impressions, clicks, cost_micros, conversions, conversion_value."""
    keys = [
        "metrics.impressions",
        "metrics.clicks",
        "metrics.cost_micros",
        "metrics.conversions",
        "metrics.conversions_value",
        "metrics.all_conversions",
        "metrics.all_conversions_value",
    ]
    totals = {k: 0.0 for k in keys}
    for r in rows:
        flat = flatten(r) if any(isinstance(v, dict) for v in r.values()) else r
        for k in keys:
            v = flat.get(k)
            if v is None:
                continue
            try:
                totals[k] += float(v)
            except (TypeError, ValueError):
                pass
    if totals["metrics.impressions"]:
        totals["metrics.ctr"] = totals["metrics.clicks"] / totals["metrics.impressions"]
    if totals["metrics.clicks"]:
        totals["metrics.average_cpc_micros"] = totals["metrics.cost_micros"] / totals["metrics.clicks"]
    if totals["metrics.clicks"]:
        totals["metrics.conversion_rate"] = totals["metrics.conversions"] / totals["metrics.clicks"]
    if totals["metrics.cost_micros"] and totals["metrics.conversions_value"]:
        totals["metrics.roas"] = totals["metrics.conversions_value"] / (totals["metrics.cost_micros"] / 1_000_000.0)
    return totals
