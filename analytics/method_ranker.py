from __future__ import annotations
from typing import Any
from analytics.dataset_intelligence import DatasetIntelligence
from analytics.method_registry import METHODS
from analytics.data_gate import prediction_readiness


def _status_weight(s): return {"Live":18,"Beta":8,"Planned":-8,"Research":-16}.get(s,-10)


def rank_methods(intel: DatasetIntelligence, question: str="") -> list[dict[str,Any]]:
    roles=intel.role_map; rows=intel.rows; q=(question or "").lower(); qtype=intel.question_assessment.get("question_type","unspecified")
    opportunity={x["id"]:x["score"] for x in intel.analytical_opportunities}
    numeric=sum(1 for s in intel.column_signals if s["semantic_type"] in ("numeric","binary_numeric"))
    categorical=sum(1 for s in intel.column_signals if s["semantic_type"] in ("categorical","boolean","binary_numeric"))
    out=[]
    for m in METHODS:
        mid=m["id"]; score=18+_status_weight(m["status"]); reasons=[]; blockers=[]; evaluated=True
        if mid in opportunity: score += opportunity[mid]*.45; reasons.append("Dataset structure directly matches this analytical family.")
        has=lambda r: bool(roles.get(r))
        if mid=="binary_ab":
            ok=has("treatment") and has("binary_outcome"); reasons += ["Treatment/variant + binary outcome detected."] if ok else []; blockers += [] if ok else ["Needs treatment/variant + binary outcome."]
        elif mid=="continuous_ab":
            ok=has("treatment") and (has("continuous_outcome") or has("revenue")); reasons += ["Treatment + continuous outcome detected."] if ok else []; blockers += [] if ok else ["Needs treatment + continuous numeric outcome."]
        elif mid=="abn":
            ok=has("treatment") and (has("binary_outcome") or has("continuous_outcome") or has("revenue")); blockers += [] if ok else ["Needs 3+ treatment arms + outcome; arm count is verified at execution."]
        elif mid=="bootstrap_difference":
            ok=has("treatment") and numeric>=1; blockers += [] if ok else ["Needs a grouping/treatment field + numeric outcome."]
        elif mid=="linear_regression":
            ok=rows>=50 and numeric>=2; blockers += [] if ok else ["Needs enough labeled history for a holdout, a numeric target, and predictor variation."]
            if ok: reasons.append("Dataset is large enough for a conservative predictive holdout; final readiness also depends on the chosen target and predictors.")
        elif mid=="logistic_regression":
            ok=rows>=50 and has("binary_outcome") and (numeric+categorical)>=2; blockers += [] if ok else ["Needs a binary target, predictors, class support, and enough rows for validation."]
        elif mid=="tree_model":
            ok=rows>=100 and (numeric+categorical)>=2; blockers += [] if ok else ["Needs a defined target, predictors, and enough labeled history for a real holdout."]
        elif mid=="kmeans_segmentation":
            ok=rows>=50 and numeric>=2; blockers += [] if ok else ["Needs 2+ numeric features and at least 50 rows."]
        elif mid=="anomaly_detection":
            ok=rows>=50 and numeric>=1; blockers += [] if ok else ["Needs numeric features and at least 50 rows."]
        elif mid=="marketing_efficiency":
            ok=has("spend") and (has("revenue") or has("conversions")) and (has("channel") or has("campaign") or has("segment")); blockers += [] if ok else ["Needs group/channel + spend + revenue or conversions."]
        elif mid=="funnel":
            ok=(has("impressions") and has("clicks") and has("conversions")); blockers += [] if ok else ["Needs two or more ordered funnel-stage measures; auto-detection currently recognizes media funnel fields."]
        elif mid=="cohort_retention":
            ok=(has("customer") or has("id")) and has("date") and rows>=20; blockers += [] if ok else ["Needs customer identifier + event date with repeated observations."]
        elif mid=="did":
            ok=has("treatment") and has("post") and (has("continuous_outcome") or has("revenue") or has("conversions")); blockers += [] if ok else ["Needs treatment, post indicator, and numeric outcome."]
        elif mid=="event_study":
            ok=has("treatment") and has("relative_time") and has("date") and (has("unit") or has("id")) and rows>=80; blockers += [] if ok else ["Needs treatment, relative event time, unit, calendar time, outcome, and 80+ rows."]
        elif mid=="interrupted_time_series":
            ok=has("date") and numeric>=1 and rows>=20; blockers += [] if ok else ["Needs 20+ time points, a numeric outcome, and intervention date supplied by user."]
        elif mid=="mmm_beta":
            evaluated=False; ok=False; blockers.append("Run MMM through its dedicated Lab Special workspace, where CampaignLab can collect the consequential time/outcome/media mappings and apply the MMM-specific readiness gate.")
        else:
            evaluated=False; ok=False; blockers.append("This method is documented but not exposed as a validated Live executor.")
        if qtype=="causal": score += 12 if m["family"] in ("Causal inference","Experimentation") else -7
        if qtype=="predictive": score += 12 if m["family"]=="Predictive & statistical" else 0
        if any(w in q for w in ["roas","budget","cac","channel","cpa"]): score += 16 if mid=="marketing_efficiency" else 0
        if any(w in q for w in ["predict","propensity","forecast"]): score += 10 if mid in ("logistic_regression","linear_regression","tree_model") else 0
        if any(w in q for w in ["before","after","rollout","policy"]): score += 10 if mid in ("did","event_study","interrupted_time_series") else 0
        eligible=evaluated and not blockers
        executable=eligible and m["status"]=="Live"
        score=max(0,min(100,round(score)))
        out.append({"method_id":mid,"name":m["name"],"family":m["family"],"implementation_status":m["status"],"score":score,"eligible":eligible,"executable_now":executable,"reasons":reasons[:3],"blockers":blockers[:3],"answers":m["answers"],"requires":m["requires"]})
    out.sort(key=lambda x:(x["executable_now"],x["eligible"],x["score"]),reverse=True)
    return out[:12]
