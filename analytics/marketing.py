from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd


def analyze_marketing_efficiency(df: pd.DataFrame, group_col: str, spend_col: str, revenue_col: str|None=None, conversions_col: str|None=None, clicks_col: str|None=None, impressions_col: str|None=None) -> dict[str,Any]:
    required=[group_col,spend_col]+[c for c in [revenue_col,conversions_col,clicks_col,impressions_col] if c]
    miss=[c for c in required if c not in df]
    if miss: raise ValueError(f"Columns not found: {miss}")
    if not revenue_col and not conversions_col: raise ValueError("Provide revenue or conversions to measure efficiency.")
    d=df[required].copy()
    for c in required[1:]: d[c]=pd.to_numeric(d[c],errors="coerce")
    agg=d.groupby(group_col,dropna=False)[required[1:]].sum(min_count=1).reset_index()
    agg=agg[agg[spend_col].notna()]
    rows=[]
    total_spend=float(agg[spend_col].sum())
    for _,r in agg.iterrows():
        spend=float(r[spend_col] or 0); out={"group":str(r[group_col]),"spend":spend,"spend_share":spend/total_spend if total_spend else None}
        if revenue_col:
            rev=float(r[revenue_col] or 0); out.update({"revenue":rev,"roas":rev/spend if spend>0 else None})
        if conversions_col:
            conv=float(r[conversions_col] or 0); out.update({"conversions":conv,"cpa":spend/conv if conv>0 else None})
        if clicks_col:
            clicks=float(r[clicks_col] or 0); out["clicks"]=clicks; out["cpc"]=spend/clicks if clicks>0 else None
        if impressions_col:
            imp=float(r[impressions_col] or 0); out["impressions"]=imp; out["cpm"]=spend/imp*1000 if imp>0 else None
            if clicks_col: out["ctr"]=clicks/imp if imp>0 else None
        if conversions_col and clicks_col: out["cvr"]=conv/clicks if clicks>0 else None
        rows.append(out)
    key="roas" if revenue_col else "cpa"
    rows=sorted(rows,key=lambda x:(x.get(key) is not None,x.get(key,0)),reverse=(key=="roas"))
    return {"method":"marketing_efficiency","group_by":group_col,"rows":rows[:50],"totals":{"spend":total_spend,"groups":len(rows)},"warning":"Observed efficiency is not incrementality. High ROAS can reflect selection, attribution, or demand that would have happened anyway."}


def analyze_funnel(df: pd.DataFrame, stage_columns: list[str]) -> dict[str,Any]:
    if len(stage_columns)<2: raise ValueError("A funnel needs at least two ordered stages.")
    miss=[c for c in stage_columns if c not in df]
    if miss: raise ValueError(f"Columns not found: {miss}")
    counts=[]
    for c in stage_columns:
        s=df[c]
        if pd.api.types.is_numeric_dtype(s): count=float(pd.to_numeric(s,errors="coerce").fillna(0).sum())
        else: count=float(s.notna().sum())
        counts.append(count)
    rows=[]
    for i,(c,n) in enumerate(zip(stage_columns,counts)):
        prev=counts[i-1] if i else None
        rows.append({"stage":c,"count":n,"step_conversion":(n/prev if prev and prev>0 else None),"from_start":(n/counts[0] if counts[0]>0 else None),"dropoff_from_previous":(1-n/prev if prev and prev>0 else None)})
    return {"method":"funnel_analysis","stages":rows}
