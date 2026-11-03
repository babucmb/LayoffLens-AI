# LayoffLens AI

### Enterprise Workforce Resilience Intelligence Platform

**See the risks. Find the alternatives. Protect the workforce.**

LayoffLens AI is an AI-powered enterprise decision-support platform designed to help organizations identify business and operational risks early, investigate their causes, forecast potential impacts, and evaluate alternatives before considering workforce reductions.

It brings together financial, sales, project, workforce capacity, hiring, AI investment and infrastructure signals into a coordinated investigation and scenario-planning workflow.

Rather than automatically recommending layoffs, LayoffLens AI helps decision-makers understand business conditions, explore preventive alternatives, review supporting evidence and retain human control over decisions.

> **Demo environment:** The included dataset is synthetic and aggregate-only. No individual employee termination scoring, automated employment decisions or live HR/payroll integrations are performed.

---

## Key Features

- **Enterprise Intelligence:** Analyze financial performance, sales pipeline, project delivery, workforce capacity and infrastructure signals.
- **Risk Detection:** Identify business anomalies, operational risks and emerging capacity mismatches.
- **Multi-Agent Investigation:** Coordinate bounded specialist workflows to investigate selected business events.
- **Meta AI Integration:** Optional Meta Model API integration for structured supervisor and specialist reasoning.
- **Business Forecasting:** Generate deterministic projections and compare business outlooks.
- **Scenario Planning:** Compare baseline, downside and preventive intervention scenarios.
- **Alternative Evaluation:** Explore reskilling, redeployment, contractor optimization, spending reviews and other illustrative preventive options.
- **Evidence-Based Reviews:** Maintain investigation evidence, reviewer comments, decisions and audit history.
- **Research Integration:** Optionally retrieve relevant public information through Tavily.

## How It Works

1. **Collect:** Load and validate enterprise demonstration data.
2. **Detect:** Identify signals, anomalies and potential business risks.
3. **Investigate:** Execute a bounded investigation using relevant specialist agents.
4. **Forecast:** Evaluate potential financial and operational outcomes.
5. **Simulate:** Compare baseline, downside and preventive alternatives.
6. **Review:** Present evidence and findings for human assessment.
7. **Record:** Preserve investigation and review history locally.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Analytics | Pandas, NumPy, deterministic forecasting |
| AI integration | Meta Model API |
| Agent orchestration | Bounded supervisor and specialist runtime |
| External research | Optional Tavily API |
| Persistence | SQLite |
| Testing | Pytest |

---

## Project Structure

```text
LayoffLens-AI/
│
├── backend/
│   ├── app/
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── data/
├── tests/
│   └── fixtures/
│
├── scripts/
├── docs/
│
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

# Installation and Setup

## 1. Prerequisites

Install the following before running the application:

- Python 3.10 or later (use the Python version supported by the project dependencies).
- pip.
- Git.
- A modern web browser.

## 2. Clone the repository

Open Windows PowerShell:

```powershell
git clone YOUR_GITHUB_REPOSITORY_URL
cd LayoffLens-AI
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual public GitHub repository URL.

## 3. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 4. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

## 5. Configure environment variables

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the required settings.

### Environment configuration

The application uses demo mode by default. No API key is required to run the deterministic demonstration.

```env
# Application modes
META_MODEL_MODE=demo
WRI_AGENT_MODE=simulation

# Meta Model API
MODEL_API_KEY=
META_MODEL_ID=muse-spark-1.3
META_MODEL_BASE_URL=https://api.meta.ai/v1

# Optional specialist model overrides
META_SUPERVISOR_MODEL=
META_SIGNAL_MODEL=
META_RESEARCH_MODEL=
META_FINANCE_MODEL=
META_DEMAND_MODEL=
META_CAPACITY_MODEL=
META_OPERATIONS_MODEL=
META_SCENARIO_MODEL=
META_ALTERNATIVES_MODEL=
META_REVIEW_MODEL=
META_REPORTING_MODEL=

# Optional Tavily public research integration
TAVILY_API_KEY=
TAVILY_API_URL=https://api.tavily.com/search
WRI_RESEARCH_TIMEOUT_SECONDS=15

# Local database
WRI_DATABASE_PATH=

# Bounded agent execution
WRI_AGENT_TIMEOUT_SECONDS=20
WRI_AGENT_MAX_STEPS=12

# Optional local authentication and monitoring
WRI_AUTH_ENABLED=false
WRI_MONITOR_ENABLED=false
```

### Understanding the configuration

| Variable | Purpose |
|---|---|
| `META_MODEL_MODE` | Selects Meta demo or live model mode |
| `WRI_AGENT_MODE` | Selects simulation or live agent execution |
| `MODEL_API_KEY` | Server-side Meta API credential |
| `META_MODEL_ID` | Meta model identifier |
| `META_MODEL_BASE_URL` | Meta API base URL |
| `TAVILY_API_KEY` | Optional public research API credential |
| `WRI_DATABASE_PATH` | Optional local SQLite database location |
| `WRI_AGENT_TIMEOUT_SECONDS` | Maximum agent execution timeout |
| `WRI_AGENT_MAX_STEPS` | Maximum bounded investigation steps |

**Important:**

- Keep `META_MODEL_MODE=demo` and `WRI_AGENT_MODE=simulation` for the default demonstration.
- Live Meta requests require an authorized API key and appropriate account access.
- To enable live Meta integration, configure:

```env
META_MODEL_MODE=live
WRI_AGENT_MODE=live
MODEL_API_KEY=YOUR_META_API_KEY
```

- Tavily is optional and requires its own API key.
- Never commit your actual `.env` file or API credentials to GitHub.
- The Meta live integration was implemented and mock-tested but has not been live-verified in this submission.

---

# Running the Application

From the repository root, with your virtual environment activated:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open the application:

**Frontend:** http://127.0.0.1:8000/

**FastAPI documentation:** http://127.0.0.1:8000/docs

The application uses a local SQLite database for persisted investigation and review information. By default, the database is created locally. You can configure a different location using `WRI_DATABASE_PATH`.

To stop the application, press `Ctrl + C` in PowerShell.

---

# Running Tests

From the project root:

```powershell
python -m pytest -q
```

Additional validation:

```powershell
python -m compileall -q backend

node --check frontend/app.js

python scripts/check_submission.py
```

---

# Meta AI Integration

LayoffLens AI includes an optional Meta Model API integration.

The integration is designed to support structured supervisor and specialist reasoning, while deterministic analytics remain responsible for numerical calculations and scenario results.

The application supports:

- Configurable Meta model selection.
- Structured model outputs.
- Bounded model execution.
- Response validation.
- Deterministic fallback when live inference is unavailable.

The default demo configuration does not make outbound Meta API requests.

Live Meta inference has not been verified in this submission. See `docs/meta-api-integration.md` for additional implementation details.

# Data and Responsible Use

The current demonstration uses synthetic, aggregate-only enterprise data.

It does not:
- Connect to actual company HR, payroll or ERP accounts.
- Score named employees for termination.
- Recommend individual layoffs.
- Automatically make employment decisions.
- Replace management, legal or human-resources review.

Scenario costs and preventive savings are illustrative assumptions, not guaranteed financial outcomes.

Public research is contextual information and is not treated as verified internal enterprise evidence.

# Current Limitations

LayoffLens AI is a hackathon implementation and decision-support foundation.

Production deployment would require additional work, including:
- Authorized enterprise data integrations.
- Organization-specific identity and access management.
- Production-grade tenant isolation and security.
- Real-world forecast validation.
- Data retention and privacy controls.
- Production monitoring and deployment infrastructure.

# Hackathon Project

**Event:** Meta Global AI Developer Hackathon 2026

**Problem statement:** Build for Your World

**Project:** LayoffLens AI — Enterprise Workforce Resilience Intelligence Platform

The project explores how Meta AI-powered reasoning, coordinated investigation workflows and explainable business analytics can help organizations identify risks earlier and evaluate alternatives before making workforce-related decisions.

**Demo video:** Add your three-minute demo URL here.

**Repository:** Add your public GitHub repository URL here.

---

**Built for a future where business resilience and workforce protection go hand in hand.**
