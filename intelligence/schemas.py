from typing import Any, Literal
from pydantic import BaseModel, Field

# ============================================================
# DATASET INFORMATION
# ============================================================


class GetColumnInfoRequest(BaseModel):
    column: str = Field(
        ...,
        description="Exact name of the column to inspect.",
    )


class GetUniqueValuesRequest(BaseModel):
    column: str = Field(
        ...,
        description="Exact name of the column whose unique values are required.",
    )


class GetValueCountsRequest(BaseModel):
    column: str = Field(
        ...,
        description="Exact name of the column whose value frequencies are required.",
    )


class GetFilteredValueCountsRequest(BaseModel):
    column: str = Field(
        ...,
        description="Target column whose value frequencies are calculated.",
    )
    filter_column: str = Field(
        ...,
        description="Column name to apply the filter condition on.",
    )
    operator: Literal[
        "==",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
    ] = Field(
        ...,
        description="Comparison operator ('==', '!=', '>', '>=', '<', '<=').",
    )
    value: Any = Field(
        ...,
        description="Value to compare against.",
    )
    top_n: int = Field(
        default=10,
        ge=1,
        description="Number of top frequent values to return (default: 10).",
    )


class GetFirstOrLastNRows(BaseModel):
    n: int = Field(
        ..., description="Get the first n or Last n rows from dataset."
    )
    first: bool = Field(
        default=True,
        description="If set to true gives first n rows else if set to false gives last n rows.",
    )


# ============================================================
# STATISTICS
# ============================================================


class CalculateStatisticRequest(BaseModel):
    column: str = Field(
        ...,
        description="Name of the numerical column.",
    )
    statistic: Literal[
        "mean",
        "median",
        "std",
        "variance",
        "min",
        "max",
    ] = Field(
        ...,
        description="Statistic to calculate: 'mean', 'median', 'std', 'variance', 'min', or 'max'.",
    )


class CalculateFilteredStatisticRequest(BaseModel):
    column: str = Field(
        ...,
        description="Numerical column to calculate statistic on.",
    )
    statistic: Literal[
        "mean",
        "median",
        "std",
        "variance",
        "min",
        "max",
    ] = Field(
        ...,
        description="Statistic to calculate ('mean', 'median', 'std', 'variance', 'min', 'max').",
    )
    filter_column: str = Field(
        ...,
        description="Column name to apply the filter condition on.",
    )
    operator: Literal[
        "==",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
    ] = Field(
        ...,
        description="Comparison operator ('==', '!=', '>', '>=', '<', '<=').",
    )
    value: Any = Field(
        ...,
        description="Value to compare against.",
    )


# ============================================================
# GROUPING / RELATIONSHIPS
# ============================================================


class GroupByAggregateRequest(BaseModel):
    group_column: str = Field(
        ...,
        description="Column used to group the dataset (e.g. 'pclass', 'sex', 'category').",
    )
    value_column: str = Field(
        ...,
        description="Column on which the numerical aggregation is performed (e.g. 'survived', 'fare', 'age').",
    )
    aggregation: Literal[
        "mean",
        "median",
        "sum",
        "min",
        "max",
        "count",
    ] = Field(
        ...,
        description="Aggregation method: 'mean', 'median', 'sum', 'min', 'max', or 'count'.",
    )


class CalculateCorrelationRequest(BaseModel):
    column1: str = Field(
        ...,
        description="First numerical column name.",
    )
    column2: str = Field(
        ...,
        description="Second numerical column name.",
    )


# ============================================================
# DATA QUERIES
# ============================================================


class FilterRowsRequest(BaseModel):
    column: str = Field(
        ...,
        description="Column name on which the condition is applied.",
    )
    operator: Literal[
        "==",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
    ] = Field(
        ...,
        description="Comparison operator ('==', '!=', '>', '>=', '<', '<=').",
    )
    value: Any = Field(
        ...,
        description="Value used for comparison (number, string, boolean).",
    )


class SortRowsRequest(BaseModel):
    column: str = Field(
        ...,
        description="Column name used for sorting.",
    )
    ascending: bool = Field(
        default=True,
        description="True for ascending order (default), False for descending order.",
    )


# ============================================================
# VISUALIZATION
# ============================================================


class HistogramRequest(BaseModel):
    column: str = Field(
        ...,
        description="Numerical column to visualize as a histogram.",
    )
    title: str = Field(
        default="Histogram",
        description="Title of the plot.",
    )
    xlabel: str = Field(
        default="X",
        description="Label for the X axis.",
    )
    ylabel: str = Field(
        default="Frequency",
        description="Label for the Y axis.",
    )
    bins: int = Field(
        default=30,
        ge=1,
        description="Number of histogram bins (default: 30).",
    )
    color: str = Field(
        default="blue",
        description="Color of the histogram bars.",
    )
    edgecolor: str = Field(
        default="black",
        description="Color of the bar edges.",
    )
    alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Transparency of the bars.",
    )

class BarChartRequest(BaseModel):
    x_column: str = Field(
        ...,
        description="Column to use for the X axis of the bar chart.",
    )
    y_column: str = Field(
        ...,
        description="Column containing the values to plot on the Y axis. This should normally be an already-computed or aggregated metric.",
    )
    title: str = Field(
        default="Bar Chart",
        description="Title of the plot.",
    )
    xlabel: str = Field(
        default="X",
        description="Label for the X axis.",
    )
    ylabel: str = Field(
        default="Y",
        description="Label for the Y axis.",
    )
    color: str = Field(
        default="blue",
        description="Color of the bars.",
    )
    edgecolor: str = Field(
        default="black",
        description="Color of the bar edges.",
    )
    alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Transparency of the bars.",
    )



class BoxplotRequest(BaseModel):
    column: str = Field(
        ...,
        description="Numerical column to visualize with a box plot.",
    )
    title: str = Field(
        default="Box Plot",
        description="Title of the plot.",
    )
    xlabel: str = Field(
        default="X",
        description="Label for the X axis.",
    )
    ylabel: str = Field(
        default="Y",
        description="Label for the Y axis.",
    )
    color: str = Field(
        default="blue",
        description="Face color of the box.",
    )
    alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Transparency of the box.",
    )


class ScatterPlotRequest(BaseModel):
    x_column: str = Field(
        ...,
        description="Numerical column for the X axis.",
    )
    y_column: str = Field(
        ...,
        description="Numerical column for the Y axis.",
    )
    title: str = Field(
        default="Scatter Plot",
        description="Title of the plot.",
    )
    xlabel: str = Field(
        default="X",
        description="Label for the X axis.",
    )
    ylabel: str = Field(
        default="Y",
        description="Label for the Y axis.",
    )
    color: str = Field(
        default="blue",
        description="Color of the scatter points.",
    )
    edgecolor: str = Field(
        default="black",
        description="Color of the point edges.",
    )
    alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Transparency of the points.",
    )


class CorrelationHeatmapRequest(BaseModel):
    title: str = Field(
        default="Correlation Heatmap",
        description="Title of the heatmap plot.",
    )


# ============================================================
# ENCODING
# ============================================================


class OneHotEncodeRequest(BaseModel):
    columns: list[str] = Field(
        ...,
        min_length=1,
        description="List of categorical column names to one-hot encode.",
    )


class OrdinalEncodeRequest(BaseModel):
    columns: list[str] = Field(
        ...,
        min_length=1,
        description="List of categorical column names to ordinally encode.",
    )
    categories: list[list[str]] | Literal["auto"] = Field(
        default="auto",
        description="Category ordering per column, or 'auto' to infer automatically.",
    )


# ============================================================
# DATASET MODIFICATION
# ============================================================


class DeleteColumnRequest(BaseModel):
    column: str = Field(
        ...,
        description="Name of the column to delete from the dataset.",
    )


class RenameColumnRequest(BaseModel):
    old_name: str = Field(
        ...,
        description="Current name of the column to rename.",
    )
    new_name: str = Field(
        ...,
        description="New name for the column.",
    )


class SelectColumnsRequest(BaseModel):
    columns: list[str] = Field(
        ...,
        min_length=1,
        description="List of column names to retain. All other columns will be dropped.",
    )


class DropRowsRequest(BaseModel):
    indices: list[int] = Field(
        ...,
        min_length=1,
        description="List of integer row indices to drop from the dataset.",
    )


class UpdateValueRequest(BaseModel):
    column: str = Field(
        ...,
        description="Name of the column containing the cell to update.",
    )
    row_index: int = Field(
        ...,
        description="Index of the row to update.",
    )
    value: Any = Field(
        ...,
        description="New value for the specified cell.",
    )


class AddColumnRequest(BaseModel):
    column: str = Field(
        ...,
        description="Name of the new column to add.",
    )
    values: list[Any] = Field(
        ...,
        min_length=1,
        description="List of values for the new column (must match dataset row count).",
    )


class FillColumnRequest(BaseModel):
    column: str = Field(
        ...,
        description="Name of the column to fill.",
    )
    value: Any = Field(
        ...,
        description="Value to fill across every row of the specified column.",
    )
