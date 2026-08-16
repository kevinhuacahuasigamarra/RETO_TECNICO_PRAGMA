import unittest
from decimal import Decimal

import pandas as pd

from src.statistics import batch_statistics


class TestBatchStatistics(unittest.TestCase):
    def test_statistics_ignore_null_price_but_count_all_rows(self):
        df = pd.DataFrame(
            {
                "timestamp": ["1/1/2012", "1/2/2012", "1/3/2012"],
                "price": [10.0, None, 30.0],
                "user_id": [1, 2, 3],
            }
        )

        result = batch_statistics(df)

        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["valid_price_count"], 2)
        self.assertEqual(result["price_sum"], Decimal("40.0"))
        self.assertEqual(result["min_price"], Decimal("10.0"))
        self.assertEqual(result["max_price"], Decimal("30.0"))


if __name__ == "__main__":
    unittest.main()
