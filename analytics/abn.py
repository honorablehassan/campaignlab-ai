from __future__ import annotations

from typing import Any
import itertools
import numpy as np
import pandas as pd
from scipy import stats


def _holm_adjust(pvals: list[float]) -> list[float]:
    m=len(pvals)
    order=np.argsort(pvals)
    out=np.empty(m,float)
    running=0.0
    for rank, idx in enumerate(order):
        adj=min(1.0,(m-rank)*pvals[idx])
        running=max(running,adj)
        out[idx]=running
    return out.tolist()


def analyze_abn(df: pd.DataFrame, group_col: str, outcome_col: str, outcome_type: str = "auto", control_group: str | None = None, alpha: float = 0.05) -> dict[str, Any]:
    if group_col not in df or outcome_col not in df:
        raise ValueError("Group and outcome columns must exist.")
    d=df[[group_col,outcome_col]].dropna().copy()
    if d[group_col].nunique() < 3:
        raise ValueError("A/B/n requires at least three non-empty arms.")
    if d[group_col].nunique() > 20:
        raise ValueError("CampaignLab caps A/B/n at 20 arms to avoid accidental high-cardinality grouping.")
    if outcome_type == "auto":
        outcome_type = "binary" if d[outcome_col].nunique() == 2 else "continuous"
    groups=list(d[group_col].astype(str).unique())
    d[group_col]=d[group_col].astype(str)
    control = str(control_group) if control_group is not None else groups[0]
    if control not in groups:
        raise ValueError("Selected control group is not present.")
    pair_rows=[]
    pvals=[]
    summaries=[]
    if outcome_type == "binary":
        vals=list(d[outcome_col].unique())
        if len(vals)!=2:
            raise ValueError("Binary A/B/n outcome must have exactly two observed values.")
        positive=1 if set(vals).issubset({0,1,False,True}) else vals[-1]
        d["__y__"]=(d[outcome_col]==positive).astype(int)
        table=pd.crosstab(d[group_col],d["__y__"])
        chi2,p,_,_=stats.chi2_contingency(table)
        for g in groups:
            s=d.loc[d[group_col]==g,"__y__"]
            summaries.append({"arm":g,"n":int(len(s)),"rate":float(s.mean())})
        c=d.loc[d[group_col]==control,"__y__"]
        for g in groups:
            if g==control: continue
            t=d.loc[d[group_col]==g,"__y__"]
            count=np.array([c.sum(),t.sum()]); nobs=np.array([len(c),len(t)])
            pooled=count.sum()/nobs.sum()
            se=np.sqrt(pooled*(1-pooled)*(1/nobs[0]+1/nobs[1]))
            z=(t.mean()-c.mean())/se if se>0 else 0.0
            pv=float(2*stats.norm.sf(abs(z)))
            pvals.append(pv)
            pair_rows.append({"comparison":f"{g} vs {control}","effect":float(t.mean()-c.mean()),"p_value":pv})
        omnibus={"test":"chi_square","statistic":float(chi2),"p_value":float(p)}
    elif outcome_type == "continuous":
        d["__y__"]=pd.to_numeric(d[outcome_col],errors="coerce"); d=d.dropna(subset=["__y__"])
        arrays=[d.loc[d[group_col]==g,"__y__"].values for g in groups]
        if min(map(len,arrays))<2: raise ValueError("Every arm needs at least two numeric observations.")
        f,p=stats.f_oneway(*arrays)
        for g,a in zip(groups,arrays): summaries.append({"arm":g,"n":int(len(a)),"mean":float(np.mean(a)),"sd":float(np.std(a,ddof=1))})
        c=d.loc[d[group_col]==control,"__y__"].values
        for g in groups:
            if g==control: continue
            t=d.loc[d[group_col]==g,"__y__"].values
            res=stats.ttest_ind(t,c,equal_var=False)
            pv=float(res.pvalue); pvals.append(pv)
            pair_rows.append({"comparison":f"{g} vs {control}","effect":float(np.mean(t)-np.mean(c)),"p_value":pv})
        omnibus={"test":"one_way_anova","statistic":float(f),"p_value":float(p)}
    else:
        raise ValueError("outcome_type must be auto, binary, or continuous.")
    adjusted=_holm_adjust(pvals) if pvals else []
    for row,adj in zip(pair_rows,adjusted):
        row["holm_adjusted_p"]=float(adj); row["significant_after_correction"]=bool(adj<alpha)
    return {"method":"abn","outcome_type":outcome_type,"control":control,"arms":summaries,"omnibus":omnibus,"pairwise_vs_control":pair_rows,"multiple_testing":"Holm family-wise error correction","alpha":alpha}
