"""Seeded synthetic dataset for the SQL-agent eval (no real or proprietary data)."""

from __future__ import annotations

import datetime
import random
import sqlite3
from pathlib import Path

DEFAULT_SEED = 20261103
REGIONS = ["north", "south", "east", "west"]
SEGMENTS = ["retail", "smb", "enterprise"]
STATUSES = ["paid", "refunded", "pending"]

SCHEMA = """customers(id INTEGER PRIMARY KEY, region TEXT, segment TEXT)
orders(id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, order_date TEXT 'YYYY-MM-DD', status TEXT)
regions: north, south, east, west; segments: retail, smb, enterprise; statuses: paid, refunded, pending"""


def build_db(path: str | Path, seed: int = DEFAULT_SEED, customers: int = 120, orders: int = 800) -> Path:
    path = Path(path)
    if path.exists():
        path.unlink()
    rng = random.Random(seed)
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, region TEXT, segment TEXT)")
        conn.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, "
            "order_date TEXT, status TEXT)"
        )
        conn.executemany(
            "INSERT INTO customers VALUES (?,?,?)",
            [(i, rng.choice(REGIONS), rng.choice(SEGMENTS)) for i in range(1, customers + 1)],
        )
        start = datetime.date(2023, 1, 1).toordinal()
        span = datetime.date(2024, 12, 31).toordinal() - start
        active = max(1, int(customers * 0.85))  # the rest never order
        rows = []
        for i in range(1, orders + 1):
            day = datetime.date.fromordinal(start + rng.randint(0, span)).isoformat()
            status = rng.choices(STATUSES, weights=[6, 2, 2])[0]
            rows.append((i, rng.randint(1, active), round(rng.uniform(5, 1200), 2), day, status))
        conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", rows)
        conn.commit()
    finally:
        conn.close()
    return path
