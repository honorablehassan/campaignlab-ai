# CampaignLab security notes

- Never commit `.streamlit/secrets.toml`, `.env`, API keys, raw customer extracts, or credentials.
- Uploaded datasets are processed in the running Streamlit process. The tool runtime returns compact structured summaries to the LLM; it does not expose raw rows as tool outputs.
- The Evidence orchestrator can call only explicitly registered tools. It cannot execute arbitrary Python or arbitrary SQL.
- Production deployment should add authentication, encrypted managed storage where needed, centralized secret management, retention rules, and provider-level audit logging.
- Optional OIDC accounts use Streamlit's native authentication boundary. Unauthenticated sessions are never written into persistent Decision Memory.
- The bundled SQLite Decision Memory is for local/single-instance use. A multi-user production deployment must use managed encrypted storage behind the repository interface and enforce per-user authorization at the database layer.
- Decision Memory exposes per-decision and full-memory deletion. Persistent deletion removes associated outcome observations as well as the decision.
- All tabular uploads pass through one bounded parser: CSV/XLSX only, non-empty, and at most 50 MB by default. Parser failures are converted into compact user-facing errors.
- System Health reports deployment boundaries explicitly. A passing local test suite is not represented as multi-tenant production readiness.

## Production launch gates

- Replace local SQLite with encrypted managed storage and database-layer row authorization.
- Configure and test OIDC login, logout, callback URLs, session expiry, and account deletion in the deployed environment.
- Store secrets in the deployment provider, apply least-privilege access, and rotate them under an incident procedure.
- Define evidence and decision retention periods, backups, restore testing, audit logging, rate limits, and abuse controls.
- Run dependency, application-security, privacy, and independent statistical reviews before handling customer data.
