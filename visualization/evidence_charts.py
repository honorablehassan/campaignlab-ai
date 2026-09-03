from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analytics.ab_binary import required_sample_size_per_group
from visualization.style import annotate_bars, clean_axes, finalize, format_compact_axis, format_percent_axis


def conversion_rate_chart(result):
    labels = ["Control", "Treatment"]
    rates = np.array([result.control_rate, result.treatment_rate]) * 100
    lows = np.array([result.control_ci_low, result.treatment_ci_low]) * 100
    highs = np.array([result.control_ci_high, result.treatment_ci_high]) * 100
    yerr = np.vstack([rates - lows, highs - rates])

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.bar(labels, rates, width=0.55)
    ax.errorbar(labels, rates, yerr=yerr, fmt="none", capsize=6, linewidth=1.6)
    ax.set_ylabel("Conversion rate")
    ax.set_ylim(bottom=0)
    format_percent_axis(ax, axis="y", decimals=1)
    clean_axes(ax, grid_axis="y")
    annotate_bars(ax, rates, suffix="%", decimals=2)
    finalize(
        fig,
        ax,
        title="Treatment vs control conversion",
        subtitle="Observed rates with Wilson 95% confidence intervals",
    )
    return fig


def effect_interval_chart(result):
    effect = result.absolute_lift * 100
    low = result.ci_low * 100
    high = result.ci_high * 100
    threshold = result.business_threshold * 100

    fig, ax = plt.subplots(figsize=(8.0, 3.45))
    ax.errorbar(
        effect,
        0,
        xerr=[[effect - low], [high - effect]],
        fmt="o",
        markersize=7,
        capsize=7,
        linewidth=2,
    )
    ax.axvline(0, linestyle="--", linewidth=1.15, alpha=0.7, label="No effect")
    if threshold > 0:
        ax.axvline(threshold, linestyle=":", linewidth=1.4, alpha=0.85, label="Business threshold")
    ax.set_yticks([])
    ax.set_xlabel("Treatment − control")
    format_percent_axis(ax, axis="x", decimals=1)
    clean_axes(ax, grid_axis="x")
    ax.legend(frameon=False, loc="best")
    ax.text(effect, 0.07, f"{effect:+.2f} pp", ha="center", fontsize=9.5)
    finalize(
        fig,
        ax,
        title="Estimated incremental lift",
        subtitle=f"95% plausible range: {low:+.2f} pp to {high:+.2f} pp",
    )
    return fig


def sample_size_curve(baseline_rate: float, alpha: float = 0.05, power: float = 0.80):
    max_mde = min(0.08, max(0.01, (1 - baseline_rate) * 0.25))
    min_mde = min(0.0025, max_mde / 4)
    mdes = np.linspace(min_mde, max_mde, 22)
    samples = []
    valid_mdes = []
    for mde in mdes:
        target = baseline_rate + mde
        if target >= 1:
            continue
        valid_mdes.append(mde * 100)
        samples.append(required_sample_size_per_group(baseline_rate, target, alpha, power))

    fig, ax = plt.subplots(figsize=(7.6, 4.35))
    ax.plot(valid_mdes, samples, marker="o", markersize=3.5, linewidth=1.8)
    ax.set_xlabel("Minimum detectable lift (percentage points)")
    ax.set_ylabel("Users per group")
    ax.set_ylim(bottom=0)
    format_compact_axis(ax, axis="y")
    clean_axes(ax, grid_axis="both")
    finalize(
        fig,
        ax,
        title="Sample size vs detectable lift",
        subtitle=f"Baseline {baseline_rate:.1%} · {power:.0%} power · 5% two-sided alpha",
    )
    return fig


def missingness_chart(profile, top_n: int = 15):
    rows = [m for m in profile.missingness if m["missing_rate"] > 0][:top_n]
    if not rows:
        return None
    plot_df = pd.DataFrame(rows).sort_values("missing_rate", ascending=True)
    values = plot_df["missing_rate"].values * 100
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.35 * len(plot_df))))
    ax.barh(plot_df["column"], values)
    ax.set_xlabel("Missing values")
    format_percent_axis(ax, axis="x", decimals=0)
    clean_axes(ax, grid_axis="x")
    annotate_bars(ax, values, horizontal=True, suffix="%", decimals=1)
    finalize(fig, ax, title="Where missing data is concentrated")
    return fig
