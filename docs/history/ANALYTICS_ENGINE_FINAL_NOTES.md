# CampaignLab Analytics Engine Final Hardening Batch

Base: CampaignLab V2.6 MMM Flagship UI
Purpose: cumulative analytics/data-trust hardening before the dedicated UI/UX QA phase.

## What this batch contains

- All red-team fixes accumulated after V2.6.
- 644 automated tests passing in the final assembled tree.
- Deterministic Data Builder foundation and "CampaignLab found your evidence" source understanding.
- Multi-export MMM Data Builder: separate media + commerce files can be mapped, aggregated, aligned, and handed to MMM readiness.
- Built-in five-source Data Builder demo (Meta-like, Google Ads-like, YouTube-like, TV-like, commerce).
- GA4-like source understanding and ordered event-funnel builder support.
- Large-data guardrail messaging that recommends warehouse/SQL query pushdown instead of raw-row movement.
- Dataset Intelligence fixes for event-level GA4-style tables, duration/time false positives, and binary-flag false outcomes.
- MMM hardening: missing/non-finite core fields blocked, negative spend blocked, duplicate periods blocked, non-numeric controls blocked, outcome variation required, baseline-vs-media holdout benchmark, conservative evidence strength, and optimizer extrapolation refusal.
- A/B alpha/business-threshold validation hardening.
- Event-study treatment-effect uncertainty calculation hardened against irrelevant nuisance-parameter covariance warnings.

## Data Builder philosophy

Infer the obvious. Ask only when ambiguity changes the analysis. Preserve unknowns rather than manufacture certainty.

Important examples:
- Missing media is not silently converted to zero.
- Generic ad schemas are not falsely labeled Meta/Google without platform-specific evidence.
- Platform-attributed revenue is not treated as incrementality.
- Large event streams are candidates for SQL/query pushdown rather than raw app ingestion.

## Scope boundary

This is the final analytics-engine hardening batch before a separate full UI/UX QA. It intentionally does not add production warehouse connectors yet. The Data Builder exposes the correct future connector architecture without pretending those integrations already exist.
