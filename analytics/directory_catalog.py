"""Decision-first information architecture for CampaignLab analytics."""

DECISION_FAMILIES = [
    {
        "id":"experimentation_uplift","title":"Experimentation & Uplift","question":"Did what we changed actually improve the outcome?","description":"Measure average incremental lift from experiments, compare variants, plan detectable effects, and eventually learn where treatment effects differ.",
        "method_ids":["binary_ab","continuous_ab","abn","bootstrap_difference","factorial","cuped","causal_forest"],
    },
    {
        "id":"causal_impact","title":"Causal Impact","question":"Did the intervention actually cause the change?","description":"Use comparison groups, timing and explicit assumptions to estimate counterfactual impact when a clean randomized test is not available.",
        "method_ids":["did","event_study","interrupted_time_series","synthetic_control","dag_adjustment","dml"],
    },
    {
        "id":"prediction","title":"Prediction","question":"What is likely to happen, and what predicts it?","description":"Predict outcomes with explicit data-sufficiency, leakage and holdout checks instead of judging models only on in-sample fit.",
        "method_ids":["linear_regression","logistic_regression","tree_model"],
    },
    {
        "id":"marketing_performance","title":"Marketing Performance","question":"Where is marketing working, leaking, or wasting money?","description":"Diagnose observed efficiency, funnel drop-off, customer retention and channel performance before making stronger causal claims.",
        "method_ids":["marketing_efficiency","funnel","cohort_retention"],
    },
    {
        "id":"segments_patterns","title":"Segments & Patterns","question":"What useful groups or unusual patterns are hiding in the data?","description":"Find descriptive customer structure and anomalies without pretending those patterns are causal truths.",
        "method_ids":["kmeans_segmentation","anomaly_detection"],
    },
]

METHOD_PRESENTATION = {
    "binary_ab":{"human_name":"Conversion Lift Test","technical":"Binary A/B experiment","machinery":["Two-proportion z-test","Fisher's exact check","Wilson confidence intervals","SRM check","Power / MDE context"]},
    "continuous_ab":{"human_name":"Average Value Lift Test","technical":"Continuous-outcome A/B · Welch's t-test","machinery":["Welch's t-test","Confidence interval","Cohen's d","Mann–Whitney robustness check"]},
    "abn":{"human_name":"Multi-Variant Experiment","technical":"A/B/n experiment","machinery":["Chi-square or ANOVA omnibus test","Pairwise z/Welch comparisons","Holm multiple-comparison correction"]},
    "bootstrap_difference":{"human_name":"Flexible Lift Comparison","technical":"Bootstrap group difference","machinery":["Empirical resampling","Percentile confidence interval","Mean or median effect"]},
    "linear_regression":{"human_name":"Driver Model","technical":"Linear regression","machinery":["OLS","HC3 robust standard errors","VIF","Residual diagnostics"]},
    "logistic_regression":{"human_name":"Outcome Propensity Model","technical":"Logistic regression","machinery":["Log-odds model","Odds ratios","AUC","Brier score"]},
    "tree_model":{"human_name":"Nonlinear Prediction Model","technical":"Tree ensemble","machinery":["Random forest / gradient boosting","Holdout validation","Feature importance"]},
    "marketing_efficiency":{"human_name":"Channel Efficiency Scan","technical":"ROAS / CPA / CPC / CPM analysis","machinery":["Ratio metrics","Scale vs efficiency checks","Zero-denominator guards"]},
    "funnel":{"human_name":"Funnel Leak Finder","technical":"Funnel analysis","machinery":["Step conversion","Drop-off","From-start conversion"]},
    "cohort_retention":{"human_name":"Retention by Cohort","technical":"Cohort analysis","machinery":["Cohort age","Retention matrix","Cohort-size diagnostics"]},
    "did":{"human_name":"Before-vs-After Impact Test","technical":"Difference-in-Differences","machinery":["Treatment × post interaction","Robust/clustered SE","Parallel-trends diagnostics"]},
    "event_study":{"human_name":"Impact Over Time","technical":"Panel event study","machinery":["Unit/time fixed effects","Relative-time coefficients","Clustered SE","Pre-trend diagnostics"]},
    "interrupted_time_series":{"human_name":"Intervention Trend Break","technical":"Interrupted time series","machinery":["Level shift","Slope change","HAC standard errors"]},
    "kmeans_segmentation":{"human_name":"Customer Segment Finder","technical":"K-means clustering","machinery":["Standardization","Silhouette search","Cluster profiles"]},
    "anomaly_detection":{"human_name":"Anomaly Finder","technical":"Isolation Forest","machinery":["Isolation score","Contamination threshold","Ranked anomalies"]},
    "causal_forest":{"human_name":"Who Actually Responded?","technical":"Causal forest / heterogeneous treatment effects","machinery":["Conditional treatment effects","Overlap","Honest validation"]},
}

LAB_SPECIALS = [
    {
        "id":"mmm","title":"Marketing Mix & Budget Optimizer","question":"What is driving performance — and where should the next dollar go?","status":"Beta","description":"Build an MMM-ready time series from marketing data, check whether the mix is identifiable enough to model, estimate observational channel contribution with carryover and saturation, validate through time, and explore constrained budget reallocations.",
        "guardrail":"CampaignLab treats MMM contribution as model-based observational evidence, not proof of causality. High-stakes reallocations should be calibrated with experiments or credible quasi-experimental evidence where possible.",
    }
]
