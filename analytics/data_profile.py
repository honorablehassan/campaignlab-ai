from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DataProfile:
    rows: int
    columns: int
    duplicate_rows: int
    duplicate_rate: float
    missing_cells: int
    missing_rate: float
    constant_columns: list[str]
    likely_id_columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    missingness: list[dict[str, Any]]
    date_ranges: list[dict[str, Any]]

    def to_dict(self) -> dict:
        return asdict(self)


def _likely_id(series: pd.Series, name: str, rows: int) -> bool:
    lowered = name.lower()
    name_hint = lowered == "id" or lowered.endswith("_id") or lowered.endswith("id")
    if rows == 0:
        return False
    uniqueness = series.nunique(dropna=True) / max(1, series.notna().sum())
    return name_hint or uniqueness >= 0.98


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    rows, cols = df.shape
    duplicates = int(df.duplicated().sum()) if rows else 0
    missing_cells = int(df.isna().sum().sum())
    total_cells = max(1, rows * cols)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    categorical_cols = [
        c for c in df.columns if c not in numeric_cols and c not in datetime_cols
    ]
    constants = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    likely_ids = [c for c in df.columns if _likely_id(df[c], str(c), rows)]

    missingness = sorted(
        [
            {
                "column": str(c),
                "missing_count": int(df[c].isna().sum()),
                "missing_rate": float(df[c].isna().mean()) if rows else 0.0,
            }
            for c in df.columns
        ],
        key=lambda x: x["missing_rate"],
        reverse=True,
    )

    date_ranges = []
    for c in datetime_cols:
        non_null = df[c].dropna()
        if not non_null.empty:
            date_ranges.append(
                {
                    "column": str(c),
                    "min": str(non_null.min()),
                    "max": str(non_null.max()),
                }
            )

    return DataProfile(
        rows=rows,
        columns=cols,
        duplicate_rows=duplicates,
        duplicate_rate=duplicates / rows if rows else 0.0,
        missing_cells=missing_cells,
        missing_rate=missing_cells / total_cells,
        constant_columns=constants,
        likely_id_columns=likely_ids,
        numeric_columns=[str(c) for c in numeric_cols],
        categorical_columns=[str(c) for c in categorical_cols],
        datetime_columns=[str(c) for c in datetime_cols],
        missingness=missingness,
        date_ranges=date_ranges,
    )


def infer_marketing_fields(df: pd.DataFrame) -> dict[str, list[str]]:
    """Conservative name-based field hints. These are candidates, never truth claims."""
    aliases = {
        "spend": ("spend", "cost", "ad_cost", "media_cost"),
        "revenue": ("revenue", "sales", "gmv", "value"),
        "conversions": ("conversion", "conversions", "orders", "purchases", "leads"),
        "clicks": ("click", "clicks"),
        "impressions": ("impression", "impressions"),
        "channel": ("channel", "source", "medium", "platform"),
        "treatment": ("treatment", "variant", "group", "arm", "control"),
        "outcome": ("outcome", "converted", "conversion", "purchase", "response"),
        "date": ("date", "day", "week", "month", "timestamp", "time"),
        "customer": ("customer", "user", "visitor", "account", "client"),
    }
    result: dict[str, list[str]] = {k: [] for k in aliases}
    for col in df.columns:
        lowered = str(col).lower().replace(" ", "_")
        for field, hints in aliases.items():
            if any(hint == lowered or f"_{hint}" in lowered or lowered.startswith(f"{hint}_") for hint in hints):
                result[field].append(str(col))
    return result


def recommend_dataset_analyses(df: pd.DataFrame, question: str = "") -> list[dict[str, str]]:
    fields = infer_marketing_fields(df)
    recs: list[dict[str, str]] = []

    if fields["spend"] and (fields["revenue"] or fields["conversions"]):
        recs.append(
            {
                "name": "Channel / campaign efficiency",
                "fit": "Strong",
                "why": "Spend and performance outcomes appear to be available, so efficiency metrics can be calculated deterministically.",
                "method_id": "marketing_efficiency",
            }
        )
    if fields["treatment"] and fields["outcome"]:
        recs.append(
            {
                "name": "Treatment / variant comparison",
                "fit": "Strong",
                "why": "The schema appears to contain both a group/variant field and an outcome field.",
                "method_id": "binary_ab",
            }
        )
    if fields["date"] and len(df.select_dtypes(include=[np.number]).columns) > 0:
        recs.append(
            {
                "name": "Trend and anomaly analysis",
                "fit": "Good",
                "why": "Time fields plus numeric measures support trend, change-point, and anomaly-oriented analysis.",
                "method_id": "trend_analysis",
            }
        )
    if fields["customer"] and fields["date"]:
        recs.append(
            {
                "name": "Customer cohort / retention analysis",
                "fit": "Possible",
                "why": "Customer identifiers and time fields may support cohort behavior analysis if repeat observations exist.",
                "method_id": "cohort_retention",
            }
        )
    if len(df.select_dtypes(include=[np.number]).columns) >= 2:
        recs.append(
            {
                "name": "Driver / relationship analysis",
                "fit": "Possible",
                "why": "Multiple numeric variables support relationship analysis, subject to an explicit target and validity checks.",
                "method_id": "regression_family",
            }
        )

    if not recs:
        recs.append(
            {
                "name": "Structured exploratory analysis",
                "fit": "Starting point",
                "why": "The schema does not yet expose a high-confidence marketing analysis path. Profile distributions and clarify the decision before modeling.",
                "method_id": "eda",
            }
        )
    return recs[:5]


def question_risks(df: pd.DataFrame, question: str) -> list[dict[str, str]]:
    if not question.strip():
        return []
    q = question.lower()
    fields = infer_marketing_fields(df)
    risks: list[dict[str, str]] = []

    if any(word in q for word in ("roas", "return on ad", "profit", "profitable")):
        if not fields["spend"]:
            risks.append({"level": "high", "message": "The question needs spend/cost, but no obvious spend field was detected."})
        if not fields["revenue"]:
            risks.append({"level": "high", "message": "The question needs revenue/value, but no obvious revenue field was detected."})
    if any(word in q for word in ("cause", "caused", "incremental", "incrementality", "impact", "lift")):
        if not fields["treatment"]:
            risks.append(
                {
                    "level": "high",
                    "message": "The question sounds causal, but no obvious treatment/control or variant field was detected. Observational performance alone does not establish incrementality.",
                }
            )
    if "cac" in q or "acquisition cost" in q:
        if not fields["spend"]:
            risks.append({"level": "high", "message": "CAC requires cost/spend, and no obvious spend field was detected."})
        if not fields["conversions"] and not fields["customer"]:
            risks.append({"level": "high", "message": "CAC requires an acquisition count or customer identifier, and neither is obvious in the schema."})
    return risks
