"""Rebuild CampaignLab's deterministic demo datasets and known-answer manifest.

Run from the repository root:
    python examples/generate_demo_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent


def _adstock(values: np.ndarray, alpha: float) -> np.ndarray:
    out = np.zeros_like(values, dtype=float)
    for i, value in enumerate(values):
        out[i] = value + (alpha * out[i - 1] if i else 0.0)
    return out


def _sat(values: np.ndarray, scale: float) -> np.ndarray:
    return 1.0 - np.exp(-np.maximum(values, 0.0) / scale)


def marketing_evidence(seed: int = 1103) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 2400
    variant = np.where(np.arange(n) % 2 == 0, "control", "treatment")
    rng.shuffle(variant)
    channel = rng.choice(["Paid Search", "Meta", "Email", "Organic"], n, p=[0.30, 0.28, 0.18, 0.24])
    baseline = pd.Series(channel).map({"Paid Search": 0.115, "Meta": 0.075, "Email": 0.13, "Organic": 0.095}).to_numpy()
    probability = np.clip(baseline + np.where(variant == "treatment", 0.025, 0.0), 0, 1)
    converted = rng.binomial(1, probability)
    order_value = np.maximum(18, rng.normal(94, 24, n))
    clicked = rng.binomial(1, pd.Series(channel).map({"Paid Search": .31, "Meta": .19, "Email": .27, "Organic": .23}).to_numpy())
    cost = pd.Series(channel).map({"Paid Search": 2.20, "Meta": 1.35, "Email": .18, "Organic": 0.0}).to_numpy()
    return pd.DataFrame({
        "user_id": np.arange(100000, 100000 + n),
        "event_date": pd.Timestamp("2026-06-01") + pd.to_timedelta(rng.integers(0, 56, n), unit="D"),
        "variant": variant,
        "channel": channel,
        "converted": converted,
        "revenue": np.round(converted * order_value, 2),
        "ad_spend": np.round(cost, 2),
        "clicked": clicked,
        "impressions": np.ones(n, dtype=int),
    }).sort_values(["event_date", "user_id"]).reset_index(drop=True)


def panel_rollout(seed: int = 2207) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2025-07-01")
    for market in range(30):
        treated = int(market >= 15)
        market_effect = rng.normal(0, 3.5)
        for relative_time in range(-6, 8):
            post = int(relative_time >= 0)
            dynamic_effect = (2.0 + 1.1 * relative_time) if treated and post else 0.0
            outcome = 48 + market_effect + 0.45 * (relative_time + 6) + dynamic_effect + rng.normal(0, 1.4)
            rows.append({
                "market_id": market,
                "treated": treated,
                "post": post,
                "relative_time": relative_time,
                "month": start + pd.DateOffset(months=relative_time + 6),
                "revenue_per_customer": round(outcome, 4),
            })
    return pd.DataFrame(rows)


def mmm_weekly(seed: int = 3301) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 182
    t = np.arange(n)
    week = pd.date_range("2023-01-02", periods=n, freq="W-MON")
    promotion = rng.binomial(1, .13, n)
    holiday = ((week.month == 11) | (week.month == 12)).astype(int)
    price = 100 + np.cumsum(rng.normal(0, .12, n))

    meta = np.maximum(5000, 42000 + 9000 * np.sin(2 * np.pi * t / 23) + rng.normal(0, 6500, n))
    search = np.maximum(5000, 51000 + 11000 * np.cos(2 * np.pi * t / 31) + rng.normal(0, 7500, n))
    youtube = np.maximum(2000, 26000 + 8500 * np.sin(2 * np.pi * (t + 5) / 41) + rng.normal(0, 5000, n))
    tv = np.maximum(0, 18000 + 16000 * (np.mod(t, 18) < 5) + rng.normal(0, 4500, n))

    media = (
        150000 * _sat(_adstock(meta, .50), 78000)
        + 205000 * _sat(_adstock(search, .25), 72000)
        + 90000 * _sat(_adstock(youtube, .70), 80000)
        + 70000 * _sat(_adstock(tv, .85), 110000)
    )
    baseline = 430000 + 70000 * np.sin(2 * np.pi * t / 52) + 450 * t
    revenue = baseline + media + 80000 * promotion + 55000 * holiday - 4200 * (price - 100) + rng.normal(0, 22000, n)
    conversions = np.maximum(0, np.round(revenue / 96 + rng.normal(0, 180, n))).astype(int)
    return pd.DataFrame({
        "week": week,
        "revenue": np.round(revenue, 2),
        "meta_spend": np.round(meta, 2),
        "paid_search_spend": np.round(search, 2),
        "youtube_spend": np.round(youtube, 2),
        "tv_spend": np.round(tv, 2),
        "promotion": promotion,
        "holiday_period": holiday,
        "price_index": np.round(price, 3),
        "conversions": conversions,
    })


def main() -> None:
    marketing_evidence().to_csv(ROOT / "demo_marketing_evidence.csv", index=False)
    panel_rollout().to_csv(ROOT / "demo_panel_rollout.csv", index=False)
    mmm_weekly().to_csv(ROOT / "demo_mmm_weekly.csv", index=False)
    manifest = {
        "version": "2.0",
        "purpose": "Deterministic known-answer scenarios for demos and regression tests; not real customer data.",
        "datasets": {
            "demo_marketing_evidence.csv": {
                "design": "balanced randomized binary experiment",
                "known_signal": "treatment adds 2.5 percentage points to conversion probability before sampling noise",
                "seed": 1103,
            },
            "demo_panel_rollout.csv": {
                "design": "30-market panel with parallel pre-trends and stagger-free intervention",
                "known_signal": "treated markets gain 2.0 plus 1.1 per post-period relative-time unit",
                "reference_period": -1,
                "seed": 2207,
            },
            "demo_mmm_weekly.csv": {
                "design": "182 weekly periods with four media channels, carryover, saturation, seasonality, trend, controls, and noise",
                "known_adstock": {"meta_spend": 0.50, "paid_search_spend": 0.25, "youtube_spend": 0.70, "tv_spend": 0.85},
                "known_relative_media_scale": ["paid_search_spend", "meta_spend", "youtube_spend", "tv_spend"],
                "seed": 3301,
            },
        },
    }
    (ROOT / "demo_truth_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
