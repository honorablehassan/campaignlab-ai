MODEL = "gpt-5.6-luna"

PAGE_TITLE = "CampaignLab"
PAGE_ICON = "🧪"

# Runtime resilience. OpenAI's SDK performs bounded retry/backoff for transient errors.
API_TIMEOUT_SECONDS = 45.0
API_MAX_RETRIES = 2

# Cost telemetry only. Keep these configurable if pricing changes.
MODEL_INPUT_COST_PER_MILLION = 0.20
MODEL_CACHED_INPUT_COST_PER_MILLION = 0.02
MODEL_OUTPUT_COST_PER_MILLION = 1.20
