"""
Synthetic retail sales data generator.

Creates realistic-looking (but fully fictional) order, customer, and product
tables for a portfolio analytics project. Nothing here represents a real
company — all names, amounts, and patterns are randomly generated.

Seeded with random_state=42 so the dataset is reproducible.

Tables:
    customers.csv : ~2,500 customers (customer_id, name, region, signup_date)
    products.csv  : 60 products across 6 categories
    orders.csv    : ~12,000 orders across 2023-2024 with realistic seasonality
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RANDOM_STATE = 42
N_CUSTOMERS = 2_500
N_ORDERS = 12_000
N_PRODUCTS = 60

REGIONS = ["North", "South", "East", "West"]
CATEGORIES = ["Electronics", "Home & Kitchen", "Apparel", "Sports", "Beauty", "Toys"]
CHANNELS = ["Online", "In-Store", "Mobile App"]

FIRST_NAMES = [
    "Ava", "Liam", "Maya", "Noah", "Priya", "Ethan", "Sofia", "Lucas", "Aria",
    "Mateo", "Zoe", "Oliver", "Ivy", "Elijah", "Nora", "Leo", "Hannah", "Owen",
    "Lily", "Caleb", "Ruby", "Daniel", "Chloe", "Henry", "Mila", "Owen",
]
LAST_NAMES = [
    "Smith", "Garcia", "Patel", "Kim", "Johnson", "Nguyen", "Brown", "Davis",
    "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Hernandez",
    "Lee", "Walker", "Hall", "Allen", "Young",
]
CITIES = {
    "North": ["Chicago", "Minneapolis", "Detroit", "Cleveland"],
    "South": ["Dallas", "Atlanta", "Houston", "Miami"],
    "East": ["Boston", "New York", "Philadelphia", "Washington"],
    "West": ["Seattle", "San Francisco", "Denver", "Los Angeles"],
}
PRODUCT_ADJECTIVES = [
    "Deluxe", "Pro", "Classic", "Premium", "Eco", "Compact", "Ultra", "Essential",
]
PRODUCT_NOUNS = {
    "Electronics": ["Headphones", "Speaker", "Charger", "Smart Watch", "Tablet Stand"],
    "Home & Kitchen": ["Blender", "Cookware Set", "Lamp", "Throw Pillow", "Organizer"],
    "Apparel": ["Jacket", "Sneakers", "T-Shirt", "Jeans", "Backpack"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Water Bottle", "Tent", "Bike Light"],
    "Beauty": ["Serum", "Moisturizer", "Hair Dryer", "Fragrance", "Brush Set"],
    "Toys": ["Building Blocks", "Puzzle", "RC Car", "Dollhouse", "Board Game"],
}

CATEGORY_PRICE = {
    "Electronics": (80, 300),
    "Home & Kitchen": (25, 150),
    "Apparel": (20, 120),
    "Sports": (15, 180),
    "Beauty": (10, 90),
    "Toys": (12, 80),
}


def generate_customers(rng: np.random.Generator) -> pd.DataFrame:
    ids = [f"C{1000 + i}" for i in range(N_CUSTOMERS)]
    regions = rng.choice(REGIONS, size=N_CUSTOMERS, p=[0.30, 0.28, 0.22, 0.20])
    cities = [rng.choice(CITIES[r]) for r in regions]
    names = [
        f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}" for _ in range(N_CUSTOMERS)
    ]
    start = np.datetime64("2021-01-01")
    signup_days = rng.integers(0, 1095, size=N_CUSTOMERS)
    signup_dates = start + signup_days.astype("timedelta64[D]")
    df = pd.DataFrame(
        {
            "customer_id": ids,
            "customer_name": names,
            "region": regions,
            "city": cities,
            "signup_date": pd.to_datetime(signup_dates).date.astype(str),
        }
    )
    return df


def generate_products(rng: np.random.Generator) -> pd.DataFrame:
    per_cat = N_PRODUCTS // len(CATEGORIES)
    rows = []
    for i, cat in enumerate(CATEGORIES):
        nouns = PRODUCT_NOUNS[cat]
        lo, hi = CATEGORY_PRICE[cat]
        for j in range(per_cat):
            noun = nouns[j % len(nouns)]
            adj = PRODUCT_ADJECTIVES[(i * 3 + j) % len(PRODUCT_ADJECTIVES)]
            rows.append(
                {
                    "product_id": f"P{i * per_cat + j + 1:03d}",
                    "product_name": f"{adj} {noun}",
                    "category": cat,
                    "unit_price": round(float(rng.uniform(lo, hi)), 2),
                }
            )
    return pd.DataFrame(rows)


def _seasonal_multiplier(dates: pd.Series) -> np.ndarray:
    """Seasonality: holiday spike in Nov/Dec, summer bump, slow February."""
    month = dates.dt.month.to_numpy()
    mult = np.ones(len(dates))
    mult = np.where(np.isin(month, [11, 12]), 1.9, mult)
    mult = np.where(np.isin(month, [6, 7]), 1.3, mult)
    mult = np.where(month == 2, 0.8, mult)
    return mult


def generate_orders(
    rng: np.random.Generator, customers: pd.DataFrame, products: pd.DataFrame
) -> pd.DataFrame:
    order_ids = [f"O{100000 + i}" for i in range(N_ORDERS)]
    start = pd.Timestamp("2023-01-01")
    # Sample order dates with seasonality weights
    all_days = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    weights = _seasonal_multiplier(pd.Series(all_days))
    weights = weights / weights.sum()
    order_days = rng.choice(all_days, size=N_ORDERS, replace=True, p=weights)

    # Repeat buyers: a loyal core drives most orders (Pareto-ish).
    # power(0.5) concentrates spend so ~2/3 of customers are repeat buyers.
    cust_ids = customers["customer_id"].to_numpy()
    loyalty = rng.power(0.5, size=len(cust_ids))
    cust_probs = loyalty / loyalty.sum()
    chosen_customers = rng.choice(cust_ids, size=N_ORDERS, p=cust_probs)

    # Products: top sellers per category sell more
    prod_ids = products["product_id"].to_numpy()
    prod_weights = rng.power(1.8, size=len(prod_ids))
    prod_weights = prod_weights / prod_weights.sum()
    chosen_products = rng.choice(prod_ids, size=N_ORDERS, p=prod_weights)
    prod_lookup = products.set_index("product_id")["unit_price"].to_dict()

    quantities = rng.choice([1, 1, 1, 2, 2, 3, 4, 5], size=N_ORDERS)
    # Discounts: 10% off is common, 20% rare; ~40% of orders have a discount
    discounts = rng.choice(
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.10, 0.10, 0.15, 0.20], size=N_ORDERS
    )
    channels = rng.choice(CHANNELS, size=N_ORDERS, p=[0.45, 0.35, 0.20])

    unit_prices = np.array([prod_lookup[p] for p in chosen_products])
    # Add small price noise to mimic promos
    unit_prices = np.round(unit_prices * rng.uniform(0.97, 1.03, size=N_ORDERS), 2)
    line_total = np.round(unit_prices * quantities * (1 - discounts), 2)

    df = pd.DataFrame(
        {
            "order_id": order_ids,
            "order_date": pd.to_datetime(order_days).strftime("%Y-%m-%d"),
            "customer_id": chosen_customers,
            "product_id": chosen_products,
            "quantity": quantities,
            "unit_price": unit_prices,
            "discount": discounts,
            "line_total": line_total,
            "channel": channels,
        }
    )
    return df.sort_values("order_date").reset_index(drop=True)


def main() -> None:
    rng = np.random.default_rng(RANDOM_STATE)
    customers = generate_customers(rng)
    products = generate_products(rng)
    orders = generate_orders(rng, customers, products)

    customers.to_csv("data/customers.csv", index=False)
    products.to_csv("data/products.csv", index=False)
    orders.to_csv("data/orders.csv", index=False)

    total_mb = sum(
        __import__("os").path.getsize(f"data/{f}")
        for f in ("customers.csv", "products.csv", "orders.csv")
    ) / 1e6
    print(f"customers: {len(customers):,} rows")
    print(f"products:  {len(products):,} rows")
    print(f"orders:    {len(orders):,} rows")
    print(f"total size: {total_mb:.2f} MB")


if __name__ == "__main__":
    main()
