from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats


def run_difference_in_differences(df: pd.DataFrame, outcome: str, treatment_col: str, post_col: str, covariates: list[str]|None=None, unit_col: str|None=None) -> dict[str,Any]:
    covariates=covariates or []
    cols=[outcome,treatment_col,post_col,*covariates]+([unit_col] if unit_col else [])
    miss=[c for c in cols if c not in df];
    if miss: raise ValueError(f"Columns not found: {miss}")
    d=df[cols].dropna().copy(); d[outcome]=pd.to_numeric(d[outcome],errors="coerce"); d=d.dropna(subset=[outcome])
    if len(d)<40: raise ValueError("DiD requires at least 40 usable observations in CampaignLab.")
    if d[treatment_col].nunique()!=2 or d[post_col].nunique()!=2: raise ValueError("Treatment and post indicators must each have exactly two observed values.")
    # robustly convert two-level columns to 0/1
    for c in [treatment_col,post_col]:
        vals=list(d[c].unique()); d[f"__{c}"]=(d[c]==vals[-1]).astype(int)
    rhs=f"__{treatment_col} * __{post_col}" + (" + "+" + ".join([f'Q(\"{c}\")' for c in covariates]) if covariates else "")
    model=smf.ols(f'Q("{outcome}") ~ {rhs}',data=d)
    if unit_col and d[unit_col].nunique()>=2:
        fit=model.fit(cov_type="cluster",cov_kwds={"groups":d[unit_col]}); se_type=f"clustered by {unit_col}"
    else:
        fit=model.fit(cov_type="HC3"); se_type="HC3 robust"
    term=f"__{treatment_col}:__{post_col}"; ci=fit.conf_int().loc[term]
    cell=d.groupby([f"__{treatment_col}",f"__{post_col}"])[outcome].agg(["mean","count"]).reset_index().to_dict("records")
    return {"method":"difference_in_differences","n":int(len(d)),"effect":float(fit.params[term]),"std_error":float(fit.bse[term]),"p_value":float(fit.pvalues[term]),"ci_low":float(ci.iloc[0]),"ci_high":float(ci.iloc[1]),"se_type":se_type,"cell_summary":cell,"r2":float(fit.rsquared),"assumption_warning":"A DiD coefficient is causal only if parallel trends and no treatment-timing/confounding violations are credible. Inspect pre-trends before acting."}


def run_event_study(df: pd.DataFrame, outcome: str, treatment_col: str, relative_time_col: str, unit_col: str, calendar_time_col: str, reference_period: int=-1, covariates: list[str]|None=None) -> dict[str,Any]:
    covariates=covariates or []
    cols=[outcome,treatment_col,relative_time_col,unit_col,calendar_time_col,*covariates]
    miss=[c for c in cols if c not in df]
    if miss: raise ValueError(f"Columns not found: {miss}")
    d=df[cols].dropna().copy(); d[outcome]=pd.to_numeric(d[outcome],errors="coerce"); d[relative_time_col]=pd.to_numeric(d[relative_time_col],errors="coerce"); d=d.dropna()
    if len(d)<80 or d[unit_col].nunique()<4: raise ValueError("Event study needs at least 80 rows and 4 units in CampaignLab.")
    vals=list(d[treatment_col].unique())
    if len(vals)!=2: raise ValueError("Treatment column must have two levels.")
    d["__treated"]=(d[treatment_col]==vals[-1]).astype(int)
    if reference_period not in set(d[relative_time_col].astype(int)): raise ValueError("Reference relative period is absent from data.")
    # Build only treated-by-event-time indicators. Including treated and relative-time
    # main effects here would duplicate the unit and calendar fixed effects, creating
    # a rank-deficient design whose clustered covariance can vary across platforms.
    event_times=sorted(float(v) for v in d[relative_time_col].unique() if float(v)!=float(reference_period))
    event_terms=[]
    for i,event_time in enumerate(event_times):
        term=f"__event_{i}"
        d[term]=((d["__treated"]==1) & np.isclose(d[relative_time_col].astype(float),event_time)).astype(int)
        event_terms.append((term,event_time))
    if not event_terms: raise ValueError("Event study needs at least one non-reference relative period.")
    rhs=" + ".join(term for term,_ in event_terms)
    rhs += f' + C(Q("{unit_col}")) + C(Q("{calendar_time_col}"))'
    if covariates: rhs += " + " + " + ".join([f'Q("{c}")' for c in covariates])
    fit=smf.ols(f'Q("{outcome}") ~ {rhs}',data=d).fit(cov_type="cluster",cov_kwds={"groups":d[unit_col]})
    effects=[]
    cov=fit.cov_params()
    critical=float(stats.norm.ppf(.975))
    for name,rel_time in event_terms:
        val=float(fit.params[name])
        variance=float(cov.loc[name,name])
        if not np.isfinite(variance) or variance < -1e-12:
            raise ValueError("Event-study clustered uncertainty is numerically unstable for a treatment-time effect. Increase independent units/clusters or simplify the specification before interpreting it.")
        se=float(np.sqrt(max(variance,0.0)))
        if se>0:
            z=val/se
            p_value=float(2*stats.norm.sf(abs(z)))
            ci_low=float(val-critical*se); ci_high=float(val+critical*se)
        else:
            p_value=1.0 if abs(val)<1e-12 else 0.0
            ci_low=ci_high=val
        effects.append({"relative_time":rel_time,"effect":val,"std_error":se,"p_value":p_value,"ci_low":ci_low,"ci_high":ci_high})
    effects.sort(key=lambda x:x["relative_time"])
    pre=[e for e in effects if e["relative_time"]<reference_period]
    return {"method":"event_study","n":int(len(d)),"units":int(d[unit_col].nunique()),"reference_period":reference_period,"effects":effects,"pre_period_effects":pre,"assumption_warning":"Event-study coefficients are causal only under credible identification assumptions. Pre-period estimates are a diagnostic, not proof of parallel trends."}


def run_interrupted_time_series(df: pd.DataFrame, outcome: str, time_col: str, intervention_date: str) -> dict[str,Any]:
    if outcome not in df or time_col not in df: raise ValueError("Outcome/time columns must exist.")
    d=df[[outcome,time_col]].copy(); d[time_col]=pd.to_datetime(d[time_col],errors="coerce"); d[outcome]=pd.to_numeric(d[outcome],errors="coerce"); d=d.dropna().sort_values(time_col)
    # aggregate duplicate timestamps
    d=d.groupby(time_col,as_index=False)[outcome].mean()
    if len(d)<20: raise ValueError("Interrupted time series needs at least 20 time points.")
    intervention=pd.Timestamp(intervention_date)
    d["t"]=np.arange(len(d)); d["post"]=(d[time_col]>=intervention).astype(int)
    if d["post"].sum()<5 or (1-d["post"]).sum()<5: raise ValueError("Need at least five pre and five post time points.")
    first_post=int(np.argmax(d["post"].values==1)); d["time_after"]=np.where(d["post"]==1,d["t"]-first_post,0)
    fit=smf.ols(f'Q("{outcome}") ~ t + post + time_after',data=d).fit(cov_type="HAC",cov_kwds={"maxlags":min(3,max(1,len(d)//10))})
    return {"method":"interrupted_time_series","n_periods":int(len(d)),"level_change":float(fit.params["post"]),"level_change_p":float(fit.pvalues["post"]),"slope_change":float(fit.params["time_after"]),"slope_change_p":float(fit.pvalues["time_after"]),"baseline_slope":float(fit.params["t"]),"r2":float(fit.rsquared),"warning":"ITS can be biased by concurrent events, seasonality, anticipation, or misspecified trends. A comparison series strengthens causal interpretation."}
