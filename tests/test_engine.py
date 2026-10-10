"""
Tests for the local engine adapter's pure logic (table parsing, type names, reply mapping)
and for what the LLM is shown after a tool call. They run inside YOUR project, because
web_app.engine imports your data/ and intelligence/ packages:

    python -m unittest discover -s tests -v          (from the project root)
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence.chatbot import ChatResult, build_observation
from web_app import engine


class TestCsvTextToTable(unittest.TestCase):
    def test_clean_csv_becomes_a_table(self):
        table = engine.csv_text_to_table("column,missing\nAge,177\nCabin,687\n")
        self.assertEqual(table["columns"], ["column", "missing"])
        self.assertEqual(table["rows"], [["Age", 177], ["Cabin", 687]])
        self.assertEqual(table["total_rows"], 2)

    def test_unquoted_commas_in_values_are_rejected_not_misaligned(self):
        text = "Name,Sex\nBraund, Mr. Owen,male\nSmith,female"
        self.assertIsNone(engine.csv_text_to_table(text))

    def test_properly_quoted_commas_are_fine(self):
        table = engine.csv_text_to_table('Name,Sex\n"Braund, Mr. Owen",male')
        self.assertEqual(table["rows"], [["Braund, Mr. Owen", "male"]])

    def test_not_tables(self):
        self.assertIsNone(engine.csv_text_to_table("just a sentence"))
        self.assertIsNone(engine.csv_text_to_table("a,b,c"))                      # header only
        self.assertIsNone(engine.csv_text_to_table("a,b\n1,2\n\nc,d\n3,4"))       # two blocks (blank line)
        self.assertIsNone(engine.csv_text_to_table("only\none\ncolumn"))          # one column

    def test_number_handling(self):
        rows = engine.csv_text_to_table("id,x,flag\n007,0.63,\n12,-3,yes")["rows"]
        self.assertEqual(rows, [["007", 0.63, None], [12, -3, "yes"]])            # '007' stays text, '' -> None

    def test_only_first_ten_rows_are_sent_but_total_is_kept(self):
        text = "n,sq\n" + "\n".join(f"{i},{i * i}" for i in range(25))
        table = engine.csv_text_to_table(text)
        self.assertEqual((len(table["rows"]), table["total_rows"]), (10, 25))


class TestDataFrameToTable(unittest.TestCase):
    def test_nan_becomes_null_and_rows_are_capped(self):
        df = pd.DataFrame({"a": range(30), "b": [np.nan] * 30})
        table = engine.dataframe_to_table(df)
        self.assertEqual((len(table["rows"]), table["total_rows"]), (10, 30))
        self.assertIsNone(table["rows"][0][1])

    def test_dates_become_text(self):
        table = engine.dataframe_to_table(pd.DataFrame({"d": pd.to_datetime(["2026-01-02"])}))
        self.assertIsInstance(table["rows"][0][0], str)


class TestSimpleDtype(unittest.TestCase):
    def test_mapping(self):
        cases = {
            "int64": "int", "Int64": "int", "float64": "float", "bool": "bool", "object": "text",
            "category": "text", "datetime64[ns]": "date", "timedelta64[ns]": "other",
        }
        for name, expected in cases.items():
            self.assertEqual(engine.simple_dtype(pd.Series([], dtype=name).dtype), expected, name)


def result(**overrides):
    base = dict(answer="Done.", dataframe=pd.DataFrame({"a": [1]}), memory=[], status="ok", last_tool=None, dataset_changed=False, last_result=None, last_chart=None)
    return ChatResult(**{**base, **overrides})


META = {"filename": "x.csv", "rows": 1, "columns": [{"name": "a", "dtype": "int"}]}


class TestBuildReply(unittest.TestCase):
    def test_plain_answer(self):
        self.assertEqual(engine.build_reply(result(), META), {"type": "final", "message": "Done."})

    def test_modifying_tool(self):
        tool = {"name": "delete_column", "modifies_dataset": True, "result": pd.DataFrame(), "figure_png": None}
        reply = engine.build_reply(result(last_tool=tool, dataset_changed=True), META)
        self.assertEqual((reply["type"], reply["dataset"]), ("modification", META))

    def test_plot(self):
        tool = {"name": "plot_histogram", "modifies_dataset": False, "result": None, "figure_png": "iVBOR"}
        reply = engine.build_reply(result(last_tool=tool), META)
        self.assertEqual((reply["type"], reply["image"], reply["alt"]), ("image", "iVBOR", "Chart: histogram"))

    def test_dataframe_and_series_results_are_tables(self):
        for value in (pd.DataFrame({"x": [1, 2]}), pd.Series([1, 2], name="x")):
            tool = {"name": "t", "modifies_dataset": False, "result": value, "figure_png": None}
            self.assertEqual(engine.build_reply(result(last_tool=tool), META)["type"], "table")

    def test_number_stays_text(self):
        tool = {"name": "calculate_statistic", "modifies_dataset": False, "result": 29.7, "figure_png": None}
        self.assertEqual(engine.build_reply(result(last_tool=tool), META)["type"], "final")

    def test_partial_adds_note_and_no_output(self):
        tool = {"name": "plot_histogram", "modifies_dataset": False, "result": None, "figure_png": "iVBOR"}
        reply = engine.build_reply(result(status="partial", last_tool=tool), META)
        self.assertEqual(reply["type"], "final")
        self.assertTrue(reply["message"].endswith("Note: this request was only partially completed."))
        self.assertNotIn("image", reply)

    def test_error_still_syncs_the_sidebar_if_the_dataset_changed(self):
        reply = engine.build_reply(result(status="error", answer="Cannot reach it.", dataset_changed=True), META)
        self.assertEqual((reply["type"], reply["dataset"]), ("error", META))


class TestWhatTheLlmSees(unittest.TestCase):
    def test_modifying_tool_shows_only_counts_and_columns(self):
        observation = build_observation(pd.DataFrame({"a": [1, 2], "b": [3, 4]}), modifies_dataset=True)
        self.assertIn("status: success", observation)
        self.assertIn("dataset modified", observation)
        self.assertIn("columns: a,b", observation)

    def test_query_dataframe_shows_csv(self):
        observation = build_observation(pd.DataFrame({"a": range(100)}), modifies_dataset=False)
        self.assertIn("100 rows x 1 columns", observation)
        self.assertIn("a\n0\n", observation)

    def test_series_is_treated_like_a_dataframe(self):
        observation = build_observation(pd.Series([5, 6], name="n"), modifies_dataset=False)
        self.assertIn("2 rows x 2 columns", observation) # index becomes a column

    def test_chart_is_only_announced(self):
        observation = build_observation(None, modifies_dataset=False, chart="test chart")
        self.assertIn("status: success", observation)
        self.assertIn("test chart", observation)

    def test_everything_else_is_unchanged(self):
        self.assertIn("a,b\n1,2", build_observation("a,b\n1,2", False))
        self.assertIn("29.7", build_observation(29.7, False))


if __name__ == "__main__":
    unittest.main()
