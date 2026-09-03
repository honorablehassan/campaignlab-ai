from __future__ import annotations

# Single source of truth for Evidence Lab execution + Analytics Directory documentation.
METHODS = [
    {
        "id":"binary_ab","family":"Experimentation","name":"Binary A/B test","status":"Live",
        "answers":"Did one randomized variant change a yes/no outcome such as conversion?",
        "requires":"Control/treatment assignment and a binary outcome, or group sample sizes + conversions.",
        "use_cases":["Landing-page conversion","Lead submission","Activation","Purchase/no-purchase"],
        "assumptions":["Random or otherwise defensible assignment","Independent experimental units","Stable outcome definition","No material interference between arms"],
        "diagnostics":["Sample-ratio mismatch","Wilson intervals","Fisher exact cross-check","Observed power / MDE context"],
        "outputs":["Absolute and relative lift","95% interval","p-value","business-threshold decision","SHIP / HOLD / DON'T SHIP"],
        "visuals":["Treatment outcome rates","Treatment-effect interval","MDE/sample-size curve"],
        "caution":"Statistical significance does not make a weak commercial effect valuable."
    },
    {
        "id":"continuous_ab","family":"Experimentation","name":"Continuous-outcome A/B test","status":"Live",
        "answers":"Did a randomized treatment change revenue, order value, time, score, or another continuous outcome?",
        "requires":"Treatment assignment plus continuous outcome, or two sets of observations.",
        "use_cases":["Revenue per visitor","Order value","Session duration","Average balance"],
        "assumptions":["Independent units","Defensible assignment","Outcome measured consistently"],
        "diagnostics":["Welch unequal-variance t test","Confidence interval","Cohen's d","Mann–Whitney robustness cross-check","Skew warning"],
        "outputs":["Mean difference","relative lift","95% interval","effect size","decision vs business threshold"],
        "visuals":["Group means + intervals","Outcome distribution","Treatment-effect interval"],
        "caution":"Highly skewed monetary outcomes may need bootstrap/robust analysis in addition to mean comparison."
    },
    {
        "id":"abn","family":"Experimentation","name":"A/B/n multi-arm experiment","status":"Live",
        "answers":"Which of several randomized variants performs best while controlling multiple-comparison error?",
        "requires":"3–20 variant arms plus binary or continuous outcome.",
        "use_cases":["Three creatives","Several offers","Multiple landing pages"],
        "assumptions":["Comparable randomized arms","Independent units","Pre-specified primary outcome"],
        "diagnostics":["Omnibus chi-square or ANOVA","Pairwise Welch/z comparisons","Holm family-wise error correction"],
        "outputs":["Arm summaries","global test","adjusted pairwise effects vs control"],
        "visuals":["Arm performance ranking","Adjusted comparison table"],
        "caution":"Picking the raw highest arm without multiplicity correction exaggerates evidence."
    },
    {
        "id":"bootstrap_difference","family":"Experimentation","name":"Bootstrap group difference","status":"Live",
        "answers":"How uncertain is a mean or median difference when normal approximations are questionable?",
        "requires":"Two groups and a numeric outcome.",
        "use_cases":["Skewed revenue","Median order value","Heavy-tailed engagement"],
        "assumptions":["Observed units are representative and resampling units match the independence unit"],
        "diagnostics":["Empirical bootstrap distribution","Percentile interval"],
        "outputs":["Mean/median effect","bootstrap interval","bootstrap two-sided tail probability"],
        "visuals":["Bootstrap effect distribution","Effect interval"],
        "caution":"Bootstrap does not repair confounding or bad experimental assignment."
    },
    {
        "id":"factorial","family":"Experimentation","name":"Factorial experiment","status":"Planned",
        "answers":"What are main and interaction effects of multiple randomized factors?","requires":"Factor assignments and outcome.",
        "use_cases":["Offer × creative","Message × channel"],"assumptions":["Randomized factor assignment"],"diagnostics":["Cell sizes","interaction estimability"],"outputs":["Main and interaction effects"],"visuals":["Interaction plots"],"caution":"Not yet a validated live CampaignLab executor."
    },
    {
        "id":"cuped","family":"Experimentation","name":"CUPED / pre-period covariate adjustment","status":"Planned",
        "answers":"Can pre-treatment information reduce experiment variance?","requires":"Randomized assignment, outcome, predictive pre-treatment covariate.",
        "use_cases":["Revenue experiments with historical spend"],"assumptions":["Covariate is pre-treatment"],"diagnostics":["Variance reduction","covariate balance"],"outputs":["Adjusted treatment effect"],"visuals":["Adjusted vs raw precision"],"caution":"Not yet Live; planned after expanded experiment-validation tests."
    },
    {
        "id":"linear_regression","family":"Predictive & statistical","name":"Linear regression","status":"Live",
        "answers":"How does a continuous outcome relate to multiple predictors, with uncertainty around coefficients?",
        "requires":"Continuous target and one or more usable predictors; 30+ complete observations.",
        "use_cases":["Revenue drivers","Order value","Spend-response associations"],
        "assumptions":["Reasonable linear specification","Independent errors or appropriate robust/clustered SE","No perfect multicollinearity"],
        "diagnostics":["HC3 robust SE","R² / adjusted R²","RMSE / MAE","VIF","Breusch–Pagan heteroskedasticity check"],
        "outputs":["Coefficients","95% intervals","p-values","fit metrics","multicollinearity diagnostics"],
        "visuals":["Coefficient plot","predicted vs actual","residual diagnostics"],
        "caution":"Regression association is not a causal effect unless identification assumptions justify it."
    },
    {
        "id":"logistic_regression","family":"Predictive & statistical","name":"Logistic regression","status":"Live",
        "answers":"Which variables are associated with or predict a binary outcome?",
        "requires":"Binary target, predictors, at least 10 observations in each class and 30+ complete rows.",
        "use_cases":["Conversion propensity","Churn","Response likelihood","Purchase propensity"],
        "assumptions":["Independent observations","No complete separation","Appropriate functional form for log-odds"],
        "diagnostics":["Convergence/separation failure","AUC","Brier score","pseudo-R²"],
        "outputs":["Coefficients","odds ratios + intervals","p-values","in-sample discrimination/calibration metrics"],
        "visuals":["Odds-ratio plot","probability distribution","calibration plot"],
        "caution":"In-sample AUC is not production validation; coefficients are not causal by default."
    },
    {
        "id":"tree_model","family":"Predictive & statistical","name":"Tree ensemble model","status":"Live",
        "answers":"Can nonlinear interactions improve prediction, and which features carry predictive signal?",
        "requires":"Defined target, predictors, and at least 100 labeled rows.",
        "use_cases":["Propensity modeling","Revenue prediction","Nonlinear driver discovery"],
        "assumptions":["Train/holdout data come from comparable distributions","No target leakage"],
        "diagnostics":["25% holdout evaluation","AUC/Brier/accuracy or R²/RMSE/MAE","feature importance"],
        "outputs":["Holdout metrics","top feature importances","model/task metadata"],
        "visuals":["Feature importance","predicted-vs-actual / score distribution"],
        "caution":"Feature importance is predictive, not causal. Leakage can make a bad model look excellent."
    },
    {
        "id":"marketing_efficiency","family":"Marketing analytics","name":"Channel / campaign efficiency","status":"Live",
        "answers":"Where is observed marketing spend producing the strongest and weakest efficiency?",
        "requires":"Group/channel + spend and revenue or conversions; optional clicks/impressions.",
        "use_cases":["Budget allocation","ROAS","CPA/CAC","CTR/CVR/CPC/CPM"],
        "assumptions":["Metric definitions are comparable across groups","Costs/outcomes are aligned to the same period/scope"],
        "diagnostics":["Zero-denominator guards","negative-value warnings","scale vs efficiency view"],
        "outputs":["ROAS","CPA","CPC","CPM","CTR","CVR","spend share by group"],
        "visuals":["Efficiency ranking","Spend vs revenue","Performance over time"],
        "caution":"Observed attribution efficiency is not incremental causal return."
    },
    {
        "id":"funnel","family":"Marketing analytics","name":"Funnel analysis","status":"Live",
        "answers":"Where do users or counts drop between ordered funnel stages?","requires":"Two or more ordered stage columns/counts.",
        "use_cases":["Impression → click → lead → sale","Signup → activation → paid"],"assumptions":["Stages are ordered and comparably defined"],"diagnostics":["Step conversion","drop-off","from-start conversion"],"outputs":["Stage counts and rates"],"visuals":["Funnel bars"],"caution":"Aggregate funnels do not prove individual-level progression unless data are constructed that way."
    },
    {
        "id":"cohort_retention","family":"Marketing analytics","name":"Cohort & retention analysis","status":"Live",
        "answers":"How do customer cohorts continue to appear or engage over subsequent periods?",
        "requires":"Customer identifier + event date with repeated customers.",
        "use_cases":["Acquisition cohort retention","Repeat purchase","Lifecycle engagement"],
        "assumptions":["Repeated appearance is a meaningful retention event","Customer IDs are stable"],
        "diagnostics":["Cohort size","age-period retention matrix"],
        "outputs":["Retention by cohort age","cohort sizes"],
        "visuals":["Retention heatmap","cohort curves"],
        "caution":"This implementation measures repeated presence; event-specific retention requires filtering/definition upstream."
    },
    {
        "id":"did","family":"Causal inference","name":"Difference-in-Differences","status":"Live",
        "answers":"Did an intervention change an outcome relative to a comparison group after treatment?",
        "requires":"Outcome + binary treatment group + binary pre/post indicator; ideally repeated units.",
        "use_cases":["Geo campaign launch","Policy rollout","Market-level intervention"],
        "assumptions":["Parallel counterfactual trends","No differential concurrent shocks","No anticipatory treatment effects"],
        "diagnostics":["2×2 cell summaries","HC3 or unit-clustered SE","effect interval"],
        "outputs":["DiD interaction effect","95% interval","p-value","cell means"],
        "visuals":["Pre/post group trends","counterfactual gap"],
        "caution":"A DiD regression running successfully does not prove parallel trends. Use event-study/pre-trend diagnostics."
    },
    {
        "id":"event_study","family":"Causal inference","name":"Panel event study","status":"Live",
        "answers":"How do estimated treatment effects evolve before and after an intervention?",
        "requires":"Outcome, treated/control indicator, relative event time, unit ID, calendar time; 80+ rows and 4+ units.",
        "use_cases":["Market rollout dynamics","Pre-trend diagnostics","Treatment persistence"],
        "assumptions":["Credible comparison units","appropriate timing specification","fixed-effects design is suitable"],
        "diagnostics":["Clustered SE by unit","pre-period coefficients","reference-period normalization"],
        "outputs":["Relative-time effects + intervals","pre-period estimates"],
        "visuals":["Event-study coefficient plot"],
        "caution":"Pre-trend tests are diagnostics, not proof of identification. Staggered adoption may require specialized estimators."
    },
    {
        "id":"interrupted_time_series","family":"Causal inference","name":"Interrupted time series","status":"Live",
        "answers":"Did the level or trend of a time series change at a known intervention date?",
        "requires":"20+ ordered time points, numeric outcome, intervention date, with at least 5 pre and post periods.",
        "use_cases":["Site redesign launch","Pricing change","Campaign launch with no control series"],
        "assumptions":["No major concurrent shocks","trend form is appropriate","intervention timing is known"],
        "diagnostics":["HAC robust SE","level change","slope change"],
        "outputs":["Immediate level shift","slope change","baseline trend","R²"],
        "visuals":["Observed series + intervention","fitted pre/post trend"],
        "caution":"Without a comparison series, concurrent events and seasonality can mimic intervention effects."
    },
    {
        "id":"kmeans_segmentation","family":"Data science","name":"K-means segmentation","status":"Live",
        "answers":"Can rows/customers be grouped into internally similar profiles across numeric features?","requires":"2+ numeric features and at least 50 complete rows.",
        "use_cases":["Customer segmentation","Behavioral archetypes","Campaign audience discovery"],
        "assumptions":["Scaled Euclidean distance is meaningful","chosen features represent the segmentation goal"],
        "diagnostics":["Standardization","automatic 2–8 cluster silhouette search","cluster sizes"],
        "outputs":["Cluster profiles","cluster shares","silhouette score"],
        "visuals":["Cluster profile chart","PCA/2D exploration when appropriate"],
        "caution":"Clusters are descriptive patterns, not causal or objectively true customer types."
    },
    {
        "id":"anomaly_detection","family":"Data science","name":"Isolation Forest anomaly detection","status":"Live",
        "answers":"Which observations are unusually different across a chosen numeric feature set?","requires":"Numeric features and at least 50 complete rows.",
        "use_cases":["Campaign anomalies","Suspicious performance rows","Data-quality investigation"],
        "assumptions":["Feature space represents what 'unusual' should mean"],
        "diagnostics":["Standardized features","explicit contamination rate","ranked anomaly score"],
        "outputs":["Flagged share","top unusual rows by index + feature values"],
        "visuals":["Anomaly score ranking","scatter highlights"],
        "caution":"Unusual does not mean wrong, fraudulent, or causally important. Investigate before removing data."
    },
    {
        "id":"synthetic_control","family":"Causal inference","name":"Synthetic control","status":"Research",
        "answers":"What might have happened to one/few treated units without intervention?","requires":"Long pre-period + credible donor pool.",
        "use_cases":["Geo intervention"],"assumptions":["Donor pool can reproduce treated pre-period"],"diagnostics":["Pre-fit RMSPE","placebos"],"outputs":["Synthetic counterfactual gap"],"visuals":["Actual vs synthetic"],"caution":"Research status; not executed automatically yet."
    },
    {
        "id":"dag_adjustment","family":"Causal inference","name":"DAG-guided adjustment","status":"Research",
        "answers":"Which variables should be adjusted for, avoided, or treated as mediators?","requires":"Explicit causal assumptions/graph.",
        "use_cases":["Confounder selection"],"assumptions":["Graph encodes credible causal knowledge"],"diagnostics":["Backdoor path reasoning"],"outputs":["Candidate adjustment set"],"visuals":["Causal graph"],"caution":"A DAG is a reasoning layer, not an estimator."
    },
    {
        "id":"dml","family":"Causal inference","name":"Double / Debiased Machine Learning","status":"Research",
        "answers":"Estimate causal effects with flexible nuisance models in high-dimensional observational data.","requires":"Treatment, outcome, rich pre-treatment covariates, overlap + identification assumptions.",
        "use_cases":["High-dimensional observational incrementality"],"assumptions":["Unconfoundedness/identification","overlap","cross-fitting"],"diagnostics":["Overlap","nuisance performance"],"outputs":["Orthogonalized treatment effect"],"visuals":["Effect intervals"],"caution":"Not exposed as Live until validated against known causal benchmarks."
    },
    {
        "id":"causal_forest","family":"Causal inference","name":"Causal forest / heterogeneous treatment effects","status":"Research",
        "answers":"For whom might treatment effects differ?","requires":"Large sample, treatment/outcome, rich pre-treatment covariates and credible causal design.",
        "use_cases":["Treatment targeting"],"assumptions":["Causal identification + sufficient sample"],"diagnostics":["Overlap","honest validation"],"outputs":["Conditional treatment effects"],"visuals":["HTE distribution"],"caution":"Research status; subgroup discovery can overfit badly."
    },
    {
        "id":"mmm_beta","family":"Marketing analytics","name":"Marketing Mix & Budget Optimizer","status":"Beta",
        "answers":"What is driving aggregate performance, where is media saturating, and how could a fixed budget be reallocated within observed support?",
        "requires":"Regular time series with outcome, 2+ media-spend columns, meaningful spend variation, and preferably controls for promotions/pricing/other demand drivers.",
        "use_cases":["Channel contribution","Response curves","Marginal budget allocation","Marketing planning"],
        "assumptions":["Observed controls capture important alternative demand drivers","Response shape is reasonably represented by carryover + saturation","Historical variation contains enough information to distinguish channels"],
        "diagnostics":["MMM readiness gate","Channel correlation","Spend variation","Chronological holdout","Historical-support budget bounds"],
        "outputs":["Model-attributed contribution","Carryover / saturation parameters","Holdout error","Constrained budget scenario","Evidence-strength label"],
        "visuals":["Actual vs modeled history","Channel contribution","Current vs scenario allocation"],
        "caution":"Beta Lab Special. Observational MMM is not proof of causality; calibrate high-stakes decisions with experiments or credible quasi-experimental evidence where possible."
    },

]


def get_method(method_id: str) -> dict | None:
    return next((m for m in METHODS if m["id"] == method_id), None)


def methods_by_family() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for method in METHODS:
        grouped.setdefault(method["family"], []).append(method)
    return grouped


def live_methods() -> list[dict]:
    return [m for m in METHODS if m["status"] == "Live"]
