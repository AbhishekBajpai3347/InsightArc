import pandas as pd
from typing import Any


def get_dataset_info(df: pd.DataFrame) -> str:
    """Return basic structural and type information about the dataset."""
    return "\n".join(
        [
            "row_count,column_count",
            f"{len(df)},{len(df.columns)}",
            "",
            "column,dtype",
            *[f"{col},{dtype}" for col, dtype in df.dtypes.items()],
        ]
    )


def get_first_or_last_n_rows(
    df: pd.DataFrame,
    n: int,
    first: bool,
) -> str:
    """Return the first n or last n rows of the dataset as pipe-separated values."""
    result = df.head(n) if first else df.tail(n)

    columns = ",".join(str(col) for col in result.columns)
    rows = [
        ",".join(str(value) for value in row)
        for row in result.itertuples(index=False, name=None)
    ]

    return "\n".join([columns, *rows])


def get_column_info(df: pd.DataFrame, column: str) -> str:
    """Return detailed metadata for a specific column."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    return "\n".join(
        [
            "column,dtype,non_null_count,null_count,unique_count",
            f"{column},{df[column].dtype},{df[column].notna().sum()},"
            f"{df[column].isna().sum()},{df[column].nunique()}",
        ]
    )


def get_unique_values(df: pd.DataFrame, column: str) -> str:
    """Return distinct non-null values from a column as pipe-separated values."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    return ",".join(
        str(value) for value in df[column].dropna().unique().tolist()
    )


def get_value_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return frequency counts for each value in a column."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    return (
        df[column]
        .value_counts(dropna=False)
        .rename_axis(column)
        .reset_index(name="count")
    )


def get_filtered_value_counts(
    df: pd.DataFrame,
    column: str,
    filter_column: str,
    operator: str,
    value: Any,
    top_n: int = 10,
) -> pd.DataFrame:
    """Return frequency counts of a column after filtering the dataset on another column."""
    filtered_df = filter_rows(df, filter_column, operator, value)
    if column not in filtered_df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")
    counts = filtered_df[column].value_counts(dropna=False).head(top_n)
    return counts.rename_axis(column).reset_index(name="count")


def calculate_statistic(
    df: pd.DataFrame,
    column: str,
    statistic: str,
) -> float:
    """Calculate a requested statistic for a numerical column."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' is not numerical.")

    series = df[column].dropna()
    if series.empty:
        raise ValueError(f"Column '{column}' contains only null values.")

    statistics = {
        "mean": series.mean,
        "median": series.median,
        "std": series.std,
        "variance": series.var,
        "min": series.min,
        "max": series.max,
    }

    if statistic not in statistics:
        valid_statistics = ", ".join(statistics.keys())
        raise ValueError(
            f"Unsupported statistic '{statistic}'. "
            f"Supported statistics: {valid_statistics}"
        )

    val = statistics[statistic]()
    return float(val)


def calculate_filtered_statistic(
    df: pd.DataFrame,
    column: str,
    statistic: str,
    filter_column: str,
    operator: str,
    value: Any,
) -> float:
    """Calculate a statistic on a numerical column after filtering the dataset."""
    filtered_df = filter_rows(df, filter_column, operator, value)
    return calculate_statistic(filtered_df, column, statistic)


def filter_rows(
    df: pd.DataFrame,
    column: str,
    operator: str,
    value: Any,
) -> pd.DataFrame:
    """Filter rows using a supported comparison operator with safe type coercion."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    col_series = df[column]

    # Type coercion for numerical columns when string values are passed
    if pd.api.types.is_numeric_dtype(col_series) and isinstance(value, str):
        try:
            value = float(value) if "." in value else int(value)
        except ValueError:
            pass

    operations = {
        "==": col_series == value,
        "!=": col_series != value,
        ">": col_series > value,
        ">=": col_series >= value,
        "<": col_series < value,
        "<=": col_series <= value,
    }

    if operator not in operations:
        valid_operators = ", ".join(operations.keys())
        raise ValueError(
            f"Unsupported operator '{operator}'. "
            f"Supported operators: {valid_operators}"
        )

    return df.loc[operations[operator]].copy()


def sort_rows(
    df: pd.DataFrame,
    column: str,
    ascending: bool = True,
) -> pd.DataFrame:
    """Sort the dataset by a specified column."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    return df.sort_values(
        by=column,
        ascending=ascending,
    ).copy()


def calculate_correlation(
    df: pd.DataFrame,
    column1: str,
    column2: str,
) -> float:
    """Calculate Pearson correlation between two numerical columns."""
    for column in (column1, column2):
        if column not in df.columns:
            raise ValueError(
                f"Column '{column}' does not exist in the dataset."
            )

        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Column '{column}' is not numerical.")

    correlation = df[column1].corr(df[column2])
    return float(correlation)


def groupby_aggregate(
    df: pd.DataFrame,
    group_column: str,
    value_column: str,
    aggregation: str,
) -> pd.DataFrame:
    """Group data by one column and apply an aggregation to another."""
    if group_column not in df.columns:
        raise ValueError(
            f"Group column '{group_column}' does not exist in the dataset."
        )

    if value_column not in df.columns:
        raise ValueError(
            f"Value column '{value_column}' does not exist in the dataset."
        )

    aggregations = {
        "mean": "mean",
        "median": "median",
        "sum": "sum",
        "min": "min",
        "max": "max",
        "count": "count",
    }

    if aggregation not in aggregations:
        valid_aggregations = ", ".join(aggregations.keys())
        raise ValueError(
            f"Unsupported aggregation '{aggregation}'. "
            f"Supported aggregations: {valid_aggregations}"
        )

    # For numeric aggregations, check if value column is numeric
    if aggregation in (
        "mean",
        "median",
        "sum",
        "std",
        "var",
    ) and not pd.api.types.is_numeric_dtype(df[value_column]):
        raise ValueError(
            f"Cannot calculate '{aggregation}' on non-numeric column "
            f"'{value_column}'."
        )

    return (
        df.groupby(group_column, dropna=False)[value_column]
        .agg(aggregations[aggregation])
        .reset_index()
    )
