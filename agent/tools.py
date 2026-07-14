"""Tools exposed to the Claude agent.

Three functions over the DataCo Smart Supply Chain CSV:

    query_orders(filters)        -> summary dict + sample rows
    check_inventory(product_or_category) -> aggregated order-volume view
    flag_late_shipment(order_id, reason) -> appends to outputs/flagged_orders.csv

These are the *implementations* the tool-use loop will invoke; the JSON schemas
that Claude sees are defined separately in the agent script.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

_AGENT_DIR = Path(__file__).resolve().parent
_PHASE_DIR = _AGENT_DIR.parent
_DATA_CSV = _PHASE_DIR / "data" / "DataCoSupplyChainDataset.csv"
_FLAGGED_CSV = _PHASE_DIR / "outputs" / "flagged_orders.csv"


# --------------------------------------------------------------------------- #
# Data loading (cached)
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _load_orders() -> pd.DataFrame:
    """Load the DataCo CSV once per process. Parse dates and normalize types."""
    df = pd.read_csv(_DATA_CSV, encoding="latin-1", low_memory=False)
    df["order date (DateOrders)"] = pd.to_datetime(
        df["order date (DateOrders)"], errors="coerce"
    )
    df["shipping date (DateOrders)"] = pd.to_datetime(
        df["shipping date (DateOrders)"], errors="coerce"
    )
    return df


# --------------------------------------------------------------------------- #
# Hierarchy hint helper
# --------------------------------------------------------------------------- #

def _hierarchy_hints(filters: dict[str, Any]) -> list[str]:
    """If a category/department filter returned 0 rows, tell the caller when
    the value actually lives in the *other* column of the product hierarchy.

    Category ↔ Department is the common mix-up: e.g. 'Fitness' is a Department,
    not a Category. This nudges the agent to retry with the right filter
    instead of giving up.
    """
    df = _load_orders()
    hints: list[str] = []

    if category := filters.get("category"):
        cat_hits = df["Category Name"].str.contains(category, case=False, na=False)
        dept_hits = df["Department Name"].str.contains(category, case=False, na=False)
        if not cat_hits.any() and dept_hits.any():
            hints.append(
                f"'{category}' exists in the Department column, not Category — "
                f"try department='{category}'."
            )

    if department := filters.get("department"):
        dept_hits = df["Department Name"].str.contains(department, case=False, na=False)
        cat_hits = df["Category Name"].str.contains(department, case=False, na=False)
        if not dept_hits.any() and cat_hits.any():
            hints.append(
                f"'{department}' exists in the Category column, not Department — "
                f"try category='{department}'."
            )

    return hints


# --------------------------------------------------------------------------- #
# Tool 1: query_orders
# --------------------------------------------------------------------------- #

def query_orders(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Filter orders by any combination of delivery_status, region, category, date range.

    filters keys (all optional):
        delivery_status: str  — matches "Delivery Status" (e.g. "Late delivery")
        region:          str  — matches "Order Region"
        category:        str  — matches "Category Name" (case-insensitive contains)
        department:      str  — matches "Department Name" (case-insensitive contains)
        start_date:      str  — ISO date, filters "order date (DateOrders)" >=
        end_date:        str  — ISO date, filters "order date (DateOrders)" <=
        late_only:       bool — shortcut for Late_delivery_risk == 1
        limit:           int  — number of sample rows to return (default 5)

    Returns a summary dict with counts, breakdowns, and a small sample of rows.
    """
    filters = filters or {}
    df = _load_orders()
    original_len = len(df)

    if status := filters.get("delivery_status"):
        df = df[df["Delivery Status"].str.casefold() == status.casefold()]
    if region := filters.get("region"):
        df = df[df["Order Region"].str.casefold() == region.casefold()]
    if category := filters.get("category"):
        df = df[df["Category Name"].str.contains(category, case=False, na=False)]
    if department := filters.get("department"):
        df = df[df["Department Name"].str.contains(department, case=False, na=False)]
    if start := filters.get("start_date"):
        df = df[df["order date (DateOrders)"] >= pd.Timestamp(start)]
    if end := filters.get("end_date"):
        df = df[df["order date (DateOrders)"] <= pd.Timestamp(end)]
    if filters.get("late_only"):
        df = df[df["Late_delivery_risk"] == 1]

    limit = int(filters.get("limit", 5))
    matched = len(df)

    if matched == 0:
        hints = _hierarchy_hints(filters)
        result = {
            "matched": 0,
            "original_rows": original_len,
            "filters_applied": filters,
            "sample": [],
        }
        if hints:
            result["hint"] = " ".join(hints)
        return result

    sample_cols = [
        "Order Id",
        "order date (DateOrders)",
        "Delivery Status",
        "Late_delivery_risk",
        "Days for shipping (real)",
        "Days for shipment (scheduled)",
        "Category Name",
        "Product Name",
        "Order Region",
        "Customer Segment",
        "Shipping Mode",
    ]
    sample = (
        df[sample_cols]
        .head(limit)
        .astype({"order date (DateOrders)": str})
        .to_dict(orient="records")
    )

    delivery_breakdown = df["Delivery Status"].value_counts().to_dict()
    late_pct = float((df["Late_delivery_risk"] == 1).mean() * 100)
    avg_real = float(df["Days for shipping (real)"].mean())
    avg_sched = float(df["Days for shipment (scheduled)"].mean())

    return {
        "matched": matched,
        "original_rows": original_len,
        "filters_applied": filters,
        "delivery_status_breakdown": delivery_breakdown,
        "late_delivery_risk_pct": round(late_pct, 2),
        "avg_days_shipping_real": round(avg_real, 2),
        "avg_days_shipping_scheduled": round(avg_sched, 2),
        "shipping_gap_days": round(avg_real - avg_sched, 2),
        "sample": sample,
    }


# --------------------------------------------------------------------------- #
# Tool 2: check_inventory
# --------------------------------------------------------------------------- #

def check_inventory(product_or_category: str) -> dict[str, Any]:
    """Aggregated order-volume view for a product or category.

    The DataCo dataset has no true on-hand stock column, so 'inventory' here is
    proxied by order volume, quantity moved, and late-delivery pressure — enough
    signal to tell the agent whether pushing more through this SKU/category is
    likely to run into fulfillment issues.
    """
    df = _load_orders()
    q = product_or_category.strip()

    mask = df["Product Name"].str.contains(q, case=False, na=False) | df[
        "Category Name"
    ].str.contains(q, case=False, na=False)
    hit = df[mask]

    if hit.empty:
        return {
            "query": q,
            "matched": 0,
            "note": "no matching product or category found",
        }

    match_type = (
        "product"
        if hit["Product Name"].str.contains(q, case=False, na=False).any()
        else "category"
    )

    total_orders = len(hit)
    total_units = int(hit["Order Item Quantity"].sum())
    late_orders = int((hit["Delivery Status"] == "Late delivery").sum())
    late_pct = round(late_orders / total_orders * 100, 2)

    top_regions = hit["Order Region"].value_counts().head(5).to_dict()
    top_shipping_modes = hit["Shipping Mode"].value_counts().to_dict()
    top_products = (
        hit["Product Name"].value_counts().head(5).to_dict()
        if match_type == "category"
        else {}
    )

    return {
        "query": q,
        "match_type": match_type,
        "matched": total_orders,
        "total_units_ordered": total_units,
        "late_orders": late_orders,
        "late_pct": late_pct,
        "top_regions_by_volume": top_regions,
        "shipping_mode_mix": top_shipping_modes,
        "top_products_in_category": top_products,
    }


# --------------------------------------------------------------------------- #
# Tool 3: flag_late_shipment
# --------------------------------------------------------------------------- #

def flag_late_shipment(order_id: int | str, reason: str) -> dict[str, Any]:
    """Append the order to outputs/flagged_orders.csv with timestamp and reason.

    Looks up the order in the dataset so the log carries context (delivery
    status, region, shipping gap) rather than just an ID.
    """
    df = _load_orders()

    try:
        order_id_int = int(order_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": f"invalid order_id: {order_id!r}"}

    hit = df[df["Order Id"] == order_id_int]
    if hit.empty:
        return {"ok": False, "error": f"Order Id {order_id_int} not found"}

    row = hit.iloc[0]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    record = {
        "flagged_at": ts,
        "order_id": order_id_int,
        "reason": reason,
        "delivery_status": row["Delivery Status"],
        "late_delivery_risk": int(row["Late_delivery_risk"]),
        "days_real": int(row["Days for shipping (real)"]),
        "days_scheduled": int(row["Days for shipment (scheduled)"]),
        "order_region": row["Order Region"],
        "product_name": row["Product Name"],
    }

    _FLAGGED_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not _FLAGGED_CSV.exists()
    with _FLAGGED_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(record.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(record)

    return {"ok": True, "logged_to": str(_FLAGGED_CSV), "record": record}
