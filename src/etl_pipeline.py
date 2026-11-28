from pathlib import Path
import logging
import sqlite3

import pandas as pd


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

SOURCE_FILE = DATA_DIR / "Online Retail.xlsx"
OUTPUT_FILE = DATA_DIR / "online_retail_cleaned.csv"
DATABASE_FILE = DATA_DIR / "ecommerce.db"

LOG_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. LOGGING SETUP
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / "etl_pipeline.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ],
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 3. EXTRACT
# --------------------------------------------------

def extract_data():
    """Read raw Excel data from the source file."""

    logger.info("Starting extraction")

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    df = pd.read_excel(SOURCE_FILE)

    logger.info("Extracted %s rows", len(df))
    logger.info("Source columns: %s", list(df.columns))

    return df


# --------------------------------------------------
# 4. TRANSFORM
# --------------------------------------------------

def transform_data(df):
    """Clean and prepare transaction data."""

    logger.info("Starting transformation")

    df = df.copy()

    # Standardize column names
    df.columns = df.columns.str.strip()

    required_columns = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Required columns missing: {missing_columns}"
        )

    rows_before = len(df)

    # Remove exact duplicate records
    df = df.drop_duplicates().copy()

    duplicates_removed = rows_before - len(df)

    # Convert dates and numeric fields
    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="coerce"
    )

    df["Quantity"] = pd.to_numeric(
        df["Quantity"],
        errors="coerce"
    )

    df["UnitPrice"] = pd.to_numeric(
        df["UnitPrice"],
        errors="coerce"
    )

    df["CustomerID"] = pd.to_numeric(
        df["CustomerID"],
        errors="coerce"
    )

    # Remove rows missing essential fields
    essential_columns = [
        "InvoiceNo",
        "InvoiceDate",
        "CustomerID",
        "Quantity",
        "UnitPrice",
    ]

    rows_before_missing_filter = len(df)

    df = df.dropna(
        subset=essential_columns
    ).copy()

    missing_rows_removed = (
        rows_before_missing_filter - len(df)
    )

    # Customer IDs should be whole numbers
    valid_customer_ids = (
        df["CustomerID"] > 0
    ) & (
        df["CustomerID"] % 1 == 0
    )

    df = df.loc[valid_customer_ids].copy()
    df["CustomerID"] = df["CustomerID"].astype("int64")

    # Keep valid sales transactions for this project
    # This excludes cancellations/returns and zero-value lines
    df = df.loc[
        (df["Quantity"] > 0)
        & (df["UnitPrice"] > 0)
    ].copy()

    # Create revenue for each transaction line
    df["Revenue"] = (
        df["Quantity"] * df["UnitPrice"]
    ).round(2)

    # Remove any invalid calculated revenue
    df = df.loc[
        df["Revenue"].notna()
        & (df["Revenue"] > 0)
    ].copy()

    # Sort for consistent output
    df = df.sort_values(
        ["InvoiceDate", "InvoiceNo"]
    ).reset_index(drop=True)

    report = {
        "duplicates_removed": duplicates_removed,
        "missing_essential_rows_removed": missing_rows_removed,
        "rows_after_transformation": len(df),
    }

    logger.info("Transformation report: %s", report)

    return df, report


# --------------------------------------------------
# 5. VALIDATE
# --------------------------------------------------

def validate_data(df):
    """Stop the pipeline if critical checks fail."""

    logger.info("Starting data validation")

    required_columns = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
        "Revenue",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Output columns missing: {missing_columns}"
        )

    if df.empty:
        raise ValueError(
            "No rows remain after transformation"
        )

    if df[required_columns].isna().any().any():
        raise ValueError(
            "Missing values found in required output fields"
        )

    if df.duplicated().any():
        raise ValueError(
            "Duplicate rows remain after transformation"
        )

    if (df["Quantity"] <= 0).any():
        raise ValueError(
            "Non-positive quantities found"
        )

    if (df["UnitPrice"] <= 0).any():
        raise ValueError(
            "Non-positive unit prices found"
        )

    if (df["Revenue"] <= 0).any():
        raise ValueError(
            "Non-positive revenue found"
        )

    expected_revenue = (
        df["Quantity"] * df["UnitPrice"]
    ).round(2)

    if not expected_revenue.equals(df["Revenue"]):
        raise ValueError(
            "Revenue calculation validation failed"
        )

    logger.info("All critical validation checks passed")


# --------------------------------------------------
# 6. LOAD
# --------------------------------------------------

def load_data(df):
    """Load clean data to CSV and SQLite."""

    logger.info("Starting data load")

    # Load to CSV
    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # Load to SQLite
    with sqlite3.connect(DATABASE_FILE) as connection:
        df.to_sql(
            "sales",
            connection,
            if_exists="replace",
            index=False
        )

        # Verify loaded row count
        loaded_rows = pd.read_sql_query(
            "SELECT COUNT(*) AS row_count FROM sales",
            connection
        ).iloc[0]["row_count"]

    if loaded_rows != len(df):
        raise ValueError(
            f"Row count mismatch: expected {len(df)}, "
            f"loaded {loaded_rows}"
        )

    logger.info("CSV saved to %s", OUTPUT_FILE)
    logger.info("SQLite database saved to %s", DATABASE_FILE)
    logger.info("Rows loaded into SQLite: %s", loaded_rows)


# --------------------------------------------------
# 7. RUN THE PIPELINE
# --------------------------------------------------

def main():
    logger.info("========== ETL PIPELINE STARTED ==========")

    raw_data = extract_data()

    clean_data, report = transform_data(raw_data)

    validate_data(clean_data)

    load_data(clean_data)

    logger.info("Final row count: %s", len(clean_data))
    logger.info("ETL report: %s", report)
    logger.info("========== ETL PIPELINE COMPLETED ==========")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("ETL pipeline failed")
        raise