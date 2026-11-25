from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "hmrc_payments_clean.csv"
SUPPLIER_MAPPING_PATH = ROOT / "analysis" / "supplier_name_mapping.csv"
FIGURE_DIR = ROOT / "data" / "processed" / "figures"
CORE_COLUMNS = [
    "Department family",
    "Entity",
    "Date",
    "Expense type",
    "Expense area",
    "Supplier",
    "Transaction number",
    "Amount",
    "Description",
    "Supplier Postcode",
]
YEARS = [2023, 2024, 2025]
PERIODS = pd.period_range("2023-01", "2025-12", freq="M")


def save_figure(
    fig: plt.Figure,
    name: str,
    bottom_margin: float | None = None,
) -> None:
    fig.tight_layout()
    if bottom_margin is not None:
        fig.subplots_adjust(bottom=bottom_margin)
    fig.savefig(FIGURE_DIR / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def monthly_baseline(data: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        data.groupby("period")
        .agg(
            rows=("Amount", "size"),
            debits=("Amount", lambda values: values[values > 0].sum()),
            credits=("Amount", lambda values: values[values < 0].sum()),
            net=("Amount", "sum"),
            suppliers=("Supplier group", "nunique"),
        )
        .reindex(PERIODS, fill_value=0)
    )
    return monthly


def plot_monthly_trend(monthly: pd.DataFrame) -> None:
    dates = PERIODS.to_timestamp()
    debits = monthly["debits"].to_numpy() / 1_000_000
    credits = -monthly["credits"].to_numpy() / 1_000_000
    net = monthly["net"].to_numpy() / 1_000_000

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]}
    )
    ax1.bar(
        dates,
        debits,
        width=20,
        color="#b9d8f2",
        label="Positive payment lines (gross debits)",
    )
    ax1.plot(
        dates,
        net,
        color="#075985",
        marker="o",
        markersize=3.5,
        linewidth=2,
        label="Net reported lines (debits + credits)",
    )
    ax1.set_ylim(0, max(debits) * 1.12)
    ax1.set_ylabel("£ millions")
    ax1.set_title(
        "HMRC reported payment lines by payment month, 2023–2025",
        loc="left",
        fontsize=15,
        weight="bold",
    )
    ax1.legend(frameon=True, loc="upper left")
    december_index = list(PERIODS.astype(str)).index("2023-12")
    ax1.annotate(
        "Dec 2023: £322.7m net\n(includes £138m property line)",
        xy=(dates[december_index], net[december_index]),
        xytext=(pd.Timestamp("2024-02-01"), max(debits) * 0.85),
        arrowprops={"arrowstyle": "->", "color": "#334155"},
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#cbd5e1"},
    )
    ax2.bar(
        dates,
        credits,
        width=20,
        color="#ef9a9a",
        label="Credit notes (shown as positive magnitude)",
    )
    ax2.set_ylabel("£ millions")
    ax2.set_xlabel("Payment month")
    ax2.legend(frameon=True, loc="upper left")
    for year in (2024, 2025):
        ax1.axvline(pd.Timestamp(f"{year}-01-01"), color="#64748b", linestyle="--")
        ax2.axvline(pd.Timestamp(f"{year}-01-01"), color="#64748b", linestyle="--")
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax2.get_xticklabels(), rotation=35, ha="right")
    fig.text(
        0.01,
        0.01,
        "Line-level, VAT-inclusive amounts; duplicates retained. Credit bars show absolute "
        "credit value; subtract them from debits to obtain net.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "monthly_spend_trends.png")


def plot_month_heatmap(monthly: pd.DataFrame) -> None:
    values = np.array(
        [
            [monthly.loc[pd.Period(f"{year}-{month:02d}", freq="M"), "net"] / 1_000_000
             for month in range(1, 13)]
            for year in YEARS
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(13, 3.8))
    image = ax.imshow(values, cmap="Blues", aspect="auto")
    ax.set_yticks(range(3), labels=[str(year) for year in YEARS])
    ax.set_xticks(
        range(12),
        labels=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    )
    ax.set_title(
        "Monthly net reported line amounts by calendar month (£m)",
        loc="left",
        fontsize=14,
        weight="bold",
    )
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            color = "white" if values[row, column] > values.max() * 0.55 else "#0f172a"
            ax.text(
                column,
                row,
                f"{values[row, column]:.0f}",
                ha="center",
                va="center",
                color=color,
                fontsize=8,
            )
    fig.colorbar(image, ax=ax, label="£ millions", pad=0.02)
    fig.text(
        0.01,
        0.01,
        "Net amounts include credits and retained duplicate rows; values are nominal and VAT-inclusive.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "monthly_spend_heatmap.png")


def plot_monthly_line_counts_and_median(data: pd.DataFrame) -> None:
    monthly = (
        data.groupby("period")
        .agg(
            positive_lines=("Amount", lambda values: (values > 0).sum()),
            credit_lines=("Amount", lambda values: (values < 0).sum()),
            positive_total=("Amount", lambda values: values[values > 0].sum()),
            median_positive=("Amount", lambda values: values[values > 0].median()),
        )
        .reindex(PERIODS)
    )
    dates = PERIODS.to_timestamp()
    fig, axes = plt.subplots(2, 2, figsize=(16, 9), sharex=True)
    panels = (
        (axes[0, 0], monthly["positive_lines"], "Positive payment-line count", "Lines", "#5b9bd5"),
        (axes[0, 1], monthly["credit_lines"], "Credit-line count", "Lines", "#e57373"),
        (
            axes[1, 0],
            monthly["positive_total"] / 1_000_000,
            "Gross positive payment-line total",
            "£ millions",
            "#075985",
        ),
        (
            axes[1, 1],
            monthly["median_positive"] / 1_000,
            "Median positive line amount",
            "£ thousands",
            "#15803d",
        ),
    )
    for ax, values, title, ylabel, color in panels:
        ax.plot(dates, values.to_numpy(), color=color, marker="o", markersize=3.5, linewidth=1.8)
        ax.set_title(title, loc="left", fontsize=11, weight="bold")
        ax.set_ylabel(ylabel)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.suptitle(
        "Monthly payment-line counts, positive spend, and typical line amount",
        x=0.01,
        ha="left",
        fontsize=15,
        weight="bold",
    )
    for ax in axes[1, :]:
        ax.set_xlabel("Payment month")
        plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    fig.text(
        0.01,
        0.01,
        "Counts include retained duplicate rows. Positive totals and medians use positive lines only; credits are counted separately.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "monthly_line_counts_and_median.png")


def plot_supplier_concentration(data: pd.DataFrame) -> None:
    gross = (
        data.loc[data["Amount"] > 0]
        .groupby("Supplier group")["Amount"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
    )
    shares = gross / data.loc[data["Amount"] > 0, "Amount"].sum() * 100
    cumulative = shares.cumsum()
    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(gross))
    ax.bar(x, gross.to_numpy() / 1_000_000, color="#5b9bd5")
    ax.set_ylabel("Positive payment lines (£m)")
    ax.set_xticks(x, labels=gross.index, rotation=55, ha="right")
    ax.set_title(
        "Largest supplier groups by positive reported payment lines",
        loc="left",
        fontsize=14,
        weight="bold",
    )
    ax2 = ax.twinx()
    ax2.plot(x, cumulative.to_numpy(), color="#c2410c", marker="o", linewidth=2)
    ax2.set_ylabel("Cumulative share of positive amounts (%)")
    ax2.set_ylim(0, min(100, max(30, cumulative.iloc[-1] * 1.15)))
    ax2.axhline(50, color="#c2410c", linestyle=":", linewidth=1)
    fig.text(
        0.01,
        0.01,
        "Published supplier labels are rolled up using the documented mapping; separate legal entities may share a group.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "top_supplier_concentration.png")


def plot_top_supplier_monthly_trends(data: pd.DataFrame) -> None:
    top_groups = list(
        data.loc[data["Amount"] > 0]
        .groupby("Supplier group")["Amount"]
        .sum()
        .nlargest(10)
        .index
    )
    if "Eviden group" not in top_groups:
        top_groups.append("Eviden group")
    monthly = (
        data.pivot_table(
            index="period",
            columns="Supplier group",
            values="Amount",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(index=PERIODS, columns=top_groups, fill_value=0)
    )
    dates = PERIODS.to_timestamp()
    row_count = (len(top_groups) + 1) // 2
    fig, axes = plt.subplots(row_count, 2, figsize=(17, row_count * 3.2), sharex=True)
    axes = np.asarray(axes).reshape(-1)
    for ax, supplier_group in zip(axes, top_groups):
        ax.plot(
            dates,
            monthly[supplier_group].to_numpy() / 1_000_000,
            color="#075985",
            marker="o",
            markersize=2.8,
            linewidth=1.7,
        )
        ax.axhline(0, color="#64748b", linewidth=0.7)
        ax.set_title(supplier_group, loc="left", fontsize=10, weight="bold")
        ax.set_ylabel("£ millions")
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    for ax in axes[len(top_groups) :]:
        fig.delaxes(ax)
    bottom_row = row_count - 1
    for ax in axes:
        if ax.get_subplotspec().rowspan.stop - 1 == bottom_row:
            ax.set_xlabel("Payment month")
            plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    fig.suptitle(
        "Monthly net reported spend for the 10 largest supplier groups plus Eviden",
        x=0.01,
        ha="left",
        fontsize=15,
        weight="bold",
    )
    fig.text(
        0.01,
        0.01,
        "Top 10 groups ranked by positive payment lines; Eviden is included separately from Atos. "
        "Monthly values are net of credits; each panel has its own vertical scale.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "top_supplier_monthly_trends.png", bottom_margin=0.1)


def plot_top_categories(data: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(17, 8))
    for ax, column, title in (
        (axes[0], "Expense type", "Top expense types by net amount"),
        (axes[1], "Expense area", "Top expense areas by net amount"),
    ):
        totals = data.groupby(column)["Amount"].sum().nlargest(12) / 1_000_000
        totals.sort_values().plot.barh(ax=ax, color="#2a7f9e")
        ax.set_xlabel("Net reported lines (£m)")
        ax.set_ylabel("")
        ax.set_title(title, loc="left", fontsize=12, weight="bold")
    fig.text(
        0.01,
        0.01,
        "Amounts include credits and retained duplicates; categories remain at HMRC's published labels.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "top_expense_types_and_areas.png")


def plot_top_expense_types_by_area(data: pd.DataFrame) -> None:
    top_types = data.groupby("Expense type")["Amount"].sum().nlargest(12).index
    fig, axes = plt.subplots(4, 3, figsize=(20, 17))

    for ax, expense_type in zip(axes.flat, top_types):
        area_totals = (
            data.loc[data["Expense type"] == expense_type]
            .groupby("Expense area")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )
        displayed = area_totals.head(5).copy()
        other_area_count = len(area_totals) - len(displayed)
        if other_area_count:
            displayed.loc[f"Other areas ({other_area_count})"] = area_totals.iloc[5:].sum()
        displayed = displayed.sort_values()
        displayed.plot.barh(ax=ax, color="#2a7f9e")
        ax.set_title(expense_type, loc="left", fontsize=9, weight="bold")
        ax.set_xlabel("Net reported lines (£m)", fontsize=8)
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=7)
        ax.tick_params(axis="x", labelsize=7)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda value, _: f"{value / 1_000_000:.0f}")
        )

    fig.suptitle(
        "Where the 12 largest expense types are reported",
        x=0.01,
        ha="left",
        fontsize=15,
        weight="bold",
    )
    fig.text(
        0.01,
        0.003,
        "Areas are ranked within each expense type by net amount. Top 5 shown; remaining areas are combined. "
        "Each panel has its own scale; amounts include credits and retained duplicates.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "top_expense_types_by_area.png")


def plot_change_contributors(data: pd.DataFrame) -> None:
    periods = ((2023, 2024), (2024, 2025))
    dimensions = ("Supplier group", "Expense type", "Expense area")
    fig, axes = plt.subplots(2, 3, figsize=(19, 12))
    for row_index, (start_year, end_year) in enumerate(periods):
        for column_index, dimension in enumerate(dimensions):
            ax = axes[row_index, column_index]
            annual = data.pivot_table(
                index=dimension,
                columns="year",
                values="Amount",
                aggfunc="sum",
                fill_value=0,
            ).reindex(columns=YEARS, fill_value=0)
            delta = annual[end_year] - annual[start_year]
            selected_indices = dict.fromkeys(
                [*delta.nlargest(5).index, *delta.nsmallest(5).index]
            )
            selected = delta.loc[list(selected_indices)]
            selected = selected.sort_values()
            colors = ["#c2410c" if value < 0 else "#15803d" for value in selected]
            ax.barh(selected.index, selected.to_numpy() / 1_000_000, color=colors)
            ax.axvline(0, color="#334155", linewidth=0.8)
            ax.set_title(
                f"{dimension}: {start_year} to {end_year}",
                loc="left",
                fontsize=10,
                weight="bold",
            )
            ax.set_xlabel("Change in net amount (£m)")
            ax.tick_params(axis="y", labelsize=7)
    fig.suptitle(
        "Largest year-over-year changes in net reported spend by supplier group, expense type, and expense area",
        x=0.01,
        ha="left",
        fontsize=15,
        weight="bold",
    )
    fig.text(
        0.01,
        0.01,
        "Green = increase; orange = decrease. Supplier labels use the documented group mapping.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "annual_change_contributors.png")


def plot_amount_distributions(data: pd.DataFrame) -> None:
    positive = data.loc[data["Amount"] > 0, "Amount"]
    credits = -data.loc[data["Amount"] < 0, "Amount"]
    minimum_amount = min(positive.min(), credits.min())
    maximum_amount = max(positive.max(), credits.max())
    bins = np.logspace(np.log10(minimum_amount), np.log10(maximum_amount), 40)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(positive, bins=bins, color="#5b9bd5", alpha=0.9)
    axes[0].axvline(25_000, color="#c2410c", linestyle="--", label="£25,000 reference")
    axes[0].set_title("Positive line amounts", loc="left", weight="bold")
    axes[0].set_xlabel("Amount (£, logarithmic scale)")
    axes[0].set_ylabel("Number of lines")
    axes[0].legend()
    axes[1].hist(credits, bins=bins, color="#e57373", alpha=0.9)
    axes[1].set_title("Credit magnitudes", loc="left", weight="bold")
    axes[1].set_xlabel("Absolute credit amount (£, logarithmic scale)")
    axes[1].set_ylabel("Number of lines")
    for ax in axes:
        ax.set_xscale("log")
    fig.text(
        0.01,
        0.01,
        "Log scales are used to show the long tails. The £25,000 line is for reference only, not a row filter.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "amount_distributions.png")


def plot_correlations(data: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(19, 15))
    for row_index, dimension in enumerate(("Supplier group", "Expense type")):
        totals = data.groupby(dimension)["Amount"].sum().nlargest(10)
        pivot = data.pivot_table(
            index="period",
            columns=dimension,
            values="Amount",
            aggfunc="sum",
            fill_value=0,
        ).reindex(PERIODS, fill_value=0)
        changes = pivot.reindex(columns=totals.index, fill_value=0).diff().dropna()
        for column_index, method in enumerate(("pearson", "spearman")):
            matrix = changes.corr(method=method)
            ax = axes[row_index, column_index]
            sns.heatmap(
                matrix,
                ax=ax,
                cmap="vlag",
                center=0,
                vmin=-1,
                vmax=1,
                annot=True,
                fmt=".2f",
                square=True,
                cbar=False,
                annot_kws={"fontsize": 7},
            )
            ax.set_title(
                f"{dimension} monthly-change {method.title()} correlations",
                loc="left",
                fontsize=11,
                weight="bold",
            )
            ax.tick_params(axis="x", labelrotation=60, labelsize=7)
            ax.tick_params(axis="y", labelrotation=0, labelsize=7)
    fig.suptitle(
        "Co-movement among the 10 largest supplier groups and expense types",
        x=0.01,
        ha="left",
        fontsize=15,
        weight="bold",
    )
    fig.text(
        0.01,
        0.01,
        "Correlations use 35 first differences of monthly net amounts. They are exploratory, not causal; "
        "supplier group roll-ups are applied using the documented mapping.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "monthly_change_correlations.png")


def plot_duplicate_sensitivity(data: pd.DataFrame) -> pd.DataFrame:
    deduplicated = data.drop_duplicates(subset=CORE_COLUMNS, keep="first")
    all_totals = data.groupby("year")["Amount"].sum().reindex(YEARS)
    unique_totals = deduplicated.groupby("year")["Amount"].sum().reindex(YEARS)
    difference = all_totals - unique_totals
    sensitivity = pd.DataFrame(
        {
            "all_rows_net": all_totals,
            "identical_core_rows_once_net": unique_totals,
            "difference_from_repeats": difference,
            "difference_percent": difference / all_totals * 100,
        }
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(YEARS))
    ax1.bar(x - 0.18, all_totals.to_numpy() / 1e9, width=0.36, label="All rows")
    ax1.bar(
        x + 0.18,
        unique_totals.to_numpy() / 1e9,
        width=0.36,
        label="Identical core rows counted once",
    )
    ax1.set_xticks(x, labels=[str(year) for year in YEARS])
    ax1.set_ylabel("Annual net amount (£bn)")
    ax1.set_title("Annual totals", loc="left", weight="bold")
    ax1.legend(fontsize=8)
    ax2.bar(
        [str(year) for year in YEARS],
        difference.to_numpy() / 1_000_000,
        color="#d97706",
    )
    ax2.set_ylabel("Difference (£m)")
    ax2.set_title("Effect of counting identical rows once", loc="left", weight="bold")
    for index, value in enumerate(difference.to_numpy() / 1_000_000):
        ax2.text(index, value, f"{value:.2f}", ha="center", va="bottom", fontsize=9)
    fig.text(
        0.01,
        0.01,
        "Sensitivity scenario only: this does not assert that repeated rows are erroneous.",
        fontsize=8,
        color="#475569",
    )
    save_figure(fig, "duplicate_sensitivity.png")
    return sensitivity


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    data = pd.read_csv(DATA_PATH, dtype={"Transaction number": "string"})
    data["Amount"] = pd.to_numeric(data["Amount"], errors="raise")
    data["period"] = pd.PeriodIndex(data["source_period"], freq="M")
    data["year"] = data["period"].dt.year
    supplier_mapping = pd.read_csv(SUPPLIER_MAPPING_PATH, dtype=str, keep_default_na=False)
    if supplier_mapping["source_supplier"].duplicated().any():
        raise ValueError("Supplier mapping contains duplicate source_supplier labels.")
    unknown_labels = sorted(
        set(supplier_mapping["source_supplier"]) - set(data["Supplier"].unique())
    )
    if unknown_labels:
        raise ValueError(
            "Supplier mapping contains labels not present in the dataset: "
            + ", ".join(unknown_labels)
        )
    data["Supplier group"] = (
        data["Supplier"]
        .map(supplier_mapping.set_index("source_supplier")["consolidated_supplier"])
        .fillna(data["Supplier"])
    )

    monthly = monthly_baseline(data)
    plot_monthly_trend(monthly)
    plot_month_heatmap(monthly)
    plot_monthly_line_counts_and_median(data)
    plot_supplier_concentration(data)
    plot_top_supplier_monthly_trends(data)
    plot_top_categories(data)
    plot_top_expense_types_by_area(data)
    plot_change_contributors(data)
    plot_amount_distributions(data)
    plot_correlations(data)
    sensitivity = plot_duplicate_sensitivity(data)

    print(f"Rows analyzed: {len(data):,}")
    print("Annual net totals and duplicate sensitivity:")
    print(sensitivity.to_string(float_format=lambda value: f"{value:,.2f}"))
    print("Generated figures:")
    for path in sorted(FIGURE_DIR.glob("*.png")):
        print(f"  {path}")


if __name__ == "__main__":
    main()
