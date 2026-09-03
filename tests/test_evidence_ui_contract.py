from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "ui" / "evidence_lab.py").read_text(encoding="utf-8")


def test_design_evidence_never_requires_method_vocabulary_up_front():
    assert "What are you trying to find out?" in SOURCE
    assert "Which situation is closest?" in SOURCE
    assert "Can you decide who gets each version?" not in SOURCE
    assert "How many conditions do you want to compare?" not in SOURCE


def test_unsure_path_still_builds_a_plan():
    assert '"I\'m not sure yet"' in SOURCE
    assert '"Find My Evidence Path"' in SOURCE
    assert 'st.header("First, establish what can vary")' in SOURCE
    assert "Bring whatever data I have →" in SOURCE


def test_existing_evidence_has_forward_routes():
    assert '"Analyze a structured test →"' in SOURCE
    assert '"Bring the data →"' in SOURCE
    assert 'evidence_route="📈 I already ran a test"' in SOURCE
    assert 'evidence_route="📂 I have data"' in SOURCE


def test_measurement_uncertainty_explains_instead_of_invalidating_plan():
    assert '"How does that outcome show up in the data?"' in SOURCE
    assert "Your evidence plan above is still valid either way." in SOURCE
    assert '"Bring example data for CampaignLab to inspect →"' in SOURCE


def test_stale_plan_is_not_displayed_after_inputs_change():
    assert "Build the evidence plan again so CampaignLab does not show a stale recommendation." in SOURCE
