from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = (ROOT / "ui" / "strategy_lab.py").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "ui" / "evidence_lab.py").read_text(encoding="utf-8")
MMM = (ROOT / "ui" / "mmm_lab.py").read_text(encoding="utf-8")
STATE = (ROOT / "state.py").read_text(encoding="utf-8")
ABOUT = (ROOT / "ui" / "about.py").read_text(encoding="utf-8")


def test_strategy_is_broad_and_never_shows_old_result_under_edited_inputs():
    assert "messy marketing problem" not in STRATEGY
    assert "messy decision" in STRATEGY
    assert "strategy inputs changed after the last run" in STRATEGY
    assert 'st.query_params["page"] = "evidence"' in STRATEGY


def test_strategy_handoff_populates_real_evidence_widget_keys():
    assert "st.session_state.evidence_design_question = handoff" in STATE
    assert "st.session_state.evidence_design_outcome = handoff" in STATE
    assert "st.session_state.evidence_design_constraints = handoff" in STATE
    assert '"primary_outcome": ""' in STATE


def test_evidence_has_forward_routes_and_stale_guards():
    assert "Bring whatever data I have →" in EVIDENCE
    assert "Bring the experiment data →" in EVIDENCE
    assert "These inputs changed after the last analysis" in EVIDENCE
    assert "dataset or question changed after the last CampaignLab analysis" in EVIDENCE
    assert "Show me what would unlock this question" in EVIDENCE


def test_directory_does_not_preselect_experimentation_and_has_use_cta():
    assert "default=None" in EVIDENCE
    assert "Nothing is preselected here" in EVIDENCE
    assert "Use this with my data →" in EVIDENCE


def test_mmm_never_reuses_old_model_after_mapping_or_data_change():
    assert "mmm_result_signature" in MMM
    assert "dataset or model mapping changed after the last run" in MMM
    assert "prepare_mmm_handoff" in MMM
    assert "Validate this decision in Evidence Lab" in MMM


def test_mmm_does_not_hardcode_usd_display():
    assert "Display currency" in MMM
    assert '"Source units"' in MMM


def test_about_keeps_founder_surface_and_side_support():
    assert "cl-founder-paper" in ABOUT
    assert "Keep the experiment moving." in ABOUT
    assert "cl-about-rail" in ABOUT
