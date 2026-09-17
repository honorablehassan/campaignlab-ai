"""Shared, bounded parsing for user-provided tabular evidence."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_TABULAR_EXTENSIONS = {".csv", ".xlsx"}


def load_tabular_upload(uploaded: Any, *, max_bytes: int = MAX_UPLOAD_BYTES) -> pd.DataFrame:
    name = str(getattr(uploaded, "name", "upload")).strip()
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_TABULAR_EXTENSIONS:
        raise ValueError("CampaignLab accepts CSV or XLSX evidence only.")
    raw = uploaded.getvalue()
    if not raw:
        raise ValueError("The uploaded file is empty.")
    if len(raw) > max_bytes:
        raise ValueError(f"File is larger than the current {max_bytes // (1024 * 1024)} MB safety limit. Reduce the extract before analysis.")
    try:
        frame = pd.read_csv(io.BytesIO(raw), low_memory=False) if suffix == ".csv" else pd.read_excel(io.BytesIO(raw))
    except Exception as exc:
        raise ValueError(f"CampaignLab could not parse {name} as a valid {suffix[1:].upper()} table.") from exc
    if frame.empty or len(frame.columns) == 0:
        raise ValueError("The uploaded table contains no usable rows or columns.")
    return frame
