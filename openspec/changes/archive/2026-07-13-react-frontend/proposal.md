# Proposal: react-frontend

## Intent
Create a web interface for the `demo-tigo` project using Vite, React, and TypeScript, connected to a new FastAPI backend server.

## Scope
### In Scope
- Expose the financial report agent via HTTP REST and SSE endpoints in the backend.
- Build a React-based UI for Q&A and viewing/triggering financial reports.
- Support real-time streaming of agent responses via Server-Sent Events (SSE).

### Out of Scope
- User authentication and authorization.
- Persistent database storage for chat history or reports.
- Advanced charts and data visualization.

## Capabilities
### New Capabilities
- `web-api`: REST/SSE API endpoints exposing agent features (chat, report run, data regen).
- `react-frontend-ui`: A React single-page application for user interaction and report monitoring.

### Modified Capabilities
- None.

## Approach
1. **Backend Integration**: Add `fastapi` and `uvicorn` to `backend/requirements.txt`. Add a `server` subcommand in `backend/main.py` and implement API routers in `backend/demo/server.py`.
2. **Frontend Setup**: Scaffold a Vite + React + TS project in a new `frontend/` folder. Configure the Vite dev proxy to forward API requests to the FastAPI backend.
3. **UI Implementation**: Build chat, report list, and report generation controls with proper loading/streaming states.

## Affected Areas
- `backend/requirements.txt`: New package requirements.
- `backend/main.py`: Command-line interface extension.
- `backend/demo/`: New `server.py` implementation.
- Repository root: New `frontend/` directory.

## Risks
- **CORS Configuration**: Handled by configuring CORS middleware in FastAPI and using Vite proxy.
- **LLM Latency**: Mitigated via streaming/SSE and responsive UI loading indicators.
- **API Key Exposure**: Mitigated by keeping all LLM interactions and keys strictly on the backend.

## Rollback Plan
Run `git reset --hard` or manually delete the `frontend/` directory and revert edits under `backend/`.

## Dependencies
- FastAPI, Uvicorn, and SSE-Starlette.
- Node.js, Vite, React, TypeScript.

## Success Criteria
A running frontend application that successfully triggers report generation, chats with the agent in real time, and passes all `preflight` validation scripts.
