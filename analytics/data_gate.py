from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import pandas as pd
import numpy as np


@dataclass
class ReadinessCheck:
    key: str
    label: str
    status: str  # pass | warn | fail
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessReport:
    family: str
    score: int
    status: str  # ready | caution | blocked
    checks: list[ReadinessCheck]
    blockers: list[str]
    warnings: list[str]
    strengths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "score": self.score,
            "status": self.status,
            "checks": [c.to_dict() for c in self.checks],
            "blockers": self.blockers,
            "warnings": self.warnings,
            "strengths": self.strengths,
        }


def _finalize(family: str, checks: list[ReadinessCheck]) -> ReadinessReport:
    weights = {"pass": 1.0, "warn": 0.55, "fail": 0.0}
    score = round(100 * sum(weights[c.status] for c in checks) / max(len(checks), 1))
    blockers = [c.message for c in checks if c.status == "fail"]
    warnings = [c.message for c in checks if c.status == "warn"]
    strengths = [c.message for c in checks if c.status == "pass"]
    status = "blocked" if blockers else ("caution" if warnings else "ready")
    return ReadinessReport(family, score, status, checks, blockers, warnings, strengths)


def prediction_readiness(df: pd.DataFrame, target: str | None = None, predictors: list[str] | None = None, task: str = "auto") -> ReadinessReport:
    checks: list[ReadinessCheck] = []
    rows = len(df)
    predictors = predictors or []
    checks.append(ReadinessCheck("rows", "Labeled history", "pass" if rows >= 100 else ("warn" if rows >= 50 else "fail"), f"{rows:,} rows available; richer predictive models need enough labeled history to validate out-of-sample."))
    if target and target in df:
        y = df[target]
        nonmissing = int(y.notna().sum())
        checks.append(ReadinessCheck("target_missing", "Target coverage", "pass" if nonmissing / max(rows,1) >= .9 else ("warn" if nonmissing / max(rows,1) >= .7 else "fail"), f"{nonmissing:,} of {rows:,} rows have a usable target."))
        unique = y.dropna().nunique()
        inferred = "classification" if unique <= 2 else "regression"
        task = inferred if task == "auto" else task
        if task == "classification" and unique <= 2:
            counts = y.dropna().value_counts()
            minority = int(counts.min()) if len(counts) else 0
            checks.append(ReadinessCheck("class_balance", "Class support", "pass" if minority >= 50 else ("warn" if minority >= 20 else "fail"), f"Minority class has {minority:,} observations; tiny classes make validation unstable."))
    else:
        checks.append(ReadinessCheck("target", "Defined target", "fail", "Choose the outcome CampaignLab should predict before fitting a predictive model."))
    usable_predictors = [p for p in predictors if p in df and df[p].nunique(dropna=True) > 1]
    checks.append(ReadinessCheck("predictors", "Usable predictors", "pass" if len(usable_predictors) >= 2 else ("warn" if len(usable_predictors) == 1 else "fail"), f"{len(usable_predictors):,} non-constant predictor(s) selected."))
    ratio = rows / max(len(usable_predictors), 1)
    checks.append(ReadinessCheck("complexity", "Data vs model complexity", "pass" if ratio >= 30 else ("warn" if ratio >= 15 else "fail"), f"About {ratio:.1f} rows per selected predictor; low ratios increase overfitting risk."))
    if rows >= 80:
        checks.append(ReadinessCheck("holdout", "Holdout feasibility", "pass", "Enough rows exist to reserve a meaningful holdout instead of reporting only in-sample fit."))
    else:
        checks.append(ReadinessCheck("holdout", "Holdout feasibility", "warn", "A holdout is possible but will be small; keep model complexity conservative."))
    return _finalize("prediction", checks)


def forecasting_readiness(df: pd.DataFrame, date_col: str | None, target_col: str | None, seasonal_period: int | None = None, horizon: int = 4) -> ReadinessReport:
    checks: list[ReadinessCheck] = []
    if not date_col or date_col not in df:
        checks.append(ReadinessCheck("date", "Time index", "fail", "Forecasting needs a usable date/time column."))
        return _finalize("forecasting", checks)
    if not target_col or target_col not in df:
        checks.append(ReadinessCheck("target", "Forecast target", "fail", "Choose the numeric outcome to forecast."))
        return _finalize("forecasting", checks)
    dates = pd.to_datetime(df[date_col], errors="coerce")
    target = pd.to_numeric(df[target_col], errors="coerce")
    valid = pd.DataFrame({"date": dates, "target": target}).dropna().sort_values("date")
    n = len(valid)
    checks.append(ReadinessCheck("history", "Historical depth", "pass" if n >= 52 else ("warn" if n >= 24 else "fail"), f"{n:,} usable time observations are available."))
    if n >= 3:
        deltas = valid["date"].diff().dropna().dt.total_seconds()
        regularity = float((deltas == deltas.mode().iloc[0]).mean()) if len(deltas) else 0
        checks.append(ReadinessCheck("regularity", "Regular time spacing", "pass" if regularity >= .9 else ("warn" if regularity >= .7 else "fail"), f"{regularity:.0%} of time gaps match the dominant frequency."))
    if seasonal_period:
        cycles = n / max(seasonal_period, 1)
        checks.append(ReadinessCheck("seasonality", "Seasonal coverage", "pass" if cycles >= 3 else ("warn" if cycles >= 2 else "fail"), f"History covers about {cycles:.1f} seasonal cycles at period {seasonal_period}."))
    ratio = n / max(horizon, 1)
    checks.append(ReadinessCheck("horizon", "History vs forecast horizon", "pass" if ratio >= 8 else ("warn" if ratio >= 4 else "fail"), f"History is {ratio:.1f}× the requested {horizon}-period forecast horizon."))
    checks.append(ReadinessCheck("backtest", "Backtest feasibility", "pass" if n >= max(30, horizon * 6) else "warn", "CampaignLab can reserve later periods for rolling or holdout forecast validation." if n >= max(30, horizon * 6) else "History is thin for robust rolling backtests; forecast uncertainty should be treated cautiously."))
    return _finalize("forecasting", checks)
