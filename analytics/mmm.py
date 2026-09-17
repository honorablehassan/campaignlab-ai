from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear, minimize
from sklearn.metrics import r2_score, mean_absolute_error

from analytics.data_gate import ReadinessCheck, ReadinessReport


@dataclass
class MMMReadiness:
    report: ReadinessReport
    date_col: str
    outcome_col: str
    media_cols: list[str]
    control_cols: list[str]
    frequency: str
    observations: int
    high_correlations: list[tuple[str, str, float]]

    def to_dict(self):
        d = asdict(self)
        d["report"] = self.report.to_dict()
        return d


def geometric_adstock(x: np.ndarray, alpha: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x, dtype=float)
    for i, value in enumerate(x):
        out[i] = value + (alpha * out[i-1] if i else 0.0)
    return out


def saturation(x: np.ndarray, scale: float) -> np.ndarray:
    scale = max(float(scale), 1e-9)
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    return 1.0 - np.exp(-x / scale)


def hill_saturation(x: np.ndarray, half_saturation: float, slope: float = 1.0) -> np.ndarray:
    """Bounded Hill response curve with an interpretable half-saturation point."""
    half_saturation = max(float(half_saturation), 1e-9)
    slope = max(float(slope), 1e-6)
    x = np.maximum(np.asarray(x, dtype=float), 0.0)
    powered = np.power(x, slope)
    return powered / (powered + np.power(half_saturation, slope))


def media_response(x: np.ndarray, transform: dict[str, Any]) -> np.ndarray:
    family = transform.get("saturation_family", "exponential")
    scale = float(transform["saturation_scale"])
    if family == "hill":
        return hill_saturation(x, scale, float(transform.get("saturation_slope", 1.0)))
    return saturation(x, scale)


def _infer_frequency(dates: pd.Series) -> str:
    if len(dates) < 3:
        return "unknown"
    delta = dates.sort_values().diff().dropna().dt.days.median()
    if delta <= 2: return "daily"
    if delta <= 10: return "weekly"
    if delta <= 40: return "monthly"
    return "irregular"


def mmm_readiness(df: pd.DataFrame, date_col: str, outcome_col: str, media_cols: list[str], control_cols: list[str] | None = None) -> MMMReadiness:
    control_cols = control_cols or []
    checks: list[ReadinessCheck] = []
    missing = [c for c in [date_col, outcome_col, *media_cols, *control_cols] if c not in df]
    if missing:
        checks.append(ReadinessCheck("columns", "Required fields", "fail", f"Missing columns: {', '.join(missing)}"))
        report = ReadinessReport("mmm", 0, "blocked", checks, [checks[0].message], [], [])
        return MMMReadiness(report, date_col, outcome_col, media_cols, control_cols, "unknown", 0, [])

    d = df[[date_col, outcome_col, *media_cols, *control_cols]].copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    for c in [outcome_col, *media_cols, *control_cols]:
        d[c] = pd.to_numeric(d[c], errors="coerce").replace([np.inf, -np.inf], np.nan)

    invalid_date_share = float(d[date_col].isna().mean()) if len(d) else 1.0
    checks.append(ReadinessCheck(
        "date_validity", "Time field validity",
        "pass" if invalid_date_share == 0 else "fail",
        f"{invalid_date_share:.1%} of time values are missing or unparseable." +
        (" Resolve time parsing before MMM; CampaignLab will not silently discard invalid periods." if invalid_date_share else "")
    ))

    core_cols = [outcome_col, *media_cols]
    missing_share = float(d[core_cols].isna().mean().max()) if len(d) else 1.0
    checks.append(ReadinessCheck(
        "missing", "Core data coverage",
        "pass" if missing_share == 0 else "fail",
        f"Worst missing/non-finite share across outcome/media fields is {missing_share:.1%}." +
        (" Resolve missing media/outcome periods before fitting; CampaignLab will not silently convert unknown spend to zero or discard unknown outcomes." if missing_share else "")
    ))

    bad_controls=[]
    for c in control_cols:
        original_non_null = int(df[c].notna().sum())
        numeric_non_null = int(d[c].notna().sum())
        if original_non_null and numeric_non_null / original_non_null < .8:
            bad_controls.append(c)
    checks.append(ReadinessCheck(
        "control_types", "Control field compatibility",
        "pass" if not bad_controls else "fail",
        "Selected controls are numeric or numeric-like." if not bad_controls else
        f"These controls are mostly non-numeric and are not supported by the beta MMM yet: {', '.join(bad_controls)}. Encode them explicitly or use numeric indicators."
    ))

    d = d.dropna(subset=[date_col, outcome_col]).sort_values(date_col)
    n = len(d)
    freq = _infer_frequency(d[date_col])
    checks.append(ReadinessCheck("history", "Historical depth", "pass" if n >= 104 else ("warn" if n >= 52 else "fail"), f"{n:,} usable {freq} observations. Two years of weekly history is a strong starting point; shorter histories require more caution."))
    channel_status = "pass" if 2 <= len(media_cols) <= 8 else ("warn" if 1 <= len(media_cols) <= 12 else "fail")
    channel_detail = ("A single channel can be modeled, but this is closer to a response model than a true marketing mix." if len(media_cols) == 1 else "Too many channels relative to history makes contribution harder to identify." if len(media_cols) > 8 else "Channel count is reasonable for the available history.")
    checks.append(ReadinessCheck("channels", "Channel scope", channel_status, f"{len(media_cols):,} media channel(s) selected. {channel_detail}"))

    outcome_values = d[outcome_col].dropna()
    outcome_cv = float(outcome_values.std(ddof=0) / max(abs(outcome_values.mean()), 1e-9)) if len(outcome_values) else 0.0
    checks.append(ReadinessCheck("outcome_variation", "Outcome variation", "pass" if outcome_values.nunique() >= 4 and outcome_cv >= .005 else "fail", f"Outcome has {outcome_values.nunique():,} distinct value(s) and {outcome_cv:.1%} relative variation. MMM needs outcome movement to explain."))

    negative_media = [c for c in media_cols if (d[c].dropna() < 0).any()]
    checks.append(ReadinessCheck("nonnegative_media", "Media spend validity", "pass" if not negative_media else "fail", "Media spend is non-negative." if not negative_media else f"Negative media spend found in: {', '.join(negative_media)}. Reconcile credits/refunds before MMM rather than clipping them silently."))

    weak_variation = []
    for c in media_cols:
        s = d[c].dropna()
        mean = float(s.mean()) if len(s) else 0
        cv = float(s.std(ddof=0) / mean) if mean > 0 else 0
        if s.nunique() < 4 or cv < .08: weak_variation.append(c)
    checks.append(ReadinessCheck("variation", "Spend variation", "pass" if not weak_variation else ("warn" if len(weak_variation) < len(media_cols) else "fail"), "Media spend changes enough over time to learn response patterns." if not weak_variation else f"Weak spend variation detected for: {', '.join(weak_variation)}."))

    corr = d[media_cols].corr(numeric_only=True)
    high_corr: list[tuple[str,str,float]] = []
    for i,a in enumerate(media_cols):
        for b in media_cols[i+1:]:
            v = float(corr.loc[a,b]) if a in corr and b in corr else np.nan
            if np.isfinite(v) and abs(v) >= .75: high_corr.append((a,b,v))
    checks.append(ReadinessCheck("collinearity", "Channel separation", "pass" if not high_corr else ("warn" if max(abs(x[2]) for x in high_corr) < .9 else "fail"), "No severe channel-spend correlation detected." if not high_corr else f"{len(high_corr)} highly correlated media pair(s) may be hard to separate."))

    control_msg = f"{len(control_cols)} explicit non-media control(s) selected."
    checks.append(ReadinessCheck("controls", "Alternative demand drivers", "pass" if len(control_cols) >= 2 else "warn", control_msg + (" This helps keep promotions, pricing or other demand drivers from being miscredited to media." if control_cols else " Add promotions, pricing, holidays or other known demand drivers when available.")))

    duplicate_periods = int(d[date_col].duplicated().sum())
    checks.append(ReadinessCheck("unique_periods", "One row per time period", "pass" if duplicate_periods == 0 else "fail", "Each modeled period appears once." if duplicate_periods == 0 else f"{duplicate_periods:,} duplicate time period row(s) detected. Aggregate or reconcile them before MMM."))
    if n >= 3:
        gaps = d[date_col].diff().dropna().dt.days
        mode = gaps.mode().iloc[0] if len(gaps) else np.nan
        regular = float((gaps == mode).mean()) if len(gaps) else 0.0
    else: regular = 0
    checks.append(ReadinessCheck("regularity", "Time alignment", "pass" if regular >= .9 else ("warn" if regular >= .75 else "fail"), f"{regular:.0%} of time gaps match the dominant spacing; MMM is safer on aligned regular periods."))

    weights={"pass":1.0,"warn":.55,"fail":0.0}; score=round(100*sum(weights[c.status] for c in checks)/len(checks))
    blockers=[c.message for c in checks if c.status=="fail"]; warnings=[c.message for c in checks if c.status=="warn"]; strengths=[c.message for c in checks if c.status=="pass"]
    status="blocked" if blockers else ("caution" if warnings else "ready")
    report=ReadinessReport("mmm",score,status,checks,blockers,warnings,strengths)
    return MMMReadiness(report,date_col,outcome_col,media_cols,control_cols,freq,n,high_corr)


def _baseline_features(dates: pd.Series, controls: pd.DataFrame) -> tuple[np.ndarray,list[str]]:
    n=len(dates); t=np.arange(n,dtype=float)
    cols=[np.ones(n), (t-t.mean())/(t.std() or 1)]
    names=["baseline","trend"]
    # Fourier annual-ish seasonality for weekly/monthly series. Harmless low-frequency basis for other regular grains.
    period = 52.0 if _infer_frequency(dates)=="weekly" else (12.0 if _infer_frequency(dates)=="monthly" else 365.25)
    for k in (1,2):
        cols += [np.sin(2*np.pi*k*t/period), np.cos(2*np.pi*k*t/period)]
        names += [f"season_sin_{k}",f"season_cos_{k}"]
    for c in controls.columns:
        s=pd.to_numeric(controls[c],errors="coerce").fillna(controls[c].median() if controls[c].notna().any() else 0).to_numpy(float)
        sd=s.std(); cols.append((s-s.mean())/(sd or 1)); names.append(c)
    return np.column_stack(cols),names


def _choose_media_transform(spend: np.ndarray, outcome: np.ndarray, baseline_x: np.ndarray) -> tuple[dict[str, Any], np.ndarray]:
    # Select a conservative transformation on training data only. This is not causal identification;
    # it is a deterministic response-shape choice used by the beta MMM.
    base_beta=np.linalg.lstsq(baseline_x,outcome,rcond=None)[0]
    residual=outcome-baseline_x@base_beta
    best=None
    for alpha in (0.0,.25,.5,.7,.85):
        ad=geometric_adstock(np.maximum(spend,0),alpha)
        positives=ad[ad>0]
        if not len(positives):
            candidates=[("exponential",1.0,1.0,np.zeros_like(ad))]
        else:
            scales=sorted({float(np.quantile(positives,q)) for q in (.35,.50,.65,.80)})
            candidates=[]
            for scale in scales:
                candidates.append(("exponential",scale,1.0,saturation(ad,scale)))
                for slope in (.7,1.0,1.5,2.0):
                    candidates.append(("hill",scale,slope,hill_saturation(ad,scale,slope)))
        for family,scale,slope,sat in candidates:
            corr=np.corrcoef(sat,residual)[0,1] if np.std(sat)>0 and np.std(residual)>0 else 0.0
            score=abs(float(corr)) if np.isfinite(corr) else 0.0
            # Prefer simpler curves when fit is effectively tied.
            complexity_penalty=.001 if family=="hill" else 0.0
            score-=complexity_penalty
            if best is None or score>best[0]:
                best=(score,{"adstock_alpha":float(alpha),"saturation_scale":float(scale),"saturation_family":family,"saturation_slope":float(slope)},sat)
    return best[1],best[2]


def _fit_constrained_ridge(X: np.ndarray, y: np.ndarray, media_start: int, lam: float) -> np.ndarray:
    lower=np.full(X.shape[1],-np.inf); lower[media_start:]=0.0
    upper=np.full(X.shape[1],np.inf)
    reg=np.sqrt(lam)*np.eye(X.shape[1]); reg[0,0]=0
    fit=lsq_linear(np.vstack([X,reg]),np.concatenate([y,np.zeros(X.shape[1])]),bounds=(lower,upper),lsmr_tol="auto")
    return fit.x


def _rolling_splits(training_end: int) -> list[tuple[int, int]]:
    validation=max(6,min(13,training_end//6))
    starts=sorted({max(30,training_end-validation*k) for k in (3,2,1)})
    return [(start,min(start+validation,training_end)) for start in starts if start < training_end]


def _block_resample(values: np.ndarray, block_size: int, rng: np.random.Generator) -> np.ndarray:
    if not len(values): return values.copy()
    starts=rng.integers(0,max(1,len(values)-block_size+1),size=int(np.ceil(len(values)/block_size)))
    return np.concatenate([values[s:s+block_size] for s in starts])[:len(values)]


def fit_mmm(
    df: pd.DataFrame,
    date_col: str,
    outcome_col: str,
    media_cols: list[str],
    control_cols: list[str] | None = None,
    uncertainty_samples: int = 30,
    experiment_calibrations: list[dict[str, Any]] | None = None,
) -> dict[str,Any]:
    control_cols=control_cols or []
    ready=mmm_readiness(df,date_col,outcome_col,media_cols,control_cols)
    if ready.report.status=="blocked":
        raise ValueError("MMM readiness is blocked: " + " ".join(ready.report.blockers[:2]))
    d=df[[date_col,outcome_col,*media_cols,*control_cols]].copy()
    d[date_col]=pd.to_datetime(d[date_col],errors="coerce")
    for c in [outcome_col,*media_cols,*control_cols]:
        d[c]=pd.to_numeric(d[c],errors="coerce").replace([np.inf,-np.inf],np.nan)
    d=d.dropna(subset=[date_col,outcome_col]).sort_values(date_col).reset_index(drop=True)
    if d[media_cols].isna().any().any():
        raise ValueError("MMM media fields contain missing/non-finite values. CampaignLab will not silently convert unknown spend to zero.")
    for c in media_cols: d[c]=d[c].clip(lower=0)
    for c in control_cols: d[c]=d[c].fillna(d[c].median())
    n=len(d); split=max(int(n*.8), n-26); split=min(max(split,30),n-8)
    y=d[outcome_col].to_numpy(float)
    base_x,base_names=_baseline_features(d[date_col],d[control_cols])
    transforms={}; media_x=[]
    for c in media_cols:
        transform,_=_choose_media_transform(d.loc[:split-1,c].to_numpy(float),y[:split],base_x[:split])
        full_sat=media_response(geometric_adstock(d[c].to_numpy(float),transform["adstock_alpha"]),transform)
        transforms[c]=transform
        media_x.append(full_sat)
    mx=np.column_stack(media_x)
    X=np.column_stack([base_x,mx])
    media_start=base_x.shape[1]
    best=None; rolling=[]
    folds=_rolling_splits(split)
    for lam in (.01,.1,1.0,10.0,100.0):
        fold_wapes=[]
        for train_end,val_end in folds:
            fold_beta=_fit_constrained_ridge(X[:train_end],y[:train_end],media_start,lam)
            actual=y[train_end:val_end]; forecast=X[train_end:val_end]@fold_beta
            fold_wapes.append(float(np.abs(actual-forecast).sum()/max(np.abs(actual).sum(),1e-9)))
        score=float(np.mean(fold_wapes)) if fold_wapes else np.inf
        rolling.append({"ridge_lambda":float(lam),"mean_wape":score,"fold_wapes":fold_wapes})
        if best is None or score<best[0]: best=(score,lam)
    _,lam=best
    beta=_fit_constrained_ridge(X[:split],y[:split],media_start,lam)
    uncalibrated_beta=beta.copy()
    boot_coefficients=[]
    uncertainty_samples=max(0,min(int(uncertainty_samples),200))
    if uncertainty_samples:
        rng=np.random.default_rng(20260904)
        fitted_train=X[:split]@beta; residuals=y[:split]-fitted_train
        block_size=max(2,min(8,int(round(np.sqrt(split)/2))))
        for _ in range(uncertainty_samples):
            boot_y=fitted_train+_block_resample(residuals,block_size,rng)
            boot_coefficients.append(_fit_constrained_ridge(X[:split],boot_y,media_start,lam)[media_start:])
    boot=np.asarray(boot_coefficients,float) if boot_coefficients else np.empty((0,len(media_cols)))

    # Optional experiment calibration. The experiment supplies an incremental
    # outcome and uncertainty for a known spend contrast. CampaignLab converts
    # that contrast onto the selected response scale, then precision-weights it
    # with the conditional MMM coefficient distribution.
    calibration_details=[]
    for item in experiment_calibrations or []:
        channel=str(item.get("channel") or "")
        if channel not in media_cols:
            raise ValueError(f"Experiment calibration channel {channel!r} is not in the modeled media channels.")
        baseline_spend=float(item["baseline_spend"]); treatment_spend=float(item["treatment_spend"])
        incremental=float(item["incremental_outcome"]); standard_error=float(item["standard_error"])
        if baseline_spend < 0 or treatment_spend < 0 or standard_error <= 0:
            raise ValueError("Experiment calibration spend must be non-negative and standard_error must be positive.")
        j=media_cols.index(channel); info=transforms[channel]
        steady=np.asarray([baseline_spend,treatment_spend],float)/max(1-float(info["adstock_alpha"]),1e-6)
        response_delta=float(np.diff(media_response(steady,info))[0])
        if abs(response_delta) < 1e-8:
            raise ValueError(f"Experiment calibration for {channel} has too little modeled response contrast to identify a coefficient.")
        experimental_beta=incremental/response_delta
        experimental_se=standard_error/abs(response_delta)
        model_beta=float(beta[media_start+j])
        model_se=float(np.std(boot[:,j],ddof=1)) if len(boot)>1 else max(abs(model_beta)*.5,1e-6)
        model_precision=1/max(model_se**2,1e-12); experiment_precision=1/max(experimental_se**2,1e-12)
        combined=max(0.0,(model_beta*model_precision+experimental_beta*experiment_precision)/(model_precision+experiment_precision))
        experiment_weight=float(experiment_precision/(model_precision+experiment_precision))
        beta[media_start+j]=combined
        if len(boot):
            exp_draws=rng.normal(experimental_beta,experimental_se,size=len(boot))
            boot[:,j]=np.maximum(0.0,(boot[:,j]*model_precision+exp_draws*experiment_precision)/(model_precision+experiment_precision))
        calibration_details.append({
            "channel":channel,"baseline_spend":baseline_spend,"treatment_spend":treatment_spend,
            "incremental_outcome":incremental,"standard_error":standard_error,
            "response_delta":response_delta,"model_coefficient_before":model_beta,
            "experimental_coefficient":float(experimental_beta),"coefficient_after":float(combined),
            "experiment_weight":experiment_weight,
            "scope":"Precision-weighted conditional calibration on the selected response transformation; not a full Bayesian prior or universal causal correction.",
        })

    holdout_mae=float(mean_absolute_error(y[split:],X[split:]@beta))
    pred=X@beta
    r2=float(r2_score(y,pred)); holdout_pred=pred[split:]; holdout_y=y[split:]
    holdout_wape=float(np.abs(holdout_y-holdout_pred).sum()/max(np.abs(holdout_y).sum(),1e-9))
    # Devil's-advocate benchmark: media must improve unseen-period prediction over baseline + controls.
    base_fit=np.linalg.lstsq(base_x[:split],y[:split],rcond=None)[0]
    base_holdout_pred=base_x[split:]@base_fit
    baseline_holdout_wape=float(np.abs(holdout_y-base_holdout_pred).sum()/max(np.abs(holdout_y).sum(),1e-9))
    media_holdout_improvement=float((baseline_holdout_wape-holdout_wape)/max(baseline_holdout_wape,1e-9))

    # Multiple expanding-window backtests reveal whether final-holdout quality
    # is representative or a lucky period.
    backtests=[]
    for train_end,val_end in _rolling_splits(split):
        fold_beta=_fit_constrained_ridge(X[:train_end],y[:train_end],media_start,lam)
        actual=y[train_end:val_end]; forecast=X[train_end:val_end]@fold_beta
        fold_wape=float(np.abs(actual-forecast).sum()/max(np.abs(actual).sum(),1e-9))
        fold_base=np.linalg.lstsq(base_x[:train_end],y[:train_end],rcond=None)[0]
        fold_base_pred=base_x[train_end:val_end]@fold_base
        fold_base_wape=float(np.abs(actual-fold_base_pred).sum()/max(np.abs(actual).sum(),1e-9))
        backtests.append({
            "train_periods":int(train_end),"validation_periods":int(val_end-train_end),
            "wape":fold_wape,"baseline_wape":fold_base_wape,
            "media_improvement":float((fold_base_wape-fold_wape)/max(fold_base_wape,1e-9)),
        })

    # Leave-one-control-out sensitivity asks how much channel contribution
    # changes when each observed alternative demand driver is removed.
    sensitivity=[]
    reference_totals=np.asarray([float((mx[:,j]*uncalibrated_beta[media_start+j]).sum()) for j in range(len(media_cols))])
    for control in control_cols:
        control_index=base_names.index(control)
        reduced_base=np.delete(base_x,control_index,axis=1)
        reduced_X=np.column_stack([reduced_base,mx])
        reduced_beta=_fit_constrained_ridge(reduced_X[:split],y[:split],reduced_base.shape[1],lam)
        reduced_totals=np.asarray([float((mx[:,j]*reduced_beta[reduced_base.shape[1]+j]).sum()) for j in range(len(media_cols))])
        relative=np.abs(reduced_totals-reference_totals)/np.maximum(np.abs(reference_totals),1e-9)
        sensitivity.append({
            "removed_control":control,"max_channel_contribution_change":float(np.max(relative)),
            "mean_channel_contribution_change":float(np.mean(relative)),
        })
    contributions={}
    for j,c in enumerate(media_cols):
        contrib=mx[:,j]*beta[media_start+j]
        boot_totals=boot[:,j,None]*mx[:,j] if len(boot) else np.empty((0,n))
        ci=(np.quantile(boot_totals.sum(axis=1),[.025,.975]) if len(boot) else [np.nan,np.nan])
        contributions[c]={"total":float(contrib.sum()),"total_ci_low":float(ci[0]),"total_ci_high":float(ci[1]),"mean_period":float(contrib.mean()),"share_of_modeled_media":0.0,"coefficient":float(beta[media_start+j]),**transforms[c]}
    total_media=sum(v["total"] for v in contributions.values())
    for v in contributions.values(): v["share_of_modeled_media"]=float(v["total"]/total_media) if total_media>0 else 0.0
    baseline=pred-sum(mx[:,j]*beta[media_start+j] for j in range(len(media_cols)))
    # evidence strength is intentionally conservative and diagnostic, not a causal probability.
    corr_penalty=max([abs(v) for _,_,v in ready.high_correlations],default=0)
    positive_backtest_share=(
        float(np.mean([fold["media_improvement"] > 0 for fold in backtests]))
        if backtests else 0.0
    )
    max_control_sensitivity=max(
        [row["max_channel_contribution_change"] for row in sensitivity],
        default=0.0,
    )
    if media_holdout_improvement < .02:
        strength="Limited"
    elif (
        holdout_wape<=.12 and ready.report.score>=80 and corr_penalty<.8
        and media_holdout_improvement>=.05 and positive_backtest_share>=.67
        and max_control_sensitivity<.75
    ):
        strength="Moderate"
    elif (
        holdout_wape<=.20 and ready.report.score>=65
        and positive_backtest_share>=.5 and max_control_sensitivity<1.5
    ):
        strength="Limited-to-moderate"
    else: strength="Limited"
    return {
        "method":"marketing_mix_model_native_v2",
        "status":"Beta",
        "readiness":ready.to_dict(),
        "n_observations":n,
        "holdout_periods":n-split,
        "model":{"r2":r2,"holdout_mae":float(holdout_mae),"holdout_wape":holdout_wape,"baseline_holdout_wape":baseline_holdout_wape,"media_holdout_improvement":media_holdout_improvement,"ridge_lambda":float(lam),"rolling_validation":rolling,"expanding_window_backtests":backtests,"positive_backtest_share":positive_backtest_share,"control_sensitivity":sensitivity,"max_control_sensitivity":max_control_sensitivity,"experiment_calibration":calibration_details,"uncertainty_samples":uncertainty_samples,"uncertainty_scope":"Conditional residual block bootstrap; calibrated channels also include supplied experiment standard error. Response-shape and remaining causal-identification uncertainty are not included.","evidence_strength":strength},
        "channels":contributions,
        "baseline_total":float(baseline.sum()),
        "actual_total":float(y.sum()),
        "predicted_total":float(pred.sum()),
        "series":pd.DataFrame({date_col:d[date_col],"actual":y,"predicted":pred,"baseline":baseline}).to_dict("records"),
        "warning":"This native V2 beta MMM estimates observational contribution under explicit model assumptions. Conditional intervals do not include every source of model uncertainty and do not prove causality. Supplied experiments calibrate only their stated channel, contrast, population, outcome and period.",
    }


def optimize_budget(df: pd.DataFrame, model_result: dict[str,Any], media_cols: list[str], total_weekly_budget: float | None = None) -> dict[str,Any]:
    current={c:float(pd.to_numeric(df[c],errors="coerce").fillna(0).tail(min(8,len(df))).mean()) for c in media_cols}
    total=float(total_weekly_budget if total_weekly_budget is not None else sum(current.values()))
    if total<=0: raise ValueError("Budget must be positive.")
    channels=model_result["channels"]
    upper=[]
    for c in media_cols:
        s=pd.to_numeric(df[c],errors="coerce").fillna(0)
        hist=float(s.quantile(.95))
        upper.append(max(hist*1.35,current[c]*1.35,total*.05))
    supported_total=float(sum(upper))
    if supported_total < total:
        raise ValueError(f"Requested weekly budget ({total:,.0f}) exceeds the beta model's historically supported allocation range ({supported_total:,.0f}). CampaignLab will not manufacture extrapolation room to make the optimizer feasible.")
    x0=np.array([current[c] for c in media_cols],float)
    if x0.sum()<=0: x0=np.full(len(media_cols),total/len(media_cols))
    else: x0=x0/x0.sum()*total
    def expected_media(x):
        val=0.0
        for i,c in enumerate(media_cols):
            info=channels[c]; alpha=info["adstock_alpha"]; beta=info["coefficient"]
            steady=x[i]/max(1-alpha,1e-6)
            val += beta*float(media_response(np.asarray([steady]),info)[0])
        return val
    res=minimize(lambda x:-expected_media(x),x0,bounds=[(0,u) for u in upper],constraints={"type":"eq","fun":lambda x:x.sum()-total},method="SLSQP",options={"maxiter":500,"ftol":1e-10})
    x=res.x if res.success else x0
    return {"total_weekly_budget":total,"current":current,"recommended":{c:float(x[i]) for i,c in enumerate(media_cols)},"modeled_media_response_current":float(expected_media(x0)),"modeled_media_response_recommended":float(expected_media(x)),"optimizer_status":"ok" if res.success else "fallback","guardrail":"Optimizer stays near the historical support of each channel; it should not be treated as a causal guarantee outside observed spend ranges."}
