"""CUPED precision adjustment for randomized two-arm experiments."""
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from analytics.ab_continuous import analyze_continuous_ab

def analyze_cuped(df: pd.DataFrame, group_col: str, outcome_col: str, covariate_col: str, control_group: str, treatment_group: str, *, alpha: float=.05, business_threshold: float=0.0) -> dict[str, Any]:
    missing=[c for c in [group_col,outcome_col,covariate_col] if c not in df]
    if missing: raise ValueError(f"Columns not found: {missing}")
    if outcome_col==covariate_col: raise ValueError("Outcome and pre-treatment covariate must be different columns.")
    d=df.loc[df[group_col].astype(str).isin([str(control_group),str(treatment_group)]),[group_col,outcome_col,covariate_col]].copy()
    d[outcome_col]=pd.to_numeric(d[outcome_col],errors="coerce"); d[covariate_col]=pd.to_numeric(d[covariate_col],errors="coerce")
    d=d.replace([np.inf,-np.inf],np.nan).dropna(); d[group_col]=d[group_col].astype(str)
    c=d[d[group_col]==str(control_group)]; t=d[d[group_col]==str(treatment_group)]
    if min(len(c),len(t))<20: raise ValueError("CUPED requires at least 20 complete observations in each arm.")
    x=d[covariate_col].to_numpy(float); y=d[outcome_col].to_numpy(float); variance=float(np.var(x,ddof=1))
    if variance<=1e-12: raise ValueError("The pre-treatment covariate has no usable variation.")
    theta=float(np.cov(y,x,ddof=1)[0,1]/variance)
    d["__cuped__"]=d[outcome_col]-theta*(d[covariate_col]-float(x.mean()))
    raw=analyze_continuous_ab(c[outcome_col],t[outcome_col],alpha=alpha,business_threshold=business_threshold)
    adjusted=analyze_continuous_ab(d.loc[d[group_col]==str(control_group),"__cuped__"],d.loc[d[group_col]==str(treatment_group),"__cuped__"],alpha=alpha,business_threshold=business_threshold)
    raw_var=float(np.var(y,ddof=1)); adjusted_var=float(np.var(d["__cuped__"],ddof=1)); reduction=max(-1.0,min(1.0,1-adjusted_var/max(raw_var,1e-12)))
    pooled_sd=float(np.sqrt(((len(c)-1)*c[covariate_col].var(ddof=1)+(len(t)-1)*t[covariate_col].var(ddof=1))/max(1,len(c)+len(t)-2)))
    balance=float((t[covariate_col].mean()-c[covariate_col].mean())/pooled_sd) if pooled_sd>0 else 0.0
    warnings=["Valid only when the covariate was measured before treatment and could not be affected by treatment."]
    if abs(balance)>.1: warnings.append("The pre-treatment covariate is imbalanced across arms (|standardized difference| > 0.10); inspect randomization before acting.")
    if reduction<=0: warnings.append("CUPED did not reduce variance; prefer the pre-specified primary analysis.")
    return {"method":"cuped","control":str(control_group),"treatment":str(treatment_group),"outcome":outcome_col,"pre_treatment_covariate":covariate_col,"n":int(len(d)),"theta":theta,"raw_effect":raw.absolute_lift,"raw_ci_low":raw.ci_low,"raw_ci_high":raw.ci_high,"raw_p_value":raw.p_value,"adjusted_effect":adjusted.absolute_lift,"adjusted_ci_low":adjusted.ci_low,"adjusted_ci_high":adjusted.ci_high,"adjusted_p_value":adjusted.p_value,"variance_reduction":reduction,"covariate_balance_smd":balance,"decision":adjusted.decision,"practical_significance":adjusted.practical_significance,"warnings":warnings}
