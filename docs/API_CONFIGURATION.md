# API and configuration

## Verified endpoints

- `POST /api/investigate`
- `POST /api/events/replay`
- `GET /api/history`
- `GET /api/agents`
- `GET /api/tools`
- `GET /api/models`
- `GET /api/investigations/{run_id}/trace`
- `GET /api/work`
- `POST /api/evaluations`
- `GET /api/evaluations`
- `GET /api/audit`

## Configuration

- `META_MODEL_MODE=demo` keeps Meta synthesis network-free.
- `WRI_AGENT_MODE=simulation` selects deterministic planning; `live` enables
  opt-in supervisor and specialist model calls.
- `MODEL_API_KEY` is server-side only for optional live Meta synthesis.
- `WRI_MONITOR_ENABLED=true` enables local JSON polling.
- `WRI_AUTH_ENABLED=true` enables local demo bearer authentication.
- `WRI_DEMO_USERS` configures local demo users; do not use demo credentials in
  production.
- `WRI_DATABASE_PATH` selects the SQLite database.

Secrets must be supplied through the environment or a local ignored
configuration file and never committed, logged, or sent to the frontend.
