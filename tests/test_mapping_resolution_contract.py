import pandas as pd

from analytics.data_builder import understand_source
from analytics.dataset_intelligence import analyze_dataset_intelligence
from analytics.method_ranker import rank_methods
from analytics.tool_runtime import EvidenceToolRuntime


def ambiguous_sales_df():
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=80, freq="D"),
        "channel": ["Search", "Social"] * 40,
        "spend": [100.0 + i for i in range(80)],
        "gross_sales": [300.0 + i * 2 for i in range(80)],
        "net_sales": [250.0 + i * 1.5 for i in range(80)],
    })


def test_builder_surfaces_ambiguous_revenue():
    u = understand_source(ambiguous_sales_df(), "commerce.csv")
    assert "revenue" in u["ambiguous"]
    assert set(u["ambiguous"]["revenue"]) == {"gross_sales", "net_sales"}


def test_resolved_mapping_becomes_single_role_everywhere():
    df = ambiguous_sales_df()
    intel = analyze_dataset_intelligence(df, "Which channel is most efficient?", role_overrides={"revenue": "net_sales"})
    assert intel.role_map["revenue"] == ["net_sales"]
    ranked = rank_methods(intel, "Which channel is most efficient?")
    eff = next(m for m in ranked if m["method_id"] == "marketing_efficiency")
    assert eff["eligible"] is True

    runtime = EvidenceToolRuntime(df, role_overrides={"revenue": "net_sales"})
    rt_intel = runtime.execute("inspect_dataset_intelligence", {"question": "Which channel is most efficient?"})
    assert rt_intel["role_map"]["revenue"] == ["net_sales"]
    rt_rank = runtime.execute("rank_candidate_methods", {"question": "Which channel is most efficient?"})
    rt_eff = next(m for m in rt_rank["ranked_methods"] if m["method_id"] == "marketing_efficiency")
    assert rt_eff["eligible"] is True


def test_unresolved_mapping_does_not_quietly_choose_candidate():
    df = ambiguous_sales_df()
    intel = analyze_dataset_intelligence(df, "Which channel is most efficient?", role_overrides={"revenue": None})
    assert intel.role_map["revenue"] == []
    ranked = rank_methods(intel, "Which channel is most efficient?")
    eff = next(m for m in ranked if m["method_id"] == "marketing_efficiency")
    assert eff["eligible"] is False

    runtime = EvidenceToolRuntime(df, role_overrides={"revenue": None})
    rt_intel = runtime.execute("inspect_dataset_intelligence", {"question": "Which channel is most efficient?"})
    assert rt_intel["role_map"]["revenue"] == []


def test_bad_override_is_rejected():
    df = ambiguous_sales_df()
    try:
        analyze_dataset_intelligence(df, role_overrides={"revenue": "not_a_column"})
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected invalid mapping to fail closed")


def test_runtime_cannot_override_confirmed_revenue_mapping():
    df = ambiguous_sales_df()
    runtime = EvidenceToolRuntime(df, role_overrides={"revenue": "net_sales"})
    args = {
        "group_column": "channel", "spend_column": "spend",
        "revenue_column": "gross_sales", "conversions_column": "",
        "clicks_column": "", "impressions_column": "",
    }
    try:
        runtime.execute("analyze_marketing_efficiency", args)
    except Exception as exc:
        assert "resolved to 'net_sales'" in str(exc)
    else:
        raise AssertionError("Runtime must not contradict a confirmed mapping")
