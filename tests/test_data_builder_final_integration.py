from pathlib import Path

import pandas as pd
import pytest

from analytics.data_builder import detect_source, understand_source, build_mmm_dataset

ROOT = Path(__file__).resolve().parents[1] / "examples" / "data_builder_sources"


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("meta_daily.csv", "meta_ads"),
        ("google_ads_daily.csv", "google_ads"),
        ("youtube_daily.csv", "media_export"),
        ("tv_daily.csv", "media_export"),
        ("commerce_weekly.csv", "sales"),
    ],
)
def test_builtin_sources_are_not_misclassified(filename, expected):
    df = pd.read_csv(ROOT / filename)
    assert detect_source(df, filename)["kind"] == expected


def test_generic_ad_schema_does_not_pretend_to_know_platform():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "campaign_name": ["A", "A"],
        "spend": [100, 120],
        "impressions": [1000, 1100],
        "clicks": [20, 24],
    })
    assert detect_source(df, "mystery_export.csv")["kind"] == "media_export"


def test_understanding_surfaces_platform_attribution_caution():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "spend": [100, 120],
        "purchase_value": [250, 300],
        "campaign_name": ["A", "A"],
    })
    out = understand_source(df, "meta_export.csv")
    assert out["source_kind"] == "meta_ads"
    assert any("incrementality" in x.lower() for x in out["cautions"])


def test_large_source_recommends_query_pushdown():
    # We only need row count behavior; avoid allocating 500k strings.
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=500_000, freq="min"), "event_name": "page_view", "user_pseudo_id": 1})
    out = understand_source(df, "ga4_events.csv")
    assert any("query pushdown" in x.lower() for x in out["cautions"])


def test_builtin_multi_source_demo_builds_weekly_mmm_table():
    sources = []
    for filename in ["meta_daily.csv", "google_ads_daily.csv", "youtube_daily.csv", "tv_daily.csv", "commerce_weekly.csv"]:
        df = pd.read_csv(ROOT / filename)
        u = understand_source(df, filename)
        sources.append({"name": filename.rsplit(".", 1)[0], "df": df, "kind": u["source_kind"]})
    built, report = build_mmm_dataset(sources, grain="week", outcome_source="commerce_weekly")
    assert report["status"] == "ready"
    assert len(built) == 156
    assert len(report["media_columns"]) == 4
    assert set(report["control_columns"]) == {"promotion", "holiday_period", "price_index"}
    assert built[report["media_columns"]].isna().sum().sum() == 0
    assert {"revenue", "promotion", "holiday_period", "price_index"}.issubset(built.columns)


def test_builder_preserves_unknown_media_periods():
    sales = pd.DataFrame({"week": pd.date_range("2026-01-05", periods=4, freq="W-MON"), "net_sales": [100, 110, 120, 130]})
    meta = pd.DataFrame({"date": pd.to_datetime(["2026-01-05", "2026-01-19", "2026-01-26"]), "spend": [10, 12, 13], "campaign_name": ["A"] * 3})
    sources = [
        {"name": "sales", "df": sales, "kind": "sales"},
        {"name": "meta", "df": meta, "kind": "media_export"},
    ]
    built, report = build_mmm_dataset(sources, grain="week", outcome_source="sales")
    media_col = report["media_columns"][0]
    assert built[media_col].isna().sum() == 1
    assert any("preserved" in x.lower() for x in report["warnings"])
