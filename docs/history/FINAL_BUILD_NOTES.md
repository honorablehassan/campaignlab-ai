# Final Build Notes

This package is the consolidated build intended to replace the untouched baseline project.

## Live deterministic analytical methods
15 live analytical capabilities are registered: binary A/B, continuous A/B, A/B/n, bootstrap difference, linear regression, logistic regression, tree ensemble modeling, marketing efficiency, funnel analysis, cohort retention, Difference-in-Differences, event study, interrupted time series, K-means segmentation, and Isolation Forest anomaly detection.

## Validation performed before packaging
- Python compileall across the project
- automated unit test suite across original and breadth engines
- synthetic known-signal tests for experiment, regression, predictive, causal, marketing, cohort and unsupervised methods
- tool whitelist test rejects arbitrary code execution
- raw DataFrame is not returned by profile tool
- capability registry contract checks

## Important boundaries
- Live does not mean every possible scientific assumption is automatically satisfied.
- DiD/event-study/ITS execution is gated by structural requirements and returns causal-assumption warnings.
- predictive tree importance is not causal.
- observed ROAS/CPA is not incrementality.
- Research methods remain visible in the Directory but are not executed.

## V2.5 — Decision Architecture + MMM Lab Special
- Analytics Directory now follows business question → family → method → statistical machinery.
- Statistical primitives are no longer a disconnected bottom section.
- Shared Data Gate foundation added for prediction/forecasting readiness.
- Dedicated MMM Lab Special added as Beta with readiness, carryover/adstock, saturation, chronological holdout validation, contribution, and constrained budget scenario optimization.
- Added `examples/demo_mmm_weekly.csv` (156 weekly periods) for deterministic testing/demo.
- 37/37 automated tests pass.
