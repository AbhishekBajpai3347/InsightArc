import pandas as pd
from typing import Any


def delete_column(
    df: pd.DataFrame,
    column: str,
) -> pd.DataFrame:
    """Delete a column from the dataset."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    return df.drop(columns=[column]).copy()


def rename_column(
    df: pd.DataFrame,
    old_name: str,
    new_name: str,
) -> pd.DataFrame:
    """Rename a column in the dataset."""
    if old_name not in df.columns:
        raise ValueError(f"Column '{old_name}' does not exist in the dataset.")

    if new_name in df.columns and new_name != old_name:
        raise ValueError(f"Column '{new_name}' already exists in the dataset.")

    return df.rename(columns={old_name: new_name}).copy()


def select_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Keep only the specified columns in the dataset."""
    missing_columns = [column for column in columns if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Columns do not exist in the dataset: {missing_columns}")

    return df.loc[:, columns].copy()


def drop_rows(
    df: pd.DataFrame,
    indices: list[int],
) -> pd.DataFrame:
    """Drop rows using their DataFrame index labels."""
    missing_indices = [index for index in indices if index not in df.index]

    if missing_indices:
        raise ValueError(f"Row indices do not exist in the dataset: {missing_indices}")

    return df.drop(index=indices).copy()


def update_value(
    df: pd.DataFrame,
    column: str,
    row_index: int,
    value: Any,
) -> pd.DataFrame:
    """Update a single cell in the dataset."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    if row_index not in df.index:
        raise ValueError(f"Row index '{row_index}' does not exist in the dataset.")

    updated_df = df.copy()
    updated_df.at[row_index, column] = value

    return updated_df


def add_column(
    df: pd.DataFrame,
    column: str,
    values: list[Any],
) -> pd.DataFrame:
    """Add a new column to the dataset."""
    if column in df.columns:
        raise ValueError(f"Column '{column}' already exists in the dataset.")

    if not hasattr(values, "__len__"):
        raise ValueError("Values must be an iterable with one value per row.")

    if len(values) != len(df):
        raise ValueError(
            f"Expected {len(df)} values to match dataset rows, got {len(values)}."
        )

    updated_df = df.copy()
    updated_df[column] = list(values)

    return updated_df


def fill_column(
    df: pd.DataFrame,
    column: str,
    value: Any,
) -> pd.DataFrame:
    """Fill an entire column with the specified value."""
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist in the dataset.")

    updated_df = df.copy()
    updated_df[column] = value

    return updated_df
