# -*- coding: utf-8 -*-
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder


def encode_one_hot(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    encoder.set_output(transform="pandas")
    encoded_df = encoder.fit_transform(df[columns])
    df = df.drop(columns, axis=1)
    return pd.concat([df, encoded_df], axis=1)


def encode_ordinal(
    df: pd.DataFrame, columns: list[str], categories: list[list[str]] | str
) -> pd.DataFrame:
    encoder = OrdinalEncoder(
        categories=categories,
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )
    df[columns] = encoder.fit_transform(df[columns])
    return df
