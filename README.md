# Garmin Trainer

Garmin Trainer is being refactored from a local AI-coach CLI into a single-user PWA and cloud API. The existing CLI remains available while the first web foundation is added.

## Setup

The agents call into `garmin-health-data`'s `garmin-mcp` console script over stdio. Both packages should live in the same venv so the script is on `PATH`.

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e ../garmin-data        # installs the garmin-mcp script
.venv/bin/pip install -e ".[dev]"

cp .env.example .env
# Set GARMIN_DB_PATH

# One-time auth — uses your Claude Pro/Max subscription, not API credits
claude login
```

The Claude Agent SDK requires the [Claude Code CLI](https://docs.claude.com/en/docs/claude-code/quickstart) to be installed and on `PATH`. Auth runs through that CLI: this project deliberately unsets `ANTHROPIC_API_KEY` at startup so all calls are billed against your subscription instead of pay-as-you-go API credits.

## Usage

```bash
.venv/bin/training-coach
.venv/bin/training-coach --question "Am I overtraining?"
.venv/bin/training-coach --question "I have a half marathon in 8 weeks — plan the next 2 weeks."
```

## Architecture

- [agents/training_coach.py](agents/training_coach.py) drives a tool-using loop with the Claude Agent SDK. It does not query SQL directly.
- Data access goes through the `garmin` MCP server (started as a subprocess via stdio), which exposes 11 read-only semantic tools — `get_user_profile`, `get_recent_activities`, `get_training_load`, `get_training_readiness`, `get_sleep`, `get_hrv_trend`, `get_vo2_max_trend`, `get_personal_records`, `get_race_predictions`, plus `list_users` / `get_activity_details`. See the [garmin-health-data MCP docs](https://github.com/diegoscarabelli/garmin-health-data#mcp-server) for the full tool surface.
- Model: `claude-opus-4-7`.

## Web foundation (Phase 1)

- `web/`: React/TypeScript PWA, Firebase email/password sign-in and email verification.
- `api/`: FastAPI service. `/healthz` is a minimal liveness endpoint; `/api/v1/me` verifies Firebase ID tokens and only accepts the configured verified user email.
- `infra/`: Terraform for Firebase Hosting/Auth, Firestore, Secret Manager, Artifact Registry and Cloud Run. See [infra/README.md](infra/README.md) for the bootstrap/apply sequence.
- `.github/workflows/terraform-checks.yml`: API tests, PWA build, Terraform format and validation.
- `.github/workflows/deploy.yml`: manual `workflow_dispatch` pipeline that applies Terraform and then deploys the API/PWA using WIF.

The Cloud Run endpoint is invokable by Firebase Hosting's `/api/**` rewrite, but application routes require a valid Firebase ID token and the server-side email allowlist. Firestore is not accessed directly from the browser; its rules deny client access.

### Local development

```powershell
# API
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r api/requirements-dev.txt
python -m uvicorn app.main:app --app-dir api --reload --port 8080

# In another terminal
cd web
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Set local Firebase web config in `web/.env.local` after the Terraform Firebase
web app is provisioned. The browser Firebase API key is public client config;
never put the Garmin key or an LLM credential there. The local API loads
`GCP_PROJECT_ID`, `ALLOWED_USER_EMAIL` and `CORS_ALLOWED_ORIGINS` from the
root `.env` file. No GCP resources have been created by these source files.

## Adding a new agent

Each agent is one file in `agents/`. The pattern:

1. Build a `ClaudeAgentOptions` with the `garmin` MCP server wired in and `allowed_tools` listing the tools the agent should use.
2. Write a focused system prompt that tells the agent which tools to call in what order.
3. Drive `query()` and stream `AssistantMessage` text blocks to stdout.

See [training_coach.py](agents/training_coach.py) as the reference.
