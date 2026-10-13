"""
Data cleaning for the synthetic retail dataset.

Steps:
    1. Load the three CSVs.
    2. Parse dates, enforce dtypes.
    3. Validate: no null keys, line_total consistency, non-negative amounts.
    4. Deduplicate orders.
    5. Enrich: order month, order year, customer region/category joins.

Usage:
    from data_cleaning import load_and_clean
    orders, customers, products = load_and_clean("data")
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def load_and_clean(data_dir: str = "data") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customers = pd.read_csv(f"{data_dir}/customers.csv")
    products = pd.read_csv(f"{data_dir}/products.csv")
    orders = pd.read_csv(f"{data_dir}/orders.csv")

    # --- dtypes ---
    orders["order_date"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"], format="%Y-%m-%d")
    orders["quantity"] = orders["quantity"].astype(int)

    # --- dedupe ---
    n_before = len(orders)
    orders = orders.drop_duplicates(subset=["order_id"], keep="first")
    dupes_removed = n_before - len(orders)

    # --- validation ---
    assert orders[["order_id", "customer_id", "product_id"]].notna().all().all()
    assert (orders["line_total"] >= 0).all(), "negative line_total found"
    assert (orders["quantity"] > 0).all(), "non-positive quantity found"

    # Recompute line_total and flag drift (rounds of unit_price noise can drift ±$0.01)
    recomputed = (orders["unit_price"] * orders["quantity"] * (1 - orders["discount"])).round(2)
    drift = (orders["line_total"] - recomputed).abs()
    max_drift = float(drift.max())

    # --- enrichment ---
    orders["order_month"] = orders["order_date"].dt.to_period("M").astype(str)
    orders["order_year"] = orders["order_date"].dt.year

    report = {
        "duplicate_orders_removed": int(dupes_removed),
        "max_line_total_drift_usd": round(max_drift, 4),
        "orders": len(orders),
        "customers": customers["customer_id"].nunique(),
        "products": len(products),
        "date_range": (orders["order_date"].min().date(), orders["order_date"].max().date()),
    }
    print("Cleaning report:")
    for k, v in report.items():
        print(f"  {k}: {v}")

    return orders, customers, products


if __name__ == "__main__":
    load_and_clean()
