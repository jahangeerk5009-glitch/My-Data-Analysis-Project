from pathlib import Path
import sqlite3
import pandas as pd

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = PROJECT_ROOT / "data" / "ecommerce.db"


def run_data_quality_checks():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        sales = pd.read_sql_query(
            "SELECT * FROM sales",
            connection
        )

    required_columns = [
        "InvoiceNo",
        "InvoiceDate",
        "CustomerID",
        "Quantity",
        "UnitPrice",
        "Revenue"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in sales.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    print("\n===== DATA QUALITY REPORT =====")
    print(f"Total rows: {len(sales):,}")
    print(
        "Unique customers:",
        sales["CustomerID"].nunique()
    )

    # 1. Missing values
    missing_values = sales[required_columns].isna().sum()
    print("\nMissing values:")
    print(missing_values)

    # 2. Duplicate rows
    print(
        "\nDuplicate rows:",
        sales.duplicated().sum()
    )

    # 3. Invalid quantity and price
    print(
        "Quantity <= 0:",
        (sales["Quantity"] <= 0).sum()
    )
    print(
        "UnitPrice <= 0:",
        (sales["UnitPrice"] <= 0).sum()
    )

    # 4. Revenue calculation check
    expected_revenue = (
        sales["Quantity"] * sales["UnitPrice"]
    )

    revenue_errors = (
        (sales["Revenue"] - expected_revenue).abs()
        > 0.01
    )

    print(
        "Revenue calculation errors:",
        revenue_errors.sum()
    )

    # 5. Date validation
    dates = pd.to_datetime(
        sales["InvoiceDate"],
        errors="coerce"
    )

    print(
        "Invalid dates:",
        dates.isna().sum()
    )

    # 6. Overall status
    passed = (
        sales[required_columns].notna().all().all()
        and sales["Quantity"].gt(0).all()
        and sales["UnitPrice"].gt(0).all()
        and sales["Revenue"].gt(0).all()
        and sales.duplicated().sum() == 0
        and revenue_errors.sum() == 0
        and dates.notna().all()
    )

    print("\nQUALITY STATUS:", "PASS" if passed else "FAIL")

    if not passed:
        raise ValueError(
            "Data quality checks failed. Review the report."
        )

    return sales


if __name__ == "__main__":
    run_data_quality_checks()