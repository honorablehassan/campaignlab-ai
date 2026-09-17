# CampaignLab architecture

CampaignLab separates calculation, reasoning and presentation so an AI-generated sentence cannot quietly become a statistical result.

| Layer | Responsibility | Trust boundary |
|---|---|---|
| Streamlit UI | Collect the question or file and disclose detail progressively | Does not determine statistical truth |
| Dataset intelligence | Profile structure, quality, semantic roles and answerability | Summarizes before method selection |
| Capability registry | Declare which methods are genuinely executable | A method is not ready without an executor |
| Python engines | Calculate estimates, diagnostics and eligibility checks | Deterministic code owns the numbers |
| Reasoning layer | Explain results, challenge assumptions and structure the decision | Receives bounded context and cannot execute arbitrary code |
| Decision Kernel | Normalize evidence, uncertainty, alternatives and next action | Preserves provenance and method diagnostics |
| Decision Memory | Store decisions and observed outcomes | SQLite is local/single-instance only |

## Reliability choices

- CSV/XLSX uploads use one bounded parser with a 50 MB default limit.
- Model requests have explicit timeouts, bounded retries and user-safe error references.
- The orchestrator exposes only registered analytical tools.
- UI error boundaries isolate failures by product surface.
- Demo datasets are reproducible and paired with a truth manifest.
- Contract tests protect terminology and output structure while engine tests verify numerical behavior.

## Deployment boundary

The repository is appropriate for a public portfolio deployment using synthetic or non-sensitive data. Before accepting customer data, replace SQLite with encrypted managed storage, configure and test authentication, define retention and deletion policies, add rate limits and centralized audit logging, and complete independent security, privacy and statistical review.
