# Tigo — Financial Analysis AI Agent & React Frontend

This repository contains the full stack implementation for the Tigo Financial Analysis AI Agent demo. It consists of:
1. A **Python FastAPI backend** wrapping a LangChain/LangGraph agent that parses OPEX, CAPEX, and Revenue CSV data to produce a gross-margin report and detect financial alarms.
2. A **Vite + React + TypeScript frontend** that provides an interactive Web UI for reviewing preflight status, generating financial reports, viewing detailed alarms, and conducting interactive chat conversations with the AI agent.

---

## Architecture Overview

```
                        ┌────────────────────────────────────────────────────────┐
                        │                       Web Browser                      │
                        │   ┌────────────────────────────────────────────────┐   │
                        │   │                   React App                    │   │
                        │   │   ┌─────────────┐            ┌─────────────┐   │   │
                        │   │   │  Chat Pane  │            │ Report Pane │   │   │
                        │   │   └─────────────┘            └─────────────┘   │   │
                        │   └───────────────────────┬────────────────────────┘   │
                        └───────────────────────────┼────────────────────────────┘
                                                    │
                                   Fetch & SSE      │ (Dev Proxy: http://localhost:8000)
                                   API Requests     ▼
                        ┌────────────────────────────────────────────────────────┐
                        │                     FastAPI Server                     │
                        │   ┌────────────────────────────────────────────────┐   │
                        │   │                  API Router                    │   │
                        │   │  /health, /api/preflight, /api/chat, /api/r... │   │
                        │   └───────────────────────┬────────────────────────┘   │
                        └───────────────────────────┼────────────────────────────┘
                                                    │
                                                    ▼
                        ┌────────────────────────────────────────────────────────┐
                        │                  LangChain Agent Loop                  │
                        │   ┌───────────────────────────┬────────────────────┐   │
                        │   │       Financial Tools     │    Claude/LLM      │   │
                        │   │  (DSO, P&L, Budgets, etc) │ (Narrative Synth)  │   │
                        │   └─────────────┬─────────────┴──────────▲─────────┘   │
                        └─────────────────┼────────────────────────┼─────────────┘
                                          │                        │
                                          ▼                        │
                               ┌─────────────────────┐    ┌────────┴────────┐
                               │  demo/finance.py    │    │ NVIDIA API Key  │
                               │  demo/alarms.py     │    └─────────────────┘
                               └──────────┬──────────┘
                                          ▼
                                    [data/*.csv]
```

### Components

- **Frontend (`/frontend`)**: A modern SPA built with React 19, TypeScript, and Vite. It communicates with the backend via fetch and Server-Sent Events (SSE) for streaming chat responses. It is configured to run on `http://localhost:5173` and proxy API calls to the backend.
- **Backend Server (`/backend`)**: A FastAPI server running on `http://localhost:8000`. It exposes endpoints for checking system health, running pre-demo validation checks, generating margin reports, and streaming chat tokens.
- **Financial Analysis Engine (`/backend/demo`)**: Contains the core logic for calculating P&L, budget consumption, direct costs, client DSO, and detecting the 9 deterministic alarms from CSV data.

---

## Exposed API Endpoints

The backend FastAPI application exposes the following endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Simple health check endpoint. Returns `{"status": "ok"}`. |
| `/api/preflight` | `GET` | Runs preflight verification checks (verifies `NVIDIA_API_KEY`, data integrity, tool signatures, and live LLM ping). |
| `/api/chat` | `POST` | Accepts a JSON body containing `prompt` and `thread_id`. Streams agent tokens and tool calls back to the client using Server-Sent Events (SSE). |
| `/api/report` | `POST` | Triggers the agent to run the gross-margin report generation prompt and returns the full completed report markdown. |
| `/api/data/regenerate` | `POST` | Clears all active financial CSV files under `backend/data/` and regenerates them using the deterministic seed. |

---

## Local Setup & Run Instructions

Follow these steps to run both the FastAPI server and the Vite React frontend locally.

### 1. Prerequisites
- **Python**: Python 3.14 (or any Python 3.10+ version).
- **Node.js**: Node.js v18 or newer (with `npm`).
- **NVIDIA API Key**: A valid API key is required to interact with the LLM.

---

### 2. Backend Setup & Run

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Set up a Virtual Environment**:
   If not already created, create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

3. **Install Dependencies**:
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your `NVIDIA_API_KEY`:
   ```bash
   cp .env.example .env
   # Open .env and set NVIDIA_API_KEY="..."
   ```

5. **Run Preflight Verification**:
   Verify that your local environment is correctly configured and all financial validation rules pass:
   ```bash
   .venv/bin/python main.py preflight
   # Output should conclude with "READY FOR DEMO"
   ```

6. **Start the FastAPI Server**:
   You can start the backend FastAPI server in development/reload mode:
   ```bash
   .venv/bin/python main.py server --reload
   ```
   *Note: Without `--reload`, you can run it via `.venv/bin/python main.py server`.*

7. **Run Backend Tests (Optional)**:
   ```bash
   .venv/bin/pytest
   ```

---

### 3. Frontend Setup & Run

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install npm dependencies**:
   ```bash
   npm install
   ```

3. **Start the Vite Development Server**:
   ```bash
   npm run dev
   ```
   This will spin up the development server at `http://localhost:5173`. Open this URL in your web browser.

4. **Run Frontend Tests and Checks (Optional)**:
   - **Run tests**: `npm run test`
   - **Run linter**: `npm run lint`
   - **Run TypeScript compilation build check**: `npx tsc -b`
