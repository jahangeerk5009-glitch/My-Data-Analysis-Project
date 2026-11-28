import sys
import sqlite3
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_quality import run_data_quality_checks


class TestDataQuality(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        self.sample = pd.DataFrame({
            "InvoiceNo": ["10001", "10002"],
            "InvoiceDate": [
                "2026-01-01 10:00:00",
                "2026-01-02 11:00:00"
            ],
            "CustomerID": [101, 102],
            "Quantity": [2, 3],
            "UnitPrice": [10.0, 5.0],
            "Revenue": [20.0, 15.0]
        })

        self.save_sales(self.sample)

    def tearDown(self):
     print("Deleting:", self.db_path)

     import gc
     gc.collect()

     self.temp_dir.cleanup()

    def save_sales(self, dataframe):
        with sqlite3.connect(self.db_path) as connection:
            dataframe.to_sql(
                "sales",
                connection,
                if_exists="replace",
                index=False
            )

    def test_valid_data_passes(self):
        with patch("data_quality.DB_PATH", self.db_path):
            result = run_data_quality_checks()

        self.assertEqual(len(result), 2)

    def test_invalid_quantity_fails(self):
        bad_data = self.sample.copy()
        bad_data.loc[0, "Quantity"] = -2
        bad_data.loc[0, "Revenue"] = -20.0
        self.save_sales(bad_data)

        with patch("data_quality.DB_PATH", self.db_path):
            with self.assertRaises(ValueError):
                run_data_quality_checks()

    def test_wrong_revenue_fails(self):
        bad_data = self.sample.copy()
        bad_data.loc[0, "Revenue"] = 999.0
        self.save_sales(bad_data)

        with patch("data_quality.DB_PATH", self.db_path):
            with self.assertRaises(ValueError):
                run_data_quality_checks()


if __name__ == "__main__":
    unittest.main()