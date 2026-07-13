# Exploration: react-frontend

### Current State
The `demo-tigo` backend is a Python 3.14 console application with CLI subcommands:
- `data`: Regenerates simulated financial data.
- `report`: Runs the LangChain agent over pandas data tools and outputs a formatted gross-margin markdown report.
- `chat`: Starts an interactive terminal Q&A loop.
- `preflight`: Verifies environment, dataset integrity, and LLM access.

There is currently no web interface or HTTP API server. To integrate a React frontend, we must expose the financial engine metrics and agent/chat capabilities via HTTP endpoints.

### Affected Areas
- `backend/requirements.txt` — Needs web server packages (`fastapi`, `uvicorn`).
- `backend/main.py` — Needs a new `server` subcommand to boot the HTTP API.
- `backend/demo/server.py` — A new module containing the FastAPI app, router, CORS settings, and endpoint handlers mapping to the tools in `backend/demo/tools.py`.
- `frontend/` — A new directory where the Vite + React + TS workspace will be created.

### Approaches

1. **FastAPI Web Server on Python Backend + Vite React TS Frontend**
   - **Description**: Add FastAPI and Uvicorn to the existing Python backend to expose endpoints for the 9 financial analysis tools and the agent chat. Create a standalone Vite + React + TS application in the `frontend/` directory.
   - **Pros**: 
     - Very fast, lightweight, and modern.
     - Out-of-the-box support for Pydantic (already used in the backend for `Alarm` models).
     - Generates interactive OpenAPI docs (`/docs`), making it easy to create frontend type definitions.
     - Low latency, high performance, easy setup for Server-Sent Events (SSE) to stream chat messages.
   - **Cons**: Requires adding new dependencies to the Python backend (`fastapi`, `uvicorn`).
   - **Effort**: Low-Medium

2. **Next.js (Node.js) API Wrapper calling CLI scripts**
   - **Description**: Build a Next.js application in `frontend/`. The Next.js API routes run CLI commands (e.g. `python3 main.py chat --prompt "..."`) via child process executions, capture stdout, and return the response.
   - **Pros**: 
     - Zero modifications required to the Python dependencies.
   - **Cons**: 
     - Extremely high latency (re-instantiating the Python VM, loading pandas, importing modules, and hitting the LLM for every single HTTP request).
     - Fragile parsing of console output.
     - Hard to maintain and stream chat responses back to the UI.
   - **Effort**: Medium

3. **LangServe (LangChain Web Server)**
   - **Description**: Use LangChain's official serving framework `LangServe` to expose the LangGraph agent chain.
   - **Pros**: 
     - Standardized LangChain streaming and endpoint generation.
   - **Cons**: 
     - Heavyweight wrapper.
     - More complex to customize for non-agent data endpoints (e.g. fetching raw P&L JSONs, budgets, and invoices).
   - **Effort**: Medium-High

### Recommendation
**Approach 1 (FastAPI + Vite + React + TS)** is the recommended approach. It offers high performance, clean API routes, native JSON/Pydantic serialization, and supports streaming responses cleanly. It aligns with the existing python toolchain without introducing process overhead.

### Risks
- **CORS Configuration**: Requests from the Vite dev server (`http://localhost:5173`) to FastAPI (`http://localhost:8000`) will be blocked by default unless CORS is explicitly allowed in FastAPI or proxied via Vite.
- **LLM/Network Latency**: Generating a report or chat response makes live API requests to NVIDIA AI endpoints, which can take several seconds. The frontend UI must utilize loading states, disabled buttons, and server-sent streaming to prevent UI freezes.
- **API Key Exposure**: The backend uses `NVIDIA_API_KEY` stored in `.env`. We must ensure it is kept server-side and never exposed to the frontend.

### Ready for Proposal
Yes. The orchestrator should proceed with presenting this structured analysis to the user and request approval to create a design specification (`proposal.md`) under `openspec/changes/react-frontend/proposal.md` outlining the API endpoints schema, frontend layout (dashboard, alarms feed, chat component), and installation/execution scripts.
