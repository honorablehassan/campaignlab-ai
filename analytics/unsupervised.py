from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def segment_kmeans(df: pd.DataFrame, features: list[str], k: int=0, random_state:int=42) -> dict[str,Any]:
    if len(features)<2: raise ValueError("Segmentation needs at least two numeric features.")
    miss=[c for c in features if c not in df]
    if miss: raise ValueError(f"Columns not found: {miss}")
    X=df[features].apply(pd.to_numeric,errors="coerce").dropna()
    if len(X)<50: raise ValueError("CampaignLab requires at least 50 complete rows for K-means segmentation.")
    if X.nunique().min()<=1: raise ValueError("Every segmentation feature must vary.")
    scaler=StandardScaler(); Z=scaler.fit_transform(X)
    if k==0:
        candidates=range(2,min(8,max(3,len(X)//15))+1); scored=[]
        for kk in candidates:
            labels=KMeans(n_clusters=kk,n_init=20,random_state=random_state).fit_predict(Z)
            scored.append((float(silhouette_score(Z,labels)),kk))
        _,k=max(scored)
    if not 2<=k<=10: raise ValueError("k must be 0 (auto) or between 2 and 10.")
    model=KMeans(n_clusters=k,n_init=30,random_state=random_state).fit(Z); labels=model.labels_; sil=float(silhouette_score(Z,labels))
    prof=X.assign(__cluster=labels).groupby('__cluster').agg(['mean','median','count'])
    clusters=[]
    for cid in range(k):
        idx=np.where(labels==cid)[0]; row={"cluster":int(cid),"n":int(len(idx)),"share":float(len(idx)/len(X)),"feature_means":{f:float(X.iloc[idx][f].mean()) for f in features},"feature_medians":{f:float(X.iloc[idx][f].median()) for f in features}}
        clusters.append(row)
    return {"method":"kmeans_segmentation","n":int(len(X)),"features":features,"k":int(k),"silhouette":sil,"clusters":clusters,"warning":"Clusters are descriptive patterns, not natural truths. Stability and business usefulness matter more than a clever label."}


def detect_anomalies(df: pd.DataFrame, features: list[str], contamination: float=.03, random_state:int=42) -> dict[str,Any]:
    if not features: raise ValueError("Choose at least one numeric feature.")
    if not .001<=contamination<=.20: raise ValueError("contamination must be between 0.001 and 0.20.")
    miss=[c for c in features if c not in df]
    if miss: raise ValueError(f"Columns not found: {miss}")
    X=df[features].apply(pd.to_numeric,errors="coerce").dropna()
    if len(X)<50: raise ValueError("CampaignLab requires at least 50 complete rows for anomaly detection.")
    Z=StandardScaler().fit_transform(X)
    model=IsolationForest(n_estimators=250,contamination=contamination,random_state=random_state,n_jobs=-1).fit(Z)
    score=-model.score_samples(Z); flag=model.predict(Z)==-1
    order=np.argsort(score)[::-1][:min(25,len(X))]
    top=[]
    for pos in order:
        idx=X.index[pos]
        top.append({"row_index":str(idx),"anomaly_score":float(score[pos]),"flagged":bool(flag[pos]),"values":{f:float(X.iloc[pos][f]) for f in features}})
    return {"method":"isolation_forest_anomaly_detection","n":int(len(X)),"features":features,"flagged_count":int(flag.sum()),"flagged_share":float(flag.mean()),"top_anomalies":top,"warning":"Anomaly means unusual in feature space, not erroneous or fraudulent. Investigate before deleting or acting."}
