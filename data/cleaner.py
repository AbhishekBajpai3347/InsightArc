# -*- coding: utf-8 -*-
import re
import numpy as np
import pandas as pd

NULL_THRESHOLD = 0.3


def remove_duplicate_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates()
    return df


def remove_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    duplicated_columns = df.columns.duplicated()
    columns_to_drop = df.columns[duplicated_columns]
    df = df.drop(columns=columns_to_drop)
    return df


def standardize_text(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.select_dtypes(include=["object", "string"]):
        df[column] = df[column].str.strip().str.lower()
    return df


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    # If its a time series value use ffill
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            df[column] = df[column].fillna(df[column].median())
        else:
            mode_val = df[column].mode()
            if not mode_val.empty:
                df[column] = df[column].fillna(mode_val[0])
    return df


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [re.sub(r'\W+', '_', column.lower()).strip('_') for column in df.columns]
    return df


def drop_null_columns(df: pd.DataFrame) -> pd.DataFrame:
    df_series = df.isnull().sum()
    df_series = df_series[df_series > len(df.index) * NULL_THRESHOLD]
    df = df.drop(df_series.index, axis=1)
    return df



def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = (
        df.pipe(remove_duplicate_columns)
        .pipe(remove_duplicate_rows)
        .pipe(standardize_text)
        .pipe(standardize_column_names)
        .pipe(drop_null_columns)
        .pipe(fill_missing_values)
    )
    return df
