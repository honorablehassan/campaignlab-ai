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


def _choose_media_transform(spend: np.ndarray, outcome: np.ndarray, baseline_x: np.ndarray) -> tuple[float,float,np.ndarray]:
    # Select a conservative transformation on training data only. This is not causal identification;
    # it is a deterministic response-shape choice used by the beta MMM.
    base_beta=np.linalg.lstsq(baseline_x,outcome,rcond=None)[0]
    residual=outcome-baseline_x@base_beta
    best=None
    for alpha in (0.0,.25,.5,.7,.85):
        ad=geometric_adstock(np.maximum(spend,0),alpha)
        positives=ad[ad>0]
        if not len(positives):
            scale=1.0
            sat=np.zeros_like(ad)
        else:
            scale=float(np.median(positives))
            sat=saturation(ad,scale)
        corr=np.corrcoef(sat,residual)[0,1] if np.std(sat)>0 and np.std(residual)>0 else 0.0
        score=abs(float(corr)) if np.isfinite(corr) else 0.0
        if best is None or score>best[0]: best=(score,alpha,scale,sat)
    return best[1],best[2],best[3]


def fit_mmm(df: pd.DataFrame, date_col: str, outcome_col: str, media_cols: list[str], control_cols: list[str] | None = None) -> dict[str,Any]:
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
        alpha,scale,sat=_choose_media_transform(d.loc[:split-1,c].to_numpy(float),y[:split],base_x[:split])
        full_sat=saturation(geometric_adstock(d[c].to_numpy(float),alpha),scale)
        transforms[c]={"adstock_alpha":float(alpha),"saturation_scale":float(scale)}
        media_x.append(full_sat)
    mx=np.column_stack(media_x)
    X=np.column_stack([base_x,mx])
    media_start=base_x.shape[1]
    lower=np.full(X.shape[1],-np.inf); lower[media_start:]=0.0
    upper=np.full(X.shape[1],np.inf)
    best=None
    for lam in (.01,.1,1.0,10.0,100.0):
        Xtr=X[:split]; ytr=y[:split]
        reg=np.sqrt(lam)*np.eye(X.shape[1]); reg[0,0]=0
        Xaug=np.vstack([Xtr,reg]); yaug=np.concatenate([ytr,np.zeros(X.shape[1])])
        fit=lsq_linear(Xaug,yaug,bounds=(lower,upper),lsmr_tol="auto")
        pred=X[split:]@fit.x
        mae=mean_absolute_error(y[split:],pred)
        if best is None or mae<best[0]: best=(mae,lam,fit.x)
    holdout_mae,lam,beta=best
    pred=X@beta
    r2=float(r2_score(y,pred)); holdout_pred=pred[split:]; holdout_y=y[split:]
    holdout_wape=float(np.abs(holdout_y-holdout_pred).sum()/max(np.abs(holdout_y).sum(),1e-9))
    # Devil's-advocate benchmark: media must improve unseen-period prediction over baseline + controls.
    base_fit=np.linalg.lstsq(base_x[:split],y[:split],rcond=None)[0]
    base_holdout_pred=base_x[split:]@base_fit
    baseline_holdout_wape=float(np.abs(holdout_y-base_holdout_pred).sum()/max(np.abs(holdout_y).sum(),1e-9))
    media_holdout_improvement=float((baseline_holdout_wape-holdout_wape)/max(baseline_holdout_wape,1e-9))
    contributions={}
    for j,c in enumerate(media_cols):
        contrib=mx[:,j]*beta[media_start+j]
        contributions[c]={"total":float(contrib.sum()),"mean_period":float(contrib.mean()),"share_of_modeled_media":0.0,"coefficient":float(beta[media_start+j]),**transforms[c]}
    total_media=sum(v["total"] for v in contributions.values())
    for v in contributions.values(): v["share_of_modeled_media"]=float(v["total"]/total_media) if total_media>0 else 0.0
    baseline=pred-sum(mx[:,j]*beta[media_start+j] for j in range(len(media_cols)))
    # evidence strength is intentionally conservative and diagnostic, not a causal probability.
    corr_penalty=max([abs(v) for _,_,v in ready.high_correlations],default=0)
    if media_holdout_improvement < .02:
        strength="Limited"
    elif holdout_wape<=.12 and ready.report.score>=80 and corr_penalty<.8 and media_holdout_improvement>=.05:
        strength="Moderate"
    elif holdout_wape<=.20 and ready.report.score>=65:
        strength="Limited-to-moderate"
    else: strength="Limited"
    return {
        "method":"marketing_mix_model_beta",
        "status":"Beta",
        "readiness":ready.to_dict(),
        "n_observations":n,
        "holdout_periods":n-split,
        "model":{"r2":r2,"holdout_mae":float(holdout_mae),"holdout_wape":holdout_wape,"baseline_holdout_wape":baseline_holdout_wape,"media_holdout_improvement":media_holdout_improvement,"ridge_lambda":float(lam),"evidence_strength":strength},
        "channels":contributions,
        "baseline_total":float(baseline.sum()),
        "actual_total":float(y.sum()),
        "predicted_total":float(pred.sum()),
        "series":pd.DataFrame({date_col:d[date_col],"actual":y,"predicted":pred,"baseline":baseline}).to_dict("records"),
        "warning":"This beta MMM estimates observational contribution under explicit model assumptions. It does not prove causality. Experimental or quasi-experimental calibration should strengthen high-stakes allocation decisions.",
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
            info=channels[c]; alpha=info["adstock_alpha"]; scale=info["saturation_scale"]; beta=info["coefficient"]
            steady=x[i]/max(1-alpha,1e-6)
            val += beta*(1-np.exp(-steady/max(scale,1e-9)))
        return val
    res=minimize(lambda x:-expected_media(x),x0,bounds=[(0,u) for u in upper],constraints={"type":"eq","fun":lambda x:x.sum()-total},method="SLSQP",options={"maxiter":500,"ftol":1e-10})
    x=res.x if res.success else x0
    return {"total_weekly_budget":total,"current":current,"recommended":{c:float(x[i]) for i,c in enumerate(media_cols)},"modeled_media_response_current":float(expected_media(x0)),"modeled_media_response_recommended":float(expected_media(x)),"optimizer_status":"ok" if res.success else "fallback","guardrail":"Optimizer stays near the historical support of each channel; it should not be treated as a causal guarantee outside observed spend ranges."}
