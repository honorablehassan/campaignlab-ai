from pathlib import Path


PROMPT = (Path(__file__).resolve().parents[1] / "engines" / "strategy_engine.py").read_text(encoding="utf-8")


def test_strategy_prompt_identifies_decision_stage_before_recommending():
    assert "determine the user's actual decision stage" in PROMPT
    assert "exploring, building, validating, launching, growing, and scaling" in PROMPT


def test_strategy_prompt_does_not_confuse_launch_wedge_with_product_identity():
    assert "A launch wedge is not automatically the whole product" in PROMPT


def test_strategy_prompt_has_readability_limits():
    assert "recommendation at most" in PROMPT
    assert "why_it_wins at most" in PROMPT
