# Deploy CampaignLab

## 1. Verify the Git boundary

From the git-connected project folder:

```powershell
git status --short
git check-ignore .streamlit/secrets.toml
git check-ignore .venv
git ls-files .streamlit/secrets.toml
```

The first two checks should confirm the local paths are ignored. The last command should return nothing.

## 2. Commit and push

```powershell
git add .
git status --short
git commit -m "Finish CampaignLab portfolio release"
git push origin main
```

Do not use `git add -f`. Confirm that secrets, `.venv`, caches, databases, telemetry and private datasets do not appear on GitHub.

## 3. Deploy on Streamlit Community Cloud

1. Sign in with GitHub.
2. Create an app from `honorablehassan/campaignlab-ai`.
3. Select branch `main` and entry point `app.py`.
4. In Advanced settings, add:

```toml
OPENAI_API_KEY = "your-real-key"
```

5. Deploy and wait for the health check.

Use a separate API project/key for the public demo and set a conservative project budget.

## 4. Smoke-test the public URL

- Home opens on desktop and mobile.
- Strategy Lab produces one structured result.
- Both Evidence demos load and at least one deterministic method completes.
- MMM reaches readiness, model, allocation and decision output.
- Analytics Directory, Behind the Lab and System Health open.
- No key, local username, debug path or private dataset appears on screen.

This deployment is for demonstration with bundled synthetic or non-sensitive data. Do not invite confidential customer uploads until the production gates in `SECURITY.md` are complete.
