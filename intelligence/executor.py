# -*- coding: utf-8 -*-
"""
Tool execution engine with Pydantic argument validation.

CHANGE FROM THE ORIGINAL: plot tools draw on matplotlib's current figure and return
nothing, so after every tool runs we capture that figure as a PNG (base64) and return it
in a new key, "figure_png". The visualization functions themselves are untouched.

INPUT SELECTION ("source")
    Every tool still receives ONE DataFrame as its first argument. The executor decides
    which one, based on the optional "source" argument chosen by the LLM:

        source = "dataset"          (default) -> the active dataset (current_df)
        source = "previous_result"            -> the last table produced by an earlier tool

    Only tools registered with accepts_previous_result=True may use "previous_result".
    Modifying tools always work on the active dataset.

OUTPUT ("derived_result")
    If a non-modifying tool returns a DataFrame or Series (filter, sort, group, counts, ...),
    it is returned as "derived_result" so the chat loop can offer it to the next tool.
    Tool functions do not need to know anything about this.
"""

import base64
import io
import warnings
from typing import Any

import matplotlib

matplotlib.use("Agg")  # no windows: must be set before pyplot is used  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from intelligence.tool_definitions import TOOLS  # noqa: E402

FIGURE_DPI = 150
SOURCES = ("dataset", "previous_result")


def _capture_figure_png() -> str | None:
    """PNG of matplotlib's current figure as base64 text, or None if no figure exists."""
    if not plt.get_fignums():
        return None
    buffer = io.BytesIO()
    plt.gcf().savefig(buffer, format="png", dpi=FIGURE_DPI)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def series_to_dataframe(series: pd.Series) -> pd.DataFrame:
    """A Series as a two-column table (index + values), so other tools can use it by column name."""
    name = series.name if series.name is not None else "value"
    return series.to_frame(name=name).reset_index()


def choose_input(
    tool,
    source: str,
    df: pd.DataFrame,
    previous_result: pd.DataFrame | None,
) -> pd.DataFrame:
    """Return the DataFrame the tool should run on. Raises ValueError for an impossible choice."""
    if source not in SOURCES:
        raise ValueError(f"Invalid source '{source}'. Use 'dataset' or 'previous_result'.")

    if source == "dataset":
        return df

    if not tool.accepts_previous_result or tool.modifies_dataset:
        raise ValueError(
            f"Tool '{tool.name}' always works on the dataset and cannot use source='previous_result'."
        )
    if previous_result is None:
        raise ValueError(
            "There is no previous result to use. Run the analysis step first "
            "(on the dataset), then use source='previous_result'."
        )
    return previous_result


def execute_tool(
    df: pd.DataFrame,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    previous_result: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Validate arguments and execute a registered tool.

    df              : the active dataset (current_df)
    previous_result : the last table produced by an earlier tool, or None

    Returns:
        dict containing:
            - 'result': output of the tool function
            - 'dataframe': current DataFrame (updated if modifying tool)
            - 'modifies_dataset': boolean flag
            - 'figure_png': base64 PNG if the tool drew a plot, else None
            - 'derived_result': the result as a DataFrame if a non-modifying tool returned
                                a DataFrame/Series (can feed the next tool), else None
            - 'source': "dataset" or "previous_result" (what the tool ran on)
            - 'input_rows': number of rows the tool received
    """

    print(">>> Entered execute tool")
    if tool_name not in TOOLS:
        valid_tools = ", ".join(sorted(TOOLS.keys()))
        raise ValueError(
            f"Unknown tool: '{tool_name}'. Available tools: {valid_tools}"
        )

    tool = TOOLS[tool_name]
    args = arguments.copy() if arguments else {}

    # "source" is handled here, not by the tool function.
    source = args.pop("source", None) or "dataset"
    input_df = choose_input(tool, source, df, previous_result)

    # Hard safety limit for tools whose cost grows with every row (for example a bar chart
    # draws one bar per row). Checked BEFORE running, so an accidental huge request fails
    # fast with a clear message instead of running for hours.
    if tool.max_input_rows is not None and len(input_df) > tool.max_input_rows:
        raise ValueError(
            f"'{tool_name}' received {len(input_df):,} rows, more than its limit of "
            f"{tool.max_input_rows:,} rows. It draws one mark per row, so reduce the data first "
            f"(for example groupby_aggregate, get_value_counts or filter_rows) and then call "
            f"'{tool_name}' with source='previous_result'."
        )

    # Validate arguments through Pydantic schema if defined
    if tool.input_schema is not None:
        try:
            validated = tool.input_schema.model_validate(args)
            args = validated.model_dump()
        except ValidationError as e:
            # Build an actionable error message for the LLM
            error_details = []
            for err in e.errors():
                loc = " -> ".join(str(p) for p in err["loc"])
                msg = err["msg"]
                error_details.append(f"Field '{loc}': {msg}")
            raise ValueError(
                f"Invalid arguments for tool '{tool_name}': {'; '.join(error_details)}"
            ) from e
    print("Validated args")
    # Execute tool. Start with no open figures so we only ever capture THIS tool's plot,
    # and always close them afterwards, even if the tool fails half-way through a plot.
    plt.close("all")
    try:
        with warnings.catch_warnings():
            # Plot tools call plt.show(); under the Agg backend that only emits this warning.
            warnings.filterwarnings("ignore", message=".*non-interactive.*", category=UserWarning)
            print("BEFORE tool.function")
        result = tool.function(input_df, **args)
        print("AFTER tool.function")
        
        print("BEFORE capture")
        figure_png = _capture_figure_png()
        print("AFTER capture")

        if figure_png is None and isinstance(result, dict) and "image_base64" in result:
            figure_png = result["image_base64"]
    finally:
        plt.close("all")

    # Determine resulting DataFrame
    resulting_df = result if tool.modifies_dataset and isinstance(result, pd.DataFrame) else df

    # A table produced by a non-modifying tool can feed the next tool.
    # Scalars, text, dicts and charts are not tables, so they never become derived results.
    derived_result = None
    if not tool.modifies_dataset and figure_png is None:
        if isinstance(result, pd.DataFrame):
            derived_result = result
        elif isinstance(result, pd.Series):
            derived_result = series_to_dataframe(result)

    print("Returning df")
    return {
        "result": result,
        "dataframe": resulting_df,
        "modifies_dataset": tool.modifies_dataset,
        "figure_png": figure_png,
        "derived_result": derived_result,
        "source": source,
        "input_rows": len(input_df),
    }
