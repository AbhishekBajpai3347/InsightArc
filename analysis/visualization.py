# -*- coding: utf-8 -*-
import io
import os
import base64

# Force non-interactive Agg backend before any pyplot import.
if not os.environ.get("MATPLOTLIB_INTERACTIVE", "").strip():
    import matplotlib
    matplotlib.use("Agg")

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


def _finish_plot(title="Plot"):
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    try:
        if matplotlib.get_backend().lower() not in [
            "agg",
            "module://matplotlib_inline.backend_inline",
        ]:
            plt.show()
    except Exception:
        pass

    plt.close()

    return {
        "status": "success",
        "image_base64": img_b64,
        "message": f"{title} generated successfully.",
    }


def _validate_columns(df: pd.DataFrame, columns):
    """Validate that required columns exist in the DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(
            f"Column(s) not found in DataFrame: {missing}"
        )


def plot_histogram(
    df: pd.DataFrame,
    column,
    title="Histogram",
    xlabel="X",
    ylabel="Frequency",
    bins=30,
    color="blue",
    edgecolor="black",
    alpha=0.7,
):
    _validate_columns(df, [column])

    plt.figure(figsize=(8, 5))

    plt.hist(
        df[column].dropna(),
        bins=bins,
        color=color,
        edgecolor=edgecolor,
        alpha=alpha,
    )

    plt.title(
        title,
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)

    return _finish_plot(title)


def plot_bar_chart(
    df: pd.DataFrame,
    x_column,
    y_column,
    title="Bar Chart",
    xlabel=None,
    ylabel=None,
    color="blue",
    edgecolor="black",
    alpha=0.7,
    sort_x=False,
):
    """
    Plot an existing x/y result.

    IMPORTANT:
    This function does NOT aggregate, count, or call value_counts().
    The DataFrame is expected to already contain the values to plot.
    """

    _validate_columns(df, [x_column, y_column])

    plot_df = df[[x_column, y_column]].dropna().copy()

    if sort_x:
        plot_df = plot_df.sort_values(by=x_column)

    plt.figure(figsize=(8, 5))
    plt.bar(
        plot_df[x_column],
        plot_df[y_column],
        color=color,
        edgecolor=edgecolor,
        alpha=alpha,
    )
    plt.title(
        title,
        fontsize=14,
        fontweight="bold",
    )

    plt.xlabel(
        xlabel if xlabel is not None else x_column,
        fontsize=12,
    )

    plt.ylabel(
        ylabel if ylabel is not None else y_column,
        fontsize=12,
    )
    plt.xticks(rotation=45)

    return _finish_plot(title)


def plot_count_bar_chart(
    df: pd.DataFrame,
    column,
    title="Count by Category",
    xlabel=None,
    ylabel="Count",
    color="blue",
    edgecolor="black",
    alpha=0.7,
    sort_index=True,
):
    """
    Explicitly create a frequency/count bar chart.

    This is the only bar-chart function that performs value_counts().
    """

    _validate_columns(df, [column])

    counts = df[column].dropna().value_counts(
        sort=False
    )

    if sort_index:
        try:
            counts = counts.sort_index()
        except Exception:
            pass

    plt.figure(figsize=(8, 5))

    plt.bar(
        counts.index,
        counts.values,
        color=color,
        edgecolor=edgecolor,
        alpha=alpha,
    )

    plt.title(
        title,
        fontsize=14,
        fontweight="bold",
    )

    plt.xlabel(
        xlabel if xlabel is not None else column,
        fontsize=12,
    )

    plt.ylabel(
        ylabel,
        fontsize=12,
    )

    plt.xticks(rotation=45)

    return _finish_plot(title)


def plot_boxplot(
    df: pd.DataFrame,
    column,
    title="Box Plot",
    xlabel="X",
    ylabel="Y",
    color="blue",
    alpha=0.7,
):
    _validate_columns(df, [column])

    plt.figure(figsize=(8, 5))

    plt.boxplot(
        df[column].dropna(),
        patch_artist=True,
        boxprops=dict(
            facecolor=color,
            alpha=alpha,
        ),
        medianprops=dict(color="black"),
        whiskerprops=dict(color="black"),
        capprops=dict(color="black"),
    )

    plt.title(
        title,
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)

    return _finish_plot(title)


def plot_scatter(
    df: pd.DataFrame,
    x_column,
    y_column,
    title="Scatter Plot",
    xlabel="X",
    ylabel="Y",
    color="blue",
    edgecolor="black",
    alpha=0.7,
):
    _validate_columns(df, [x_column, y_column])

    plot_df = df[[x_column, y_column]].dropna()

    plt.figure(figsize=(8, 5))

    plt.scatter(
        plot_df[x_column],
        plot_df[y_column],
        color=color,
        edgecolor=edgecolor,
        alpha=alpha,
    )

    plt.title(
        title,
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)

    return _finish_plot(title)


def plot_correlation_heatmap(
    df: pd.DataFrame,
    title="Correlation Heatmap",
):
    plt.figure(figsize=(10, 7))

    sns.heatmap(
        df.corr(numeric_only=True),
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        linewidths=0.5,
    )

    plt.title(
        title,
        fontsize=14,
        fontweight="bold",
    )

    return _finish_plot(title)
