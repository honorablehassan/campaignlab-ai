from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss, r2_score, mean_absolute_error, mean_squared_error


def fit_tree_model(df: pd.DataFrame, target: str, predictors: list[str], task: str="auto", algorithm: str="random_forest", random_state:int=42) -> dict[str,Any]:
    missing=[c for c in [target,*predictors] if c not in df]
    if missing: raise ValueError(f"Columns not found: {missing}")
    if not predictors: raise ValueError("Select predictors.")
    d=df[[target,*predictors]].copy().dropna(subset=[target])
    if len(d)<100: raise ValueError("CampaignLab requires at least 100 rows for tree-model evaluation.")
    if task=="auto": task="classification" if d[target].nunique()<=10 and not pd.api.types.is_float_dtype(d[target]) else "regression"
    X=d[predictors]; y=d[target]
    numeric=X.select_dtypes(include=[np.number]).columns.tolist(); categorical=[c for c in predictors if c not in numeric]
    pre=ColumnTransformer([
        ("num",Pipeline([("impute",SimpleImputer(strategy="median"))]),numeric),
        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore",sparse_output=False))]),categorical),
    ],remainder="drop",verbose_feature_names_out=False)
    stratify=y if task=="classification" and y.value_counts().min()>=2 else None
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.25,random_state=random_state,stratify=stratify)
    if task=="classification":
        model=RandomForestClassifier(n_estimators=250,min_samples_leaf=3,class_weight="balanced",random_state=random_state,n_jobs=-1) if algorithm=="random_forest" else GradientBoostingClassifier(random_state=random_state)
    else:
        model=RandomForestRegressor(n_estimators=250,min_samples_leaf=3,random_state=random_state,n_jobs=-1) if algorithm=="random_forest" else GradientBoostingRegressor(random_state=random_state)
    pipe=Pipeline([("pre",pre),("model",model)]); pipe.fit(Xtr,ytr)
    pred=pipe.predict(Xte)
    metrics={}
    if task=="classification":
        metrics["accuracy_holdout"]=float(accuracy_score(yte,pred))
        if len(pd.Series(y).unique())==2 and hasattr(pipe,"predict_proba"):
            prob=pipe.predict_proba(Xte)[:,1]
            # Convert holdout labels to model class 1 indicator for robust non-numeric class handling.
            positive=pipe.named_steps["model"].classes_[1]
            ybin=(pd.Series(yte).reset_index(drop=True)==positive).astype(int)
            metrics["auc_holdout"]=float(roc_auc_score(ybin,prob)); metrics["brier_holdout"]=float(brier_score_loss(ybin,prob))
    else:
        metrics={"r2_holdout":float(r2_score(yte,pred)),"rmse_holdout":float(mean_squared_error(yte,pred)**0.5),"mae_holdout":float(mean_absolute_error(yte,pred))}
    try:
        names=pipe.named_steps["pre"].get_feature_names_out(); imp=pipe.named_steps["model"].feature_importances_
        top=sorted(({"feature":str(n),"importance":float(v)} for n,v in zip(names,imp)),key=lambda r:r["importance"],reverse=True)[:15]
    except Exception: top=[]
    return {"method":f"{algorithm}_{task}","task":task,"algorithm":algorithm,"n_train":int(len(Xtr)),"n_holdout":int(len(Xte)),"target":target,"predictors":predictors,"metrics":metrics,"feature_importance":top,"warning":"Feature importance is predictive, not causal. Holdout metrics are more trustworthy than training fit but still require monitoring and external validation."}
