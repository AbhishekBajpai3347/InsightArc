# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np


def validate_structure(df: pd.DataFrame) -> dict:
    if len(df.index) == 0:
        raise ValueError("DataFrame is empty")
    return {
        "row_count": len(df.index),
        "column_count": len(df.columns),
        "duplicate_columns": df.columns[df.columns.duplicated()].tolist(),
    }


def validate_missing_values(df: pd.DataFrame) -> dict:
    null_series = df.isnull().sum()
    null_count = dict(null_series)
    null_percentages = ((null_series / len(df.index)) * 100).to_dict()
    return {
        "null_value_mean": float(df.isnull().sum().mean()),
        "null_value_counts": {k: v.item() for k, v in null_count.items()},
        "null_percentages": null_percentages,
    }


def validate_duplicate_values(df: pd.DataFrame) -> dict:
    return {"duplicate_rows": df.duplicated().sum().item()}


def validate_datatypes(df: pd.DataFrame) -> dict:
    mixed_types = {}
    for col in df:
        types = df[col].dropna().map(type).unique()
        if len(types) > 1:
            mixed_types[col] = [t.__name__ for t in types]
    return {"type_issues": mixed_types}


def calculate_quality_score(
    df: pd.DataFrame,
    null_values: float,
    duplicate_values: int,
    data_type_count_issues: int,
) -> dict:
    quality_score = 1 - (1 / (3 * len(df.index))) * (
        0.35 * null_values
        + 0.1 * duplicate_values
        + 0.55 * data_type_count_issues
    )
    return {"quality_score": quality_score}


def validate_dataset(df: pd.DataFrame, *args, **kwargs) -> dict:
    structure = validate_structure(df)
    missing_values = validate_missing_values(df)
    duplicate_values = validate_duplicate_values(df)
    datatypes = validate_datatypes(df)
    quality_score = calculate_quality_score(
        df,
        missing_values["null_value_mean"],
        duplicate_values["duplicate_rows"],
        len(datatypes["type_issues"]),
    )
    return {
        "structure": structure,
        "missing_values": missing_values,
        "duplicates": duplicate_values,
        "datatypes": datatypes,
        "quality": quality_score,
    }
