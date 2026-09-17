from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_starts_cleanly_without_secrets_file():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30)
    app.run()
    assert not app.exception
    assert any("OPENAI_API_KEY is missing" in str(item.value) for item in app.error)
    assert any("From messy questions to decisions" in str(item.value) for item in app.markdown)
