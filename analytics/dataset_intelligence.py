from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import math
import re

import numpy as np
import pandas as pd


ROLE_ALIASES = {
    "id": ("id", "user_id", "customer_id", "account_id", "client_id", "visitor_id", "session_id"),
    "date": ("date", "day", "week", "month", "timestamp", "time", "datetime", "created_at", "event_time"),
    "treatment": ("treatment", "variant", "arm", "group", "test_group", "experiment_group", "control"),
    "binary_outcome": ("converted", "conversion", "purchased", "purchase", "responded", "response", "churned", "clicked"),
    "continuous_outcome": ("revenue", "sales", "gmv", "order_value", "aov", "ltv", "profit", "margin", "spend_value"),
    "spend": ("spend", "cost", "ad_spend", "media_cost", "marketing_cost", "investment"),
    "revenue": ("revenue", "sales", "gmv", "bookings", "value"),
    "channel": ("channel", "source", "medium", "platform", "network", "campaign_type"),
    "campaign": ("campaign", "adset", "ad_set", "creative", "placement"),
    "impressions": ("impressions", "impression"),
    "clicks": ("clicks", "click"),
    "conversions": ("conversions", "orders", "purchases", "leads", "signups", "acquisitions"),
    "segment": ("segment", "audience", "cohort", "persona", "region", "market", "country", "state"),
    "customer": ("customer", "user", "account", "client", "visitor"),
    "unit": ("unit_id", "store_id", "market_id", "geo_id", "entity_id", "panel_id"),
    "post": ("post", "post_period", "after", "after_treatment", "post_treatment"),
    "relative_time": ("relative_time", "event_time", "event_period", "time_to_treatment", "event_week"),
    "stage": ("stage", "funnel_stage", "step"),
}


@dataclass(frozen=True)
class ColumnSignal:
    column: str
    dtype: str
    semantic_type: str
    roles: list[str]
    non_null: int
    unique: int
    missing_rate: float
    cardinality_ratio: float
    numeric_min: float | None = None
    numeric_max: float | None = None


@dataclass(frozen=True)
class DatasetIntelligence:
    rows: int
    columns: int
    grain_guess: str
    column_signals: list[dict[str, Any]]
    role_map: dict[str, list[str]]
    quality_findings: list[dict[str, str]]
    analytical_opportunities: list[dict[str, Any]]
    question_assessment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _name_matches(name: str, aliases: tuple[str, ...]) -> bool:
    n = _norm(name)
    tokens = set(n.split("_"))
    for alias in aliases:
        a = _norm(alias)
        if n == a or n.startswith(a + "_") or n.endswith("_" + a) or a in tokens:
            return True
    return False


def _semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        non_null = series.dropna()
        if not non_null.empty:
            uniq = set(pd.unique(non_null))
            if len(uniq) <= 2 and uniq.issubset({0, 1, 0.0, 1.0}):
                return "binary_numeric"
        return "numeric"
    return "categorical"


def _infer_roles(name: str, series: pd.Series, rows: int) -> list[str]:
    roles: list[str] = []
    semantic = _semantic_type(series)
    non_null = max(1, int(series.notna().sum()))
    uniqueness = float(series.nunique(dropna=True)) / non_null

    # Name aliases are useful, but some names describe metrics rather than roles.
    # Apply stricter semantic gates where false positives are especially costly.
    for role, aliases in ROLE_ALIASES.items():
        if not _name_matches(name, aliases):
            continue
        if role == "date":
            n = _norm(name)
            dateish = (
                semantic == "datetime"
                or n in {"date", "day", "week", "month", "time", "datetime", "timestamp", "event_time", "created_at", "event_date"}
                or n.endswith("_date")
                or n.endswith("_timestamp")
                or n.endswith("_datetime")
            )
            if not dateish:
                continue
        if role == "binary_outcome":
            # A column named purchase_value or purchase_revenue is not a binary
            # outcome merely because it contains the token "purchase".
            if semantic not in {"binary_numeric", "boolean"}:
                if not (semantic == "categorical" and series.nunique(dropna=True) <= 2):
                    continue
        roles.append(role)

    name_is_id = _name_matches(name, ROLE_ALIASES["id"])
    object_like = not pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_datetime64_any_dtype(series)
    if name_is_id or (object_like and uniqueness >= 0.98 and rows >= 20):
        roles.append("id")
    if semantic == "datetime":
        roles.append("date")
    # A 0/1 column is not automatically an outcome. Flags such as holiday,
    # promotion, mobile, post-period, and eligibility are often controls or
    # design variables. Outcome status requires outcome-like naming above.
    if semantic == "categorical" and 2 <= series.nunique(dropna=True) <= 6:
        # A low-cardinality categorical can plausibly be an experiment arm.
        if any(token in _norm(name) for token in ("variant", "arm", "group", "treatment", "control")):
            roles.append("treatment")

    # preserve order while de-duping
    return list(dict.fromkeys(roles))


def _grain_guess(df: pd.DataFrame, role_map: dict[str, list[str]]) -> str:
    rows = len(df)
    if rows == 0:
        return "empty dataset"
    ids = role_map.get("id", [])
    for col in ids:
        if col in df.columns and df[col].nunique(dropna=True) >= rows * 0.95:
            return f"likely one row per {col}"
    # Common analytics exports such as GA4 are long event tables, not
    # aggregated campaign performance, even when source/campaign fields exist.
    if "event_name" in df.columns and any(c in df.columns for c in ("user_pseudo_id", "user_id", "session_id")):
        return "likely event-level behavioral data"
    dates = role_map.get("date", [])
    campaigns = role_map.get("campaign", [])
    channels = role_map.get("channel", [])
    if dates and (campaigns or channels):
        return "likely aggregated performance by time and campaign/channel"
    return "grain unclear; confirm what one row represents before causal or customer-level modeling"


def _quality_findings(df: pd.DataFrame, signals: list[ColumnSignal], role_map: dict[str, list[str]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    rows = len(df)
    dup_rate = float(df.duplicated().mean()) if rows else 0.0
    if dup_rate >= 0.01:
        findings.append({"level": "warning", "finding": f"{dup_rate:.1%} of rows are exact duplicates."})

    for sig in signals:
        if sig.missing_rate >= 0.50:
            findings.append({"level": "warning", "finding": f"{sig.column} is {sig.missing_rate:.0%} missing."})
        elif sig.missing_rate >= 0.15:
            findings.append({"level": "info", "finding": f"{sig.column} is {sig.missing_rate:.0%} missing; confirm this is acceptable for the intended analysis."})
        if sig.unique <= 1 and rows > 0:
            findings.append({"level": "info", "finding": f"{sig.column} is constant and adds no analytical variation."})

    # Grain/integrity checks for likely identifiers.
    for col in role_map.get("id", [])[:3]:
        if col in df.columns and rows:
            non_null = max(1, int(df[col].notna().sum()))
            duplicate_share = 1 - (df[col].nunique(dropna=True) / non_null)
            if duplicate_share >= 0.05:
                findings.append({"level": "warning", "finding": f"{col} repeats in {duplicate_share:.1%} of non-null rows. Confirm whether repeated observations are expected at this grain."})

    treatment_cols = role_map.get("treatment", [])
    outcome_cols = list(dict.fromkeys(role_map.get("binary_outcome", []) + role_map.get("continuous_outcome", [])))
    for col in treatment_cols[:2]:
        if col not in df.columns:
            continue
        counts = df[col].value_counts(dropna=False)
        if len(counts) >= 2:
            shares = counts / counts.sum()
            if shares.max() > 0.9:
                findings.append({"level": "warning", "finding": f"{col} is extremely imbalanced; the largest group is {shares.max():.1%} of rows."})
            if counts.min() < 30:
                findings.append({"level": "warning", "finding": f"At least one {col} group has fewer than 30 rows; asymptotic comparisons may be unstable."})

        # Missing outcomes that differ by group can bias comparisons.
        for outcome in outcome_cols[:3]:
            if outcome not in df.columns:
                continue
            rates = df.groupby(col, dropna=False)[outcome].apply(lambda x: float(x.isna().mean()))
            if len(rates) >= 2 and float(rates.max() - rates.min()) >= 0.10:
                findings.append({"level": "warning", "finding": f"Missingness in {outcome} differs across {col} groups by {float(rates.max() - rates.min()):.1%}; treatment comparisons could be biased."})

    # Plausibility checks for marketing economics. Negative values are not always wrong, so flag rather than clean.
    for role in ("spend", "revenue"):
        for col in role_map.get(role, [])[:3]:
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(vals) and (vals < 0).mean() >= 0.01:
                    findings.append({"level": "warning", "finding": f"{col} contains {(vals < 0).mean():.1%} negative values. Confirm refunds/credits are intentional before efficiency analysis."})

    # Named binary outcomes should actually look binary.
    for col in role_map.get("binary_outcome", [])[:4]:
        if col in df.columns:
            uniq = df[col].dropna().nunique()
            if uniq > 2:
                findings.append({"level": "warning", "finding": f"{col} was recognized as an outcome by name but has {uniq} distinct values; do not treat it as binary without recoding/confirmation."})

    if not findings:
        findings.append({"level": "ok", "finding": "No major structural quality issue was detected in the initial profile."})
    return findings[:16]


def _opportunity_score(base: int, *, has_rows: bool, blockers: int = 0, bonuses: int = 0) -> int:
    score = base + bonuses - blockers * 18
    if not has_rows:
        score -= 50
    return max(0, min(100, score))


def _opportunities(df: pd.DataFrame, role_map: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows = len(df)
    has = lambda role: bool(role_map.get(role))
    ops: list[dict[str, Any]] = []

    if has("spend") and (has("revenue") or has("conversions")):
        ops.append({
            "id": "marketing_efficiency",
            "title": "Channel / campaign efficiency",
            "score": _opportunity_score(84, has_rows=rows > 0, bonuses=6 if has("channel") or has("campaign") else 0),
            "why": "Spend plus revenue/conversion fields support deterministic efficiency metrics such as ROAS, CPA/CAC, and contribution by channel or campaign.",
            "needs": ["spend", "revenue or conversions"],
            "decision_examples": ["Which channel deserves more budget?", "Which campaigns are inefficient?"],
        })

    if has("treatment") and has("binary_outcome"):
        ops.append({
            "id": "binary_ab",
            "title": "Experiment / treatment comparison",
            "score": _opportunity_score(90, has_rows=rows > 0),
            "why": "A treatment/variant field and binary outcome appear available, which can support deterministic experiment analysis if assignment and unit assumptions hold.",
            "needs": ["treatment assignment", "binary outcome"],
            "decision_examples": ["Did treatment improve conversion?", "Should we ship the variant?"],
        })

    if has("date") and any(has(r) for r in ("revenue", "spend", "conversions", "continuous_outcome")):
        ops.append({
            "id": "trend_analysis",
            "title": "Trend, seasonality, and anomaly analysis",
            "score": _opportunity_score(76, has_rows=rows > 0, bonuses=5 if rows >= 30 else 0),
            "why": "Time plus numeric performance measures can reveal trend shifts, anomalies, and periods that deserve investigation.",
            "needs": ["date/time", "numeric outcome"],
            "decision_examples": ["When did performance deteriorate?", "Which periods were abnormal?"],
        })

    if has("customer") and has("date"):
        ops.append({
            "id": "cohort_retention",
            "title": "Cohort / retention analysis",
            "score": _opportunity_score(72, has_rows=rows > 0),
            "why": "Customer identifiers plus time may support repeat-behavior, cohort, and retention analysis if customers appear more than once.",
            "needs": ["customer identifier", "event date"],
            "decision_examples": ["Which acquisition cohorts retain best?", "Is repeat purchase improving?"],
        })

    if has("treatment") and has("continuous_outcome"):
        ops.append({
            "id": "continuous_ab", "title": "Continuous-outcome experiment",
            "score": _opportunity_score(88, has_rows=rows > 0),
            "why": "Treatment assignment plus a continuous outcome can support a Welch A/B comparison and robust cross-check.",
            "needs": ["treatment assignment", "continuous outcome"],
            "decision_examples": ["Did treatment increase revenue per user?"],
        })

    if has("treatment") and role_map.get("treatment") and rows >= 80:
        tcol=role_map["treatment"][0]
        try:
            arms=int(df[tcol].dropna().nunique())
        except Exception:
            arms=0
        if arms >= 3:
            ops.append({
                "id": "abn", "title": "Multi-arm experiment",
                "score": _opportunity_score(86, has_rows=rows > 0),
                "why": f"{arms} treatment arms were detected; CampaignLab can run an omnibus test plus Holm-corrected comparisons.",
                "needs": ["3+ treatment arms", "binary or continuous outcome"],
                "decision_examples": ["Which variant wins after multiple-testing correction?"],
            })

    if has("treatment") and has("post") and (has("continuous_outcome") or has("revenue")):
        ops.append({
            "id": "did", "title": "Difference-in-Differences",
            "score": _opportunity_score(80, has_rows=rows > 0),
            "why": "Treatment/control structure plus a post-period indicator and numeric outcome make a DiD specification structurally possible.",
            "needs": ["treatment indicator", "post indicator", "numeric outcome"],
            "decision_examples": ["Did the rollout change outcomes relative to control?"],
        })

    if has("treatment") and has("relative_time") and (has("unit") or has("id")) and has("date"):
        ops.append({
            "id": "event_study", "title": "Panel event study",
            "score": _opportunity_score(78, has_rows=rows > 0, bonuses=5 if rows>=200 else 0),
            "why": "Treatment, relative event time, unit identity, and calendar time can support dynamic pre/post effect estimation.",
            "needs": ["unit", "calendar time", "relative event time", "treatment", "outcome"],
            "decision_examples": ["How did the effect evolve before and after rollout?"],
        })

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) >= 2:
        ops.append({
            "id": "regression_family",
            "title": "Driver / predictive relationship analysis",
            "score": _opportunity_score(64, has_rows=rows > 0, bonuses=8 if rows >= 200 else 0),
            "why": "Multiple numeric variables can support regression-style driver analysis once a target and prediction-versus-causation goal are defined.",
            "needs": ["explicit target", "candidate predictors"],
            "decision_examples": ["What predicts conversion?", "Which factors are associated with revenue?"],
        })

    if not ops:
        ops.append({
            "id": "eda",
            "title": "Structured exploratory analysis",
            "score": 55,
            "why": "The dataset does not expose a high-confidence specialized path yet. Start by understanding distributions, quality, and plausible decisions.",
            "needs": ["clarify decision or target"],
            "decision_examples": ["What matters in this dataset?"],
        })

    return sorted(ops, key=lambda x: x["score"], reverse=True)[:6]


def _question_type(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ("cause", "caused", "incremental", "incrementality", "impact", "effect", "lift")):
        return "causal"
    if any(x in q for x in ("predict", "likelihood", "propensity", "forecast", "churn")):
        return "predictive"
    if any(x in q for x in ("which", "compare", "best", "worse", "more budget", "cut")):
        return "comparative"
    return "exploratory/descriptive"


def _question_assessment(question: str, role_map: dict[str, list[str]]) -> dict[str, Any]:
    if not question.strip():
        return {
            "question_type": "unspecified",
            "status": "open_exploration",
            "blockers": [],
            "available_evidence": [k for k, v in role_map.items() if v],
        }

    q = question.lower()
    qtype = _question_type(question)
    blockers: list[str] = []
    available = [k for k, v in role_map.items() if v]

    if any(x in q for x in ("roas", "profit", "profitable", "return on ad")):
        if not role_map.get("spend"):
            blockers.append("No obvious spend/cost field was detected.")
        if not role_map.get("revenue"):
            blockers.append("No obvious revenue/value field was detected.")
    if any(x in q for x in ("cac", "acquisition cost")):
        if not role_map.get("spend"):
            blockers.append("CAC needs spend/cost.")
        if not (role_map.get("conversions") or role_map.get("customer")):
            blockers.append("CAC needs acquisition counts or customer identifiers.")
    if qtype == "causal" and not role_map.get("treatment"):
        blockers.append("The question is causal, but no obvious treatment/control/variant field was detected. Observed performance alone cannot establish incrementality.")
    if qtype == "causal" and role_map.get("treatment") and not (role_map.get("binary_outcome") or role_map.get("continuous_outcome") or role_map.get("conversions") or role_map.get("revenue")):
        blockers.append("A treatment field exists, but CampaignLab cannot identify a usable outcome for the causal question.")
    if qtype == "predictive" and not (role_map.get("binary_outcome") or role_map.get("continuous_outcome") or role_map.get("revenue") or role_map.get("conversions")):
        blockers.append("The question is predictive, but no obvious prediction target was detected. Specify or add the outcome to predict.")

    return {
        "question_type": qtype,
        "status": "blocked" if blockers else "provisionally_answerable",
        "blockers": blockers,
        "available_evidence": available,
        "important_note": "Schema fit is only the first gate. Method-specific identification and assumption checks still decide whether a causal or statistical conclusion is defensible.",
    }


def analyze_dataset_intelligence(
    df: pd.DataFrame,
    question: str = "",
    role_overrides: dict[str, str | None] | None = None,
) -> DatasetIntelligence:
    rows, cols = df.shape
    role_map: dict[str, list[str]] = {k: [] for k in ROLE_ALIASES}
    signals: list[ColumnSignal] = []

    for col in df.columns:
        s = df[col]
        non_null = int(s.notna().sum())
        unique = int(s.nunique(dropna=True))
        roles = _infer_roles(str(col), s, rows)
        for role in roles:
            role_map.setdefault(role, []).append(str(col))

        nmin = nmax = None
        if pd.api.types.is_numeric_dtype(s):
            numeric = pd.to_numeric(s, errors="coerce").dropna()
            if not numeric.empty:
                nmin = float(numeric.min())
                nmax = float(numeric.max())

        signals.append(ColumnSignal(
            column=str(col),
            dtype=str(s.dtype),
            semantic_type=_semantic_type(s),
            roles=roles,
            non_null=non_null,
            unique=unique,
            missing_rate=float(s.isna().mean()) if rows else 0.0,
            cardinality_ratio=float(unique / max(1, non_null)),
            numeric_min=nmin,
            numeric_max=nmax,
        ))

    # de-duplicate roles
    role_map = {k: list(dict.fromkeys(v)) for k, v in role_map.items()}

    # Consequential user-confirmed mappings are sovereign over schema inference.
    # This is a real contract, not a cosmetic UI choice: downstream readiness,
    # ranking, visualization planning and the deterministic tool runtime all see
    # the same resolved role map.
    if role_overrides:
        for role, column in role_overrides.items():
            if role not in role_map:
                raise ValueError(f"Unknown analytical role override: {role}")
            if column is None:
                # Explicitly unresolved consequential roles are removed from
                # downstream eligibility rather than letting auto-inference
                # quietly choose among ambiguous candidates.
                role_map[role] = []
                continue
            if column not in df.columns:
                raise ValueError(f"Mapped column {column!r} for role {role!r} was not found in the dataset.")
            # A resolved role means exactly this column for that role. Other
            # automatically inferred candidates no longer remain ambiguous.
            role_map[role] = [str(column)]

    return DatasetIntelligence(
        rows=rows,
        columns=cols,
        grain_guess=_grain_guess(df, role_map),
        column_signals=[asdict(s) for s in signals],
        role_map=role_map,
        quality_findings=_quality_findings(df, signals, role_map),
        analytical_opportunities=_opportunities(df, role_map),
        question_assessment=_question_assessment(question, role_map),
    )
