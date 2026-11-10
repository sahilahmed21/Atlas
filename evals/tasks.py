"""SQL-agent task suite. Ground truth is computed from the data, never hand-copied."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from dataset import REGIONS, SEGMENTS, STATUSES


@dataclass(frozen=True)
class Task:
    id: str
    question: str
    sql: str  # reference query: first column of the first row is the expected answer
    margin_sql: str | None = None  # for argmax tasks: gap between the top two (must be > 0)


def _margin(inner: str) -> str:
    return (
        f"SELECT (SELECT v FROM ({inner}) LIMIT 1) - (SELECT v FROM ({inner}) LIMIT 1 OFFSET 1)"
    )


def _build() -> list[Task]:
    tasks: list[Task] = []
    join = "orders o JOIN customers c ON c.id = o.customer_id"
    for r in REGIONS:
        tasks.append(Task(f"customers_in_{r}", f"How many customers are in the {r} region?",
                          f"SELECT count(*) FROM customers WHERE region = '{r}'"))
    for s in SEGMENTS:
        tasks.append(Task(f"paid_total_{s}",
                          f"What is the total amount of paid orders from {s} customers? (2 decimals)",
                          f"SELECT round(sum(o.amount), 2) FROM {join} WHERE o.status = 'paid' AND c.segment = '{s}'"))
    for st in STATUSES:
        tasks.append(Task(f"orders_{st}", f"How many orders have status '{st}'?",
                          f"SELECT count(*) FROM orders WHERE status = '{st}'"))
    for r in REGIONS:
        tasks.append(Task(f"avg_paid_{r}",
                          f"What is the average amount of paid orders in the {r} region, rounded to 2 decimals?",
                          f"SELECT round(avg(o.amount), 2) FROM {join} WHERE o.status = 'paid' AND c.region = '{r}'"))
    region_inner = (f"SELECT c.region k, sum(o.amount) v FROM {join} WHERE o.status = 'paid' "
                    "GROUP BY c.region ORDER BY v DESC, k")
    tasks.append(Task("top_region_paid", "Which region has the highest total amount of paid orders?",
                      f"SELECT k FROM ({region_inner}) LIMIT 1", _margin(region_inner)))
    tasks.append(Task("customers_without_orders", "How many customers have never placed an order?",
                      "SELECT count(*) FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)"))
    tasks.append(Task("max_order", "What is the largest single order amount?",
                      "SELECT max(amount) FROM orders"))
    for y in (2023, 2024):
        tasks.append(Task(f"paid_customers_{y}",
                          f"How many distinct customers placed at least one paid order in {y}?",
                          f"SELECT count(DISTINCT customer_id) FROM orders WHERE status = 'paid' AND order_date LIKE '{y}-%'"))
    seg_inner = "SELECT segment k, count(*) v FROM customers GROUP BY segment ORDER BY v DESC, k"
    tasks.append(Task("top_segment", "Which segment has the most customers?",
                      f"SELECT k FROM ({seg_inner}) LIMIT 1", _margin(seg_inner)))
    tasks.append(Task("refunded_total", "What is the total amount of refunded orders? (2 decimals)",
                      "SELECT round(sum(amount), 2) FROM orders WHERE status = 'refunded'"))
    for s in SEGMENTS:
        tasks.append(Task(f"big_paid_{s}",
                          f"How many paid orders over 500 were placed by {s} customers?",
                          f"SELECT count(*) FROM {join} WHERE o.status = 'paid' AND o.amount > 500 AND c.segment = '{s}'"))
    cust_inner = ("SELECT customer_id k, sum(amount) v FROM orders WHERE status = 'paid' "
                  "GROUP BY customer_id ORDER BY v DESC, k")
    tasks.append(Task("top_customer_paid", "Which customer id has the highest total amount of paid orders?",
                      f"SELECT k FROM ({cust_inner}) LIMIT 1", _margin(cust_inner)))
    for m in range(1, 7):
        tasks.append(Task(f"orders_2024_m{m}", f"How many orders were placed in month {m} of 2024?",
                          f"SELECT count(*) FROM orders WHERE order_date LIKE '2024-0{m}-%'"))
    tasks.append(Task("total_orders", "How many orders are there in total?", "SELECT count(*) FROM orders"))
    return tasks


TASKS: list[Task] = _build()


def _scalar(conn: sqlite3.Connection, sql: str):
    row = conn.execute(sql).fetchone()
    return None if row is None else row[0]


def _connect(db_path: str | Path) -> sqlite3.Connection:
    return sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)


def ground_truth(db_path: str | Path) -> dict[str, int | float | str]:
    conn = _connect(db_path)
    try:
        return {t.id: _scalar(conn, t.sql) for t in TASKS}
    finally:
        conn.close()


def tie_margins(db_path: str | Path) -> dict[str, float]:
    conn = _connect(db_path)
    try:
        return {t.id: _scalar(conn, t.margin_sql) for t in TASKS if t.margin_sql}
    finally:
        conn.close()


_ANSWER = re.compile(r"ANSWER:\s*(.+)", re.IGNORECASE)


def grade(expected: int | float | str, answer: str | None) -> bool:
    """Outcome grader: the last 'ANSWER: <value>' line must match the ground truth."""
    if not answer:
        return False
    found = _ANSWER.findall(answer)
    if not found:
        return False
    raw = found[-1].strip().splitlines()[0].strip().rstrip(".").lower()
    if isinstance(expected, (int, float)):
        try:
            value = float(re.sub(r"[,$\s]", "", raw))
        except ValueError:
            return False
        return abs(value - float(expected)) <= (0.005 if isinstance(expected, float) else 1e-9)
    return raw == str(expected).lower()
