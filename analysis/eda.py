import pandas as pd


def analyze_distributions(df: pd.DataFrame) -> str:
    numerical_df = df.select_dtypes(include="number")

    result = pd.DataFrame(
        {
            "skewness": numerical_df.skew().round(3),
            "kurtosis": numerical_df.kurt().round(3),
        }
    )

    lines = ["column,skewness,kurtosis"]

    for column, row in result.iterrows():
        lines.append(f"{column},{row['skewness']},{row['kurtosis']}")

    return "\n".join(lines)


def analyze_categorical_columns(df: pd.DataFrame) -> str:
    categorical_df = df.select_dtypes(include=["object", "string", "category"])

    results = []

    for column in categorical_df.columns:
        counts = categorical_df[column].value_counts()
        percentages = categorical_df[column].value_counts(normalize=True) * 100

        for value in counts.index:
            results.append(
                {
                    "column": column,
                    "value": value,
                    "count": counts[value],
                    "percentage": round(percentages[value], 2),
                }
            )

    lines = ["column,value,count,percentage"]

    for row in results:
        lines.append(
            f"{row['column']},{row['value']},{row['count']},{row['percentage']}"
        )

    return "\n".join(lines)


def analyze_unique_values(df: pd.DataFrame) -> str:
    results = df.nunique()

    lines = ["column,unique_count"]

    for column, count in results.items():
        lines.append(f"{column},{count}")

    return "\n".join(lines)


def analyze_missing_data(df: pd.DataFrame) -> str:
    missing_counts = df.isnull().sum()
    missing_percentages = (missing_counts / len(df)) * 100

    lines = ["column,missing_count,missing_percentage"]

    for column in df.columns:
        lines.append(
            f"{column},{missing_counts[column]},{missing_percentages[column]:.2f}"
        )

    return "\n".join(lines)


def analyze_correlations(df: pd.DataFrame) -> str:
    numerical_df = df.select_dtypes(include="number")
    result = numerical_df.corr()

    lines = ["column," + ",".join(result.columns)]

    for column, row in result.iterrows():
        values = ",".join(str(round(value, 3)) for value in row)
        lines.append(f"{column},{values}")

    return "\n".join(lines)


def generate_eda_summary(df: pd.DataFrame) -> dict:
    """Return a combined EDA summary dict for all analysis dimensions."""
    return {
        "distributions": analyze_distributions(df),
        "categorical_analysis": analyze_categorical_columns(df),
        "unique_values": analyze_unique_values(df),
        "missing_data": analyze_missing_data(df),
        "correlations": analyze_correlations(df),
    }
