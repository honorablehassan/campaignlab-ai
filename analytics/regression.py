from __future__ import annotations

from typing import Any
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan
from sklearn.metrics import roc_auc_score, brier_score_loss, mean_absolute_error, mean_squared_error, r2_score


def _design(df: pd.DataFrame, target: str, predictors: list[str]):
    missing=[c for c in [target,*predictors] if c not in df.columns]
    if missing: raise ValueError(f"Columns not found: {missing}")
    if not predictors: raise ValueError("Select at least one predictor.")
    d=df[[target,*predictors]].copy().dropna()
    if len(d)<30: raise ValueError("Regression needs at least 30 complete rows in CampaignLab.")
    X=pd.get_dummies(d[predictors],drop_first=True,dtype=float)
    X=X.replace([np.inf,-np.inf],np.nan).dropna(axis=1,how="all")
    # Remove constant predictors before intercept.
    X=X.loc[:, X.nunique(dropna=True)>1]
    if X.shape[1]==0: raise ValueError("No usable predictor variation remains after preprocessing.")
    y=d.loc[X.index,target]
    return d.loc[X.index], y, sm.add_constant(X,has_constant="add")


def fit_linear_regression(df: pd.DataFrame, target: str, predictors: list[str], robust_se: bool=True) -> dict[str,Any]:
    _,y,X=_design(df,target,predictors)
    y=pd.to_numeric(y,errors="coerce"); keep=y.notna(); y=y[keep].astype(float); X=X.loc[keep]
    if len(y)<30: raise ValueError("Continuous target has fewer than 30 usable numeric rows.")
    model=sm.OLS(y,X).fit(cov_type="HC3" if robust_se else "nonrobust")
    pred=model.predict(X)
    ci=model.conf_int()
    rows=[]
    for name in X.columns:
        rows.append({"term":str(name),"coefficient":float(model.params[name]),"std_error":float(model.bse[name]),"p_value":float(model.pvalues[name]),"ci_low":float(ci.loc[name,0]),"ci_high":float(ci.loc[name,1])})
    vif=[]
    if 1 < X.shape[1] <= 25:
        for i,c in enumerate(X.columns):
            if c=="const": continue
            try: v=float(variance_inflation_factor(X.values,i))
            except Exception: v=float("nan")
            vif.append({"term":str(c),"vif":v})
    try:
        bp=het_breuschpagan(model.resid,model.model.exog)
        bp_p=float(bp[1])
    except Exception: bp_p=None
    return {"method":"linear_regression","n":int(len(y)),"target":target,"predictors":predictors,"r2":float(r2_score(y,pred)),"adjusted_r2":float(model.rsquared_adj),"rmse":float(mean_squared_error(y,pred)**0.5),"mae":float(mean_absolute_error(y,pred)),"coefficients":rows,"vif":vif,"breusch_pagan_p":bp_p,"robust_se":"HC3" if robust_se else "classical","warning":"Association is not causation unless the design and adjustment set justify a causal interpretation."}


def fit_logistic_regression(df: pd.DataFrame, target: str, predictors: list[str]) -> dict[str,Any]:
    _,y,X=_design(df,target,predictors)
    vals=list(pd.Series(y).dropna().unique())
    if len(vals)!=2: raise ValueError("Logistic regression target must have exactly two observed classes.")
    positive=1 if set(vals).issubset({0,1,False,True}) else vals[-1]
    yy=(pd.Series(y,index=X.index)==positive).astype(int)
    if yy.sum()<10 or (len(yy)-yy.sum())<10: raise ValueError("CampaignLab requires at least 10 observations in each target class.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model=sm.Logit(yy,X).fit(disp=False,maxiter=200)
    except Exception as exc:
        raise ValueError(f"Logistic model could not converge; possible separation/collinearity: {exc}") from exc
    prob=np.clip(model.predict(X),1e-8,1-1e-8)
    ci=model.conf_int()
    rows=[]
    for name in X.columns:
        coef=float(model.params[name]); lo=float(ci.loc[name,0]); hi=float(ci.loc[name,1])
        rows.append({"term":str(name),"coefficient":coef,"odds_ratio":float(np.exp(coef)),"p_value":float(model.pvalues[name]),"or_ci_low":float(np.exp(lo)),"or_ci_high":float(np.exp(hi))})
    return {"method":"logistic_regression","n":int(len(yy)),"target":target,"positive_class":str(positive),"predictors":predictors,"auc_in_sample":float(roc_auc_score(yy,prob)),"brier_in_sample":float(brier_score_loss(yy,prob)),"pseudo_r2":float(model.prsquared),"coefficients":rows,"warning":"In-sample discrimination is descriptive. Use holdout/CV for predictive claims; coefficients are not causal without identification assumptions."}
