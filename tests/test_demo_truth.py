import json
from pathlib import Path

import pandas as pd

from analytics.causal import run_difference_in_differences, run_event_study


ROOT = Path(__file__).resolve().parents[1]


def test_demo_manifest_describes_every_primary_demo():
    manifest = json.loads((ROOT / "examples" / "demo_truth_manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "2.0"
    for name in ["demo_marketing_evidence.csv", "demo_panel_rollout.csv", "demo_mmm_weekly.csv"]:
        assert name in manifest["datasets"]
        assert "known_signal" in manifest["datasets"][name] or "known_adstock" in manifest["datasets"][name]


def test_experiment_demo_has_balanced_randomized_arms_and_positive_known_signal():
    df = pd.read_csv(ROOT / "examples" / "demo_marketing_evidence.csv")
    counts = df.groupby("variant").size()
    rates = df.groupby("variant")["converted"].mean()
    assert counts.max() == counts.min()
    assert rates["treatment"] > rates["control"]


def test_panel_demo_recovers_positive_rollout_effect_and_dynamic_effects():
    df = pd.read_csv(ROOT / "examples" / "demo_panel_rollout.csv")
    did = run_difference_in_differences(df, "revenue_per_customer", "treated", "post", [], "market_id")
    event = run_event_study(df, "revenue_per_customer", "treated", "relative_time", "market_id", "month", -1, [])
    assert did["effect"] > 2.0
    post = [row for row in event["effects"] if row["relative_time"] >= 0]
    assert len(post) >= 6
    assert post[-1]["effect"] > post[0]["effect"]
