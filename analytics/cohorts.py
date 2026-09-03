from __future__ import annotations
from typing import Any
import pandas as pd


def analyze_cohort_retention(df: pd.DataFrame, customer_col: str, date_col: str, freq: str="M") -> dict[str,Any]:
    if customer_col not in df or date_col not in df: raise ValueError("Customer/date columns must exist.")
    d=df[[customer_col,date_col]].dropna().copy(); d[date_col]=pd.to_datetime(d[date_col],errors="coerce"); d=d.dropna()
    if d.empty: raise ValueError("No usable customer-date rows.")
    period=d[date_col].dt.to_period(freq); first=d.groupby(customer_col)[date_col].transform("min").dt.to_period(freq)
    d["period"]=period; d["cohort"]=first
    # integer elapsed periods using ordinal difference
    d["age"]=d["period"].astype(int)-d["cohort"].astype(int)
    active=d.groupby(["cohort","age"])[customer_col].nunique().unstack(fill_value=0).sort_index()
    base=active.get(0)
    if base is None: raise ValueError("Could not establish cohort size at age zero.")
    retention=active.div(base,axis=0)
    rows=[]
    for cohort,row in retention.iterrows():
        vals={str(int(k)):float(v) for k,v in row.items() if pd.notna(v)}
        rows.append({"cohort":str(cohort),"size":int(base.loc[cohort]),"retention_by_age":vals})
    return {"method":"cohort_retention","frequency":freq,"cohorts":rows[-24:],"note":"Retention means the customer appears at least once in the period; it does not distinguish event types unless the input was pre-filtered."}
