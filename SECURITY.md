# CampaignLab security notes

- Never commit `.streamlit/secrets.toml`, `.env`, API keys, raw customer extracts, or credentials.
- Uploaded datasets are processed in the running Streamlit process. The tool runtime returns compact structured summaries to the LLM; it does not expose raw rows as tool outputs.
- The Evidence orchestrator can call only explicitly registered tools. It cannot execute arbitrary Python or arbitrary SQL.
- Production deployment should add authentication, encrypted managed storage where needed, centralized secret management, retention rules, and provider-level audit logging.
