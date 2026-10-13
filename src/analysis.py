"""
KPI functions for the sales & customer analytics project.

All functions take cleaned DataFrames (see data_cleaning.load_and_clean)
and return tidy DataFrames / scalars suitable for reporting and charts.
"""
from __future__ import annotations

import pandas as pd

AS_OF_DATE = pd.Timestamp("2024-12-31")


def total_revenue(orders: pd.DataFrame) -> float:
    return float(orders["line_total"].sum())


def average_order_value(orders: pd.DataFrame) -> float:
    return float(orders["line_total"].mean())


def total_orders(orders: pd.DataFrame) -> int:
    return int(len(orders))


def unique_customers(orders: pd.DataFrame) -> int:
    return int(orders["customer_id"].nunique())


def monthly_revenue(orders: pd.DataFrame) -> pd.DataFrame:
    out = (
        orders.groupby("order_month", as_index=False)
        .agg(revenue=("line_total", "sum"), orders=("order_id", "count"))
        .sort_values("order_month")
    )
    return out


def revenue_by_region(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    merged = orders.merge(customers[["customer_id", "region"]], on="customer_id", how="left")
    return (
        merged.groupby("region", as_index=False)
        .agg(revenue=("line_total", "sum"), orders=("order_id", "count"),
             customers=("customer_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )


def revenue_by_category(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    merged = orders.merge(products[["product_id", "category"]], on="product_id", how="left")
    return (
        merged.groupby("category", as_index=False)
        .agg(revenue=("line_total", "sum"), orders=("order_id", "count"),
             avg_order_value=("line_total", "mean"))
        .sort_values("revenue", ascending=False)
    )


def top_products(orders: pd.DataFrame, products: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    merged = orders.merge(products, on="product_id", how="left")
    return (
        merged.groupby(["product_id", "product_name", "category"], as_index=False)
        .agg(revenue=("line_total", "sum"), units=("quantity", "sum"),
             orders=("order_id", "count"))
        .sort_values("revenue", ascending=False)
        .head(n)
    )


def repeat_customer_stats(orders: pd.DataFrame) -> dict:
    per_customer = orders.groupby("customer_id").agg(
        orders=("order_id", "count"), revenue=("line_total", "sum")
    )
    repeaters = per_customer[per_customer["orders"] > 1]
    repeat_rate = len(repeaters) / len(per_customer)
    repeater_revenue_share = repeaters["revenue"].sum() / per_customer["revenue"].sum()
    return {
        "repeat_rate": float(repeat_rate),
        "repeater_revenue_share": float(repeater_revenue_share),
        "repeat_customers": int(len(repeaters)),
        "one_time_customers": int(len(per_customer) - len(repeaters)),
    }


def yoy_monthly_growth(orders: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly_revenue(orders).copy()
    monthly["year"] = monthly["order_month"].str[:4].astype(int)
    monthly["month"] = monthly["order_month"].str[5:7]
    pivot = monthly.pivot(index="month", columns="year", values="revenue")
    if 2023 in pivot.columns and 2024 in pivot.columns:
        pivot["yoy_growth_pct"] = (pivot[2024] - pivot[2023]) / pivot[2023] * 100
    return pivot.reset_index()


def rfm_segmentation(orders: pd.DataFrame, as_of: pd.Timestamp = AS_OF_DATE) -> pd.DataFrame:
    """Recency / Frequency / Monetary scores (1-5 quintiles) + segment labels."""
    rfm = orders.groupby("customer_id").agg(
        recency_days=("order_date", lambda s: (as_of - s.max()).days),
        frequency=("order_id", "count"),
        monetary=("line_total", "sum"),
    )
    rfm["r_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    def label(row) -> str:
        if row["rfm_score"] >= 13:
            return "Champions"
        if row["rfm_score"] >= 11:
            return "Loyal Customers"
        if row["rfm_score"] >= 9:
            return "Potential Loyalists"
        if row["rfm_score"] >= 7:
            return "At Risk"
        return "Lost / Inactive"

    rfm["segment"] = rfm.apply(label, axis=1)
    return rfm.reset_index()


def customer_lifetime_value_by_segment(rfm: pd.DataFrame) -> pd.DataFrame:
    return (
        rfm.groupby("segment", as_index=False)
        .agg(customers=("customer_id", "count"), avg_monetary=("monetary", "mean"))
        .sort_values("avg_monetary", ascending=False)
    )


def channel_performance(orders: pd.DataFrame) -> pd.DataFrame:
    return (
        orders.groupby("channel", as_index=False)
        .agg(revenue=("line_total", "sum"), orders=("order_id", "count"),
             avg_order_value=("line_total", "mean"))
        .sort_values("revenue", ascending=False)
    )
