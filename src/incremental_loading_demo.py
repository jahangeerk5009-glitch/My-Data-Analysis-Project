import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = PROJECT_ROOT / "data" / "online_retail_cleaned.csv"

# Separate demo database: the original database stays untouched.
DB_PATH = PROJECT_ROOT / "data" / "incremental_demo.db"

BATCH_SIZE = 100


def make_row_hash(row):
    """Create a stable key to prevent loading the same row twice."""
    row_json = json.dumps(
        row,
        sort_keys=True,
        default=str
    )

    return hashlib.sha256(
        row_json.encode("utf-8")
    ).hexdigest()


def load_batch(batch_number):
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned CSV not found: {CSV_PATH}"
        )

    data = pd.read_csv(CSV_PATH)

    required = [
        "InvoiceNo",
        "CustomerID",
        "InvoiceDate",
        "Quantity",
        "UnitPrice",
        "Revenue",
        "Country"
    ]

    missing = [
        column for column in required
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns in CSV: {missing}"
        )

    start = (batch_number - 1) * BATCH_SIZE
    end = start + BATCH_SIZE
    batch = data.iloc[start:end].copy()

    if batch.empty:
        raise ValueError(
            f"Batch {batch_number} contains no rows."
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sales_incremental (
                row_hash TEXT PRIMARY KEY,
                InvoiceNo TEXT,
                CustomerID INTEGER,
                InvoiceDate TEXT,
                Quantity REAL,
                UnitPrice REAL,
                Revenue REAL,
                Country TEXT
            )
        """)

        inserted = 0

        for _, row in batch.iterrows():
            record = {
                column: row[column]
                for column in required
            }

            row_hash = make_row_hash(record)

            cursor = connection.execute("""
                INSERT OR IGNORE INTO sales_incremental (
                    row_hash,
                    InvoiceNo,
                    CustomerID,
                    InvoiceDate,
                    Quantity,
                    UnitPrice,
                    Revenue,
                    Country
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_hash,
                str(row["InvoiceNo"]),
                int(row["CustomerID"]),
                str(row["InvoiceDate"]),
                float(row["Quantity"]),
                float(row["UnitPrice"]),
                float(row["Revenue"]),
                str(row["Country"])
            ))

            inserted += cursor.rowcount

        total = connection.execute(
            "SELECT COUNT(*) FROM sales_incremental"
        ).fetchone()[0]

    print(f"Batch number: {batch_number}")
    print(f"Rows in this batch: {len(batch)}")
    print(f"New rows inserted: {inserted}")
    print(f"Total rows in demo database: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        type=int,
        choices=[1, 2],
        required=True,
        help="Load batch 1 or batch 2"
    )

    args = parser.parse_args()
    load_batch(args.batch)