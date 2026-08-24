"""Research-oriented figures for the station PM2.5 audit."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_audit_figures(df: pd.DataFrame, output_dir: Path) -> None:
    """Create reproducible EDA figures without modifying observations."""
    if not {"date", "Station_No", "PM2.5"}.issubset(df.columns):
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(context="paper", style="whitegrid")

    plot_data = df.dropna(subset=["date", "Station_No"]).copy()
    plot_data["Station_No"] = plot_data["Station_No"].astype(str)
    order = sorted(plot_data["Station_No"].unique())

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(
        data=plot_data,
        x="date",
        y="PM2.5",
        hue="Station_No",
        linewidth=0.7,
        ax=ax,
    )
    ax.set(title="Hourly PM2.5 observations by station", xlabel="Time", ylabel="PM2.5")
    ax.legend(title="Station", bbox_to_anchor=(1.01, 1), loc="upper left")
    _save(fig, output_dir / "pm25_time_series.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(
        data=plot_data,
        x="PM2.5",
        hue="Station_No",
        element="step",
        stat="density",
        common_norm=False,
        bins="auto",
        ax=ax,
    )
    ax.set(title="PM2.5 distribution by station", xlabel="PM2.5", ylabel="Density")
    _save(fig, output_dir / "pm25_distribution_by_station.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(
        data=plot_data, x="Station_No", y="PM2.5", order=order, ax=ax
    )
    ax.set(title="PM2.5 by station", xlabel="Station", ylabel="PM2.5")
    _save(fig, output_dir / "pm25_boxplot_by_station.png")

    monthly = (
        plot_data.set_index("date")
        .groupby("Station_No")["PM2.5"]
        .resample("MS")
        .agg(["mean", "median"])
        .reset_index()
    )
    if not monthly.empty:
        monthly_long = monthly.melt(
            id_vars=["Station_No", "date"],
            value_vars=["mean", "median"],
            var_name="statistic",
            value_name="PM2.5",
        )
        fig, ax = plt.subplots(figsize=(11, 5))
        sns.lineplot(
            data=monthly_long,
            x="date",
            y="PM2.5",
            hue="Station_No",
            style="statistic",
            ax=ax,
        )
        ax.set(
            title="Monthly PM2.5 mean and median",
            xlabel="Month",
            ylabel="PM2.5",
        )
        ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
        _save(fig, output_dir / "pm25_monthly_statistics.png")

    plot_data["hour"] = plot_data["date"].dt.hour
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(
        data=plot_data,
        x="hour",
        y="PM2.5",
        hue="Station_No",
        estimator="median",
        errorbar=("ci", 95),
        ax=ax,
    )
    ax.set(
        title="Hourly-of-day PM2.5 pattern (median and 95% bootstrap CI)",
        xlabel="Hour of day",
        ylabel="PM2.5",
        xticks=range(0, 24, 2),
    )
    _save(fig, output_dir / "pm25_hour_of_day.png")

    plot_data["day_type"] = plot_data["date"].dt.dayofweek.ge(5).map(
        {False: "Weekday", True: "Weekend"}
    )
    if plot_data["day_type"].nunique() == 2:
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.boxplot(
            data=plot_data,
            x="Station_No",
            y="PM2.5",
            hue="day_type",
            order=order,
            showfliers=False,
            ax=ax,
        )
        ax.set(
            title="Weekday and weekend PM2.5 distributions",
            xlabel="Station",
            ylabel="PM2.5",
        )
        ax.legend(title="")
        _save(fig, output_dir / "pm25_weekday_weekend.png")

    monthly_missing = (
        plot_data.set_index("date")
        .groupby("Station_No")["PM2.5"]
        .resample("MS")
        .apply(lambda values: values.isna().mean() * 100)
        .rename("missing_percent")
        .reset_index()
    )
    if not monthly_missing.empty:
        matrix = monthly_missing.pivot(
            index="Station_No", columns="date", values="missing_percent"
        )
        fig, ax = plt.subplots(figsize=(12, 3.5))
        sns.heatmap(
            matrix,
            cmap="mako_r",
            vmin=0,
            vmax=100,
            cbar_kws={"label": "Missing PM2.5 (%)"},
            ax=ax,
        )
        ax.set(title="Monthly PM2.5 missingness", xlabel="Month", ylabel="Station")
        _save(fig, output_dir / "pm25_missingness_over_time.png")
