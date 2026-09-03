from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any
import time
import pandas as pd

from analytics.ab_binary import analyze_binary_ab, required_sample_size_per_group
from analytics.ab_continuous import analyze_continuous_ab
from analytics.abn import analyze_abn
from analytics.bootstrap import bootstrap_group_difference
from analytics.causal import run_difference_in_differences, run_event_study, run_interrupted_time_series
from analytics.cohorts import analyze_cohort_retention
from analytics.data_profile import profile_dataframe
from analytics.dataset_intelligence import analyze_dataset_intelligence
from analytics.marketing import analyze_marketing_efficiency, analyze_funnel
from analytics.method_ranker import rank_methods
from analytics.method_registry import METHODS
from analytics.regression import fit_linear_regression, fit_logistic_regression
from analytics.tree_models import fit_tree_model
from analytics.unsupervised import segment_kmeans, detect_anomalies
from visualization.decision_visualization import recommend_visualizations
from core.observability import record_event
from core.errors import CampaignLabToolError


def _jsonable(value: Any) -> Any:
    if is_dataclass(value): return asdict(value)
    if isinstance(value, dict): return {str(k): _jsonable(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_jsonable(v) for v in value]
    if hasattr(value,"item"):
        try: return value.item()
        except Exception: pass
    return value


def _obj(properties: dict, required: list[str]):
    return {"type":"object","properties":properties,"required":required,"additionalProperties":False}


class EvidenceToolRuntime:
    """Whitelisted deterministic analytical runtime. Raw DataFrames never enter LLM tool arguments."""
    def __init__(self, dataframe: pd.DataFrame|None=None, role_overrides: dict[str, str | None] | None=None):
        self.dataframe=dataframe
        self.role_overrides=dict(role_overrides or {})
        self._intel_cache={}
    def _df(self):
        if self.dataframe is None: raise ValueError("No dataset is loaded for this tool call.")
        return self.dataframe
    def _intel(self, question=""):
        k=question.strip()
        if k not in self._intel_cache:
            self._intel_cache[k]=analyze_dataset_intelligence(self._df(),question,role_overrides=self.role_overrides)
        return self._intel_cache[k]

    def _enforce_resolved_role(self, role: str, column: str | None) -> None:
        if role not in self.role_overrides:
            return
        resolved = self.role_overrides[role]
        if resolved is None:
            if column:
                raise ValueError(f"{role} is still unresolved; CampaignLab will not choose {column!r} behind the user's back.")
            return
        if column and column != resolved:
            raise ValueError(f"{role} was resolved to {resolved!r}; tool call attempted {column!r} instead.")

    def tool_specs(self):
        specs=[
            {"type":"function","name":"list_supported_methods","description":"List CampaignLab analytical methods, status, requirements and guardrails. Live means executable.","parameters":_obj({},[]),"strict":True},
            {"type":"function","name":"plan_binary_ab","description":"Calculate equal-allocation binary A/B sample size.","parameters":_obj({"baseline_rate":{"type":"number","minimum":.0001,"maximum":.9999},"absolute_mde":{"type":"number","minimum":.0001,"maximum":.99},"power":{"type":"number","enum":[.8,.9,.95]},"alpha":{"type":"number","enum":[.05]}},["baseline_rate","absolute_mde","power","alpha"]),"strict":True},
            {"type":"function","name":"analyze_binary_ab","description":"Analyze summary-count binary A/B experiment deterministically.","parameters":_obj({"control_n":{"type":"integer","minimum":1},"control_conversions":{"type":"integer","minimum":0},"treatment_n":{"type":"integer","minimum":1},"treatment_conversions":{"type":"integer","minimum":0},"expected_treatment_share":{"type":"number","minimum":.01,"maximum":.99},"business_threshold":{"type":"number","minimum":0,"maximum":.99}},["control_n","control_conversions","treatment_n","treatment_conversions","expected_treatment_share","business_threshold"]),"strict":True},
        ]
        if self.dataframe is not None:
            col={"type":"string"}; cols={"type":"array","items":{"type":"string"},"maxItems":30}
            specs += [
                {"type":"function","name":"profile_dataset","description":"Return compact deterministic dataframe profile without raw rows.","parameters":_obj({},[]),"strict":True},
                {"type":"function","name":"inspect_dataset_intelligence","description":"Profile uploaded data, infer semantic roles/grain, quality risks, answerability and analytical opportunities. Call first.","parameters":_obj({"question":{"type":"string"}},["question"]),"strict":True},
                {"type":"function","name":"rank_candidate_methods","description":"Rank methods against the uploaded dataset and question, showing eligibility and execution status.","parameters":_obj({"question":{"type":"string"}},["question"]),"strict":True},
                {"type":"function","name":"recommend_decision_visualizations","description":"Recommend the smallest useful chart set for this dataset/question.","parameters":_obj({"question":{"type":"string"}},["question"]),"strict":True},
                {"type":"function","name":"analyze_continuous_ab_dataset","description":"Execute Welch continuous A/B analysis on two groups in the uploaded dataset.","parameters":_obj({"group_column":col,"outcome_column":col,"control_group":col,"treatment_group":col,"business_threshold":{"type":"number","minimum":0}},["group_column","outcome_column","control_group","treatment_group","business_threshold"]),"strict":True},
                {"type":"function","name":"analyze_abn_dataset","description":"Execute multi-arm A/B/n with omnibus test and Holm-adjusted comparisons vs control.","parameters":_obj({"group_column":col,"outcome_column":col,"outcome_type":{"type":"string","enum":["auto","binary","continuous"]},"control_group":col},["group_column","outcome_column","outcome_type","control_group"]),"strict":True},
                {"type":"function","name":"bootstrap_group_difference","description":"Bootstrap a mean/median difference between two groups.","parameters":_obj({"group_column":col,"outcome_column":col,"control_group":col,"treatment_group":col,"statistic":{"type":"string","enum":["mean","median"]}},["group_column","outcome_column","control_group","treatment_group","statistic"]),"strict":True},
                {"type":"function","name":"fit_linear_regression","description":"Fit deterministic OLS with HC3 robust SE and regression diagnostics for a continuous target.","parameters":_obj({"target":col,"predictors":cols},["target","predictors"]),"strict":True},
                {"type":"function","name":"fit_logistic_regression","description":"Fit deterministic logistic regression with odds ratios and diagnostics for a binary target.","parameters":_obj({"target":col,"predictors":cols},["target","predictors"]),"strict":True},
                {"type":"function","name":"fit_tree_model","description":"Fit a holdout-evaluated random forest or gradient boosting model. Predictive only, not causal.","parameters":_obj({"target":col,"predictors":cols,"task":{"type":"string","enum":["auto","classification","regression"]},"algorithm":{"type":"string","enum":["random_forest","gradient_boosting"]}},["target","predictors","task","algorithm"]),"strict":True},
                {"type":"function","name":"analyze_marketing_efficiency","description":"Calculate observed channel/campaign ROAS, CPA/CAC-style efficiency and optional funnel media metrics.","parameters":_obj({"group_column":col,"spend_column":col,"revenue_column":col,"conversions_column":col,"clicks_column":col,"impressions_column":col},["group_column","spend_column","revenue_column","conversions_column","clicks_column","impressions_column"]),"strict":True},
                {"type":"function","name":"analyze_funnel","description":"Calculate ordered funnel stage conversion/drop-off metrics.","parameters":_obj({"stage_columns":{"type":"array","items":{"type":"string"},"minItems":2,"maxItems":12}},["stage_columns"]),"strict":True},
                {"type":"function","name":"analyze_cohort_retention","description":"Build cohort-age retention from repeated customer IDs and event dates.","parameters":_obj({"customer_column":col,"date_column":col,"frequency":{"type":"string","enum":["D","W","M","Q"]}},["customer_column","date_column","frequency"]),"strict":True},
                {"type":"function","name":"run_difference_in_differences","description":"Execute a 2x2 Difference-in-Differences model with robust or clustered standard errors.","parameters":_obj({"outcome":col,"treatment_column":col,"post_column":col,"covariates":cols,"unit_column":col},["outcome","treatment_column","post_column","covariates","unit_column"]),"strict":True},
                {"type":"function","name":"run_event_study","description":"Execute panel event study with unit/time fixed effects and unit-clustered standard errors.","parameters":_obj({"outcome":col,"treatment_column":col,"relative_time_column":col,"unit_column":col,"calendar_time_column":col,"reference_period":{"type":"integer"},"covariates":cols},["outcome","treatment_column","relative_time_column","unit_column","calendar_time_column","reference_period","covariates"]),"strict":True},
                {"type":"function","name":"segment_kmeans","description":"Run standardized K-means segmentation with automatic silhouette-based k selection when k=0.","parameters":_obj({"features":cols,"k":{"type":"integer","minimum":0,"maximum":10}},["features","k"]),"strict":True},
                {"type":"function","name":"detect_anomalies","description":"Run Isolation Forest anomaly detection over chosen numeric features.","parameters":_obj({"features":cols,"contamination":{"type":"number","minimum":.001,"maximum":.20}},["features","contamination"]),"strict":True},
                {"type":"function","name":"run_interrupted_time_series","description":"Estimate immediate level and slope changes at a known intervention date using HAC standard errors.","parameters":_obj({"outcome":col,"time_column":col,"intervention_date":{"type":"string"}},["outcome","time_column","intervention_date"]),"strict":True},
            ]
        return specs

    def execute(self,name:str,args:dict):
        started=time.perf_counter()
        try:
            out=self._execute(name,args)
            record_event(kind="tool_call",feature=name,status="ok",duration_ms=(time.perf_counter()-started)*1000)
            return _jsonable(out)
        except Exception as exc:
            eid=record_event(kind="tool_call",feature=name,status="error",duration_ms=(time.perf_counter()-started)*1000,detail=f"{type(exc).__name__}: {exc}")
            raise CampaignLabToolError(f"{name} failed: {exc} [ref {eid}]") from exc

    def _execute(self,name,args):
        if name=="list_supported_methods": return {"methods":METHODS}
        if name=="plan_binary_ab":
            target=args["baseline_rate"]+args["absolute_mde"]
            if target >= 1: raise ValueError("baseline_rate + absolute_mde must be below 1.")
            return {"sample_size_per_group":required_sample_size_per_group(args["baseline_rate"], target, alpha=args["alpha"], power=args["power"]), "baseline_rate":args["baseline_rate"], "target_rate":target, "absolute_mde":args["absolute_mde"]}
        if name=="analyze_binary_ab": return analyze_binary_ab(**args)
        if name=="profile_dataset": return _jsonable(profile_dataframe(self._df()))
        if name=="inspect_dataset_intelligence": return self._intel(args["question"]).to_dict()
        if name=="rank_candidate_methods":
            ranked=rank_methods(self._intel(args["question"]),args["question"])
            return {"ranked_methods":ranked,"methods":ranked}
        if name=="recommend_decision_visualizations": return {"visualizations":recommend_visualizations(self._intel(args["question"]),args["question"])}
        df=self._df()
        if name=="analyze_continuous_ab_dataset":
            g,o=args["group_column"],args["outcome_column"]
            c=pd.to_numeric(df.loc[df[g].astype(str)==args["control_group"],o],errors="coerce").dropna()
            t=pd.to_numeric(df.loc[df[g].astype(str)==args["treatment_group"],o],errors="coerce").dropna()
            return analyze_continuous_ab(c,t,business_threshold=args["business_threshold"])
        if name=="analyze_abn_dataset": return analyze_abn(df,args["group_column"],args["outcome_column"],args["outcome_type"],args["control_group"])
        if name=="bootstrap_group_difference": return bootstrap_group_difference(df,args["group_column"],args["outcome_column"],args["control_group"],args["treatment_group"],args["statistic"])
        if name=="fit_linear_regression": return fit_linear_regression(df,args["target"],args["predictors"])
        if name=="fit_logistic_regression": return fit_logistic_regression(df,args["target"],args["predictors"])
        if name=="fit_tree_model": return fit_tree_model(df,args["target"],args["predictors"],args["task"],args["algorithm"])
        if name=="analyze_marketing_efficiency":
            # Empty strings mean optional column absent. Consequential mappings
            # confirmed in the UI are enforced here as well, so an LLM tool
            # call cannot silently swap gross/net revenue or another resolved field.
            x={k:(v or None) for k,v in args.items()}
            self._enforce_resolved_role("spend", x["spend_column"])
            self._enforce_resolved_role("revenue", x["revenue_column"])
            self._enforce_resolved_role("conversions", x["conversions_column"])
            return analyze_marketing_efficiency(df,x["group_column"],x["spend_column"],x["revenue_column"],x["conversions_column"],x["clicks_column"],x["impressions_column"])
        if name=="analyze_funnel": return analyze_funnel(df,args["stage_columns"])
        if name=="analyze_cohort_retention":
            self._enforce_resolved_role("date", args["date_column"])
            return analyze_cohort_retention(df,args["customer_column"],args["date_column"],args["frequency"])
        if name=="run_difference_in_differences": return run_difference_in_differences(df,args["outcome"],args["treatment_column"],args["post_column"],args["covariates"],args["unit_column"] or None)
        if name=="run_event_study": return run_event_study(df,args["outcome"],args["treatment_column"],args["relative_time_column"],args["unit_column"],args["calendar_time_column"],args["reference_period"],args["covariates"])
        if name=="segment_kmeans": return segment_kmeans(df,args["features"],args["k"])
        if name=="detect_anomalies": return detect_anomalies(df,args["features"],args["contamination"])
        if name=="run_interrupted_time_series":
            self._enforce_resolved_role("date", args["time_column"])
            return run_interrupted_time_series(df,args["outcome"],args["time_column"],args["intervention_date"])
        raise ValueError(f"Unregistered tool: {name}")
