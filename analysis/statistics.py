# -*- coding: utf-8 -*-
import pandas as pd


def calculate_column_metrics(series: pd.Series) -> dict:
    """Calculate summary statistics for a single numeric Series."""
    series = series.dropna()

    if series.empty:
        return {"mean": "N/A", "median": "N/A", "std": "N/A", "min": "N/A", "max": "N/A"}

    return {
        "mean": round(float(series.mean()), 2),
        "median": round(float(series.median()), 2),
        "std": round(float(series.std()), 2),
        "min": round(float(series.min()), 2),
        "max": round(float(series.max()), 2),
    }


def analyze_statistics(df: pd.DataFrame) -> str:
    """Return a compact CSV-like statistical summary of numeric columns."""
    numeric_df = df.select_dtypes(include=["number"])
    lines = [f"Rows: {len(df)}", "Column,Mean,Median,Std,Min,Max"]
    for col in numeric_df.columns:
        s = calculate_column_metrics(numeric_df[col])
        lines.append(f"{col},{s['mean']},{s['median']},{s['std']},{s['min']},{s['max']}")
    return "\n".join(lines)
