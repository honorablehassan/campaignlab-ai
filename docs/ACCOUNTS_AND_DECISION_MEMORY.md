# Accounts and persistent Decision Memory

CampaignLab supports optional Streamlit OIDC identity. Without authentication configuration, the product continues to work in local session mode. When a user is authenticated, remembered decisions and observed outcomes persist through the Decision Repository.

## Current implementation

- optional sign in/sign out controls
- stable user identity derived from OIDC subject claims
- per-user decision isolation
- idempotent decision saves
- persistent outcome updates
- per-decision and per-user deletion primitives
- session fallback if persistence is unavailable
- SQLite local repository with WAL journaling

## Production boundary

SQLite is not the final multi-instance SaaS database. Before public multi-user deployment, replace the repository implementation with managed Postgres, encrypt data in transit and at rest, and enforce row-level authorization. Authentication proves identity; database authorization must still prevent cross-user access.

No billing, subscription or monetization behavior is included.
