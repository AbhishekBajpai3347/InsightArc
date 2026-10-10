"""
Unit tests for data manipulation, encoding, validation, and intelligence tool execution.
"""

import io
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

from intelligence.executor import execute_tool
from intelligence.tool_definitions import TOOLS
from data import cleaner, encoder, loader, modify, validator
from analysis import eda, statistics, visualization


class TestToolExecution(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "age": [22, 38, 26, 35, 35, 54, 2, 27, 14, 4],
            "fare": [7.25, 71.2833, 7.925, 53.1, 8.05, 51.8625, 21.075, 11.1333, 30.0708, 16.7],
            "sex": ["male", "female", "female", "female", "male", "male", "male", "female", "female", "female"],
            "survived": [0, 1, 1, 1, 0, 0, 0, 1, 1, 1],
        })

    def test_all_registered_tools_execute(self):
        test_inputs = {
            "get_dataset_info": {},
            "get_first_or_last_n_rows": {"n": 3, "first": True},
            "get_column_info": {"column": "age"},
            "get_unique_values": {"column": "sex"},
            "get_value_counts": {"column": "sex"},
            "get_filtered_value_counts": {"column": "sex", "filter_column": "age", "operator": ">", "value": 30},
            "get_statistics": {},
            "calculate_statistic": {"column": "age", "statistic": "mean"},
            "calculate_filtered_statistic": {"column": "fare", "statistic": "mean", "filter_column": "sex", "operator": "==", "value": "female"},
            "analyze_distributions": {},
            "analyze_categorical_columns": {},
            "analyze_unique_values": {},
            "analyze_missing_data": {},
            "analyze_correlations": {},
            "groupby_aggregate": {"group_column": "sex", "value_column": "age", "aggregation": "mean"},
            "calculate_correlation": {"column1": "age", "column2": "fare"},
            "filter_rows": {"column": "age", "operator": ">", "value": 30},
            "sort_rows": {"column": "fare", "ascending": False},
            "validate_dataset": {},
            "clean_dataset": {},
            "encode_one_hot": {"columns": ["sex"]},
            "encode_ordinal": {"columns": ["sex"], "categories": "auto"},
            "plot_histogram": {"column": "age"},
            "plot_bar_chart": {"x_column": "sex", "y_column": "fare"},
            "plot_boxplot": {"column": "age"},
            "plot_scatter": {"x_column": "age", "y_column": "fare"},
            "plot_correlation_heatmap": {},
            "delete_column": {"column": "sex"},
            "rename_column": {"old_name": "sex", "new_name": "gender"},
            "select_columns": {"columns": ["age", "fare"]},
            "drop_rows": {"indices": [0, 1]},
            "update_value": {"column": "age", "row_index": 0, "value": 25},
            "add_column": {"column": "new_col", "values": list(range(10))},
            "fill_column": {"column": "age", "value": 50},
        }

        for tool_name, args in test_inputs.items():
            with self.subTest(tool=tool_name):
                self.assertIn(tool_name, TOOLS)
                res = execute_tool(self.df, tool_name, args)
                self.assertIn("result", res)
                self.assertIn("dataframe", res)
                self.assertIn("modifies_dataset", res)
                self.assertIn("figure_png", res)

    def test_plot_tools_capture_figure_png(self):
        res = execute_tool(self.df, "plot_histogram", {"column": "age"})
        self.assertIsNotNone(res["figure_png"])
        self.assertTrue(res["figure_png"].startswith("iVBOR"))

    def test_invalid_tool_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            execute_tool(self.df, "non_existent_tool", {})


class TestDataCleaningAndValidation(unittest.TestCase):
    def test_cleaner_handles_missing_and_duplicates(self):
        dirty_df = pd.DataFrame({
            " Name ": [" Alice ", " Bob ", " Charlie ", " David ", " Alice "],
            "Age": [25.0, np.nan, 30.0, 40.0, 25.0],
            "AllNull": [np.nan, np.nan, np.nan, np.nan, np.nan],
        })
        cleaned = cleaner.clean_dataset(dirty_df)
        self.assertNotIn("allnull", cleaned.columns)
        self.assertEqual(len(cleaned), 4)
        self.assertIn("age", cleaned.columns)
        self.assertFalse(cleaned["age"].isna().any())

    def test_validator_returns_serializable_dict(self):
        df = pd.DataFrame({
            "a": [1, None, 3],
            "b": ["x", "y", "x"],
        })
        report = validator.validate_dataset(df)
        self.assertIn("structure", report)
        self.assertIn("missing_values", report)
        self.assertIsInstance(report["missing_values"]["null_percentages"], dict)


if __name__ == "__main__":
    unittest.main()
