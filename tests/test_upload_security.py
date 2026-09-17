import io

import pandas as pd
import pytest

from core.uploads import load_tabular_upload


class Upload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_upload_gate_accepts_csv():
    frame = load_tabular_upload(Upload("evidence.csv", b"group,outcome\nA,1\nB,0\n"))
    assert list(frame.columns) == ["group", "outcome"]


@pytest.mark.parametrize("name,data", [("evidence.exe", b"x"), ("empty.csv", b"")])
def test_upload_gate_rejects_unsupported_or_empty(name, data):
    with pytest.raises(ValueError):
        load_tabular_upload(Upload(name, data))


def test_upload_gate_enforces_configured_size_limit():
    with pytest.raises(ValueError, match="safety limit"):
        load_tabular_upload(Upload("large.csv", b"a\n12345\n"), max_bytes=3)


def test_upload_gate_does_not_leak_parser_details():
    with pytest.raises(ValueError, match="could not parse") as error:
        load_tabular_upload(Upload("broken.xlsx", b"not an excel file"))
    assert "BadZipFile" not in str(error.value)
