from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd


def bootstrap_group_difference(df: pd.DataFrame, group_col: str, outcome_col: str, control_group: str, treatment_group: str, statistic: str="mean", iterations:int=3000, seed:int=42) -> dict[str,Any]:
    if group_col not in df or outcome_col not in df: raise ValueError("Columns not found.")
    if not 500 <= iterations <= 20000: raise ValueError("iterations must be between 500 and 20,000.")
    d=df[[group_col,outcome_col]].copy(); d[outcome_col]=pd.to_numeric(d[outcome_col],errors="coerce"); d=d.dropna()
    c=d.loc[d[group_col].astype(str)==str(control_group),outcome_col].values; t=d.loc[d[group_col].astype(str)==str(treatment_group),outcome_col].values
    if len(c)<5 or len(t)<5: raise ValueError("Each group needs at least five numeric observations.")
    fn=np.mean if statistic=="mean" else np.median if statistic=="median" else None
    if fn is None: raise ValueError("statistic must be mean or median.")
    rng=np.random.default_rng(seed); diffs=np.empty(iterations)
    for i in range(iterations): diffs[i]=fn(rng.choice(t,len(t),replace=True))-fn(rng.choice(c,len(c),replace=True))
    effect=float(fn(t)-fn(c)); lo,hi=np.quantile(diffs,[.025,.975]); p=float(2*min((diffs<=0).mean(),(diffs>=0).mean()))
    return {"method":"bootstrap_group_difference","statistic":statistic,"control":str(control_group),"treatment":str(treatment_group),"control_n":int(len(c)),"treatment_n":int(len(t)),"effect":effect,"ci_low":float(lo),"ci_high":float(hi),"bootstrap_two_sided_p":min(1.0,p),"iterations":iterations}
