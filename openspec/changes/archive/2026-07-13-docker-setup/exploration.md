## Exploration: docker-setup

### Current State
The `demo-tigo` project is split into a [FastAPI backend](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend) and a [Vite + React frontend](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend).
- The backend is run locally via Uvicorn (defaulting to `localhost:8000`). It reads configuration (specifically `NVIDIA_API_KEY`) from [backend/.env](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/.env).
- The frontend is run via Vite dev server (defaulting to `localhost:5173`). It contains a proxy block in [vite.config.ts](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/vite.config.ts) forwarding all `/api` requests to `http://localhost:8000`.

### Affected Areas
- [backend/Dockerfile](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/Dockerfile) — New file to containerize backend service using `python:3.14-slim`.
- [frontend/Dockerfile](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/Dockerfile) — New file to containerize frontend service using `node:22-alpine`.
- [docker-compose.yml](file:///Users/alephzero/projects/demo-tigo/demo-tigo/docker-compose.yml) — New orchestration file for local development containers.
- [frontend/vite.config.ts](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/vite.config.ts) — Modify to support dynamic API url routing and host exposure inside the Docker network.
- [backend/.env](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/.env) — Loaded by Docker Compose to supply secrets to the backend container.

### Approaches
1. **Single/Monolithic Container (Multi-stage build)** — Build frontend, copy static assets to backend, and serve both via FastAPI's `StaticFiles` middleware in a single container.
   - Pros: Simple to deploy (only 1 container), avoids cross-origin/docker-network proxy configuration.
   - Cons: Breaks development hot-reloading (requires full rebuilds of the frontend to see changes), violates split service architecture.
   - Effort: Medium
2. **Multi-Container Architecture via Docker Compose (Recommended)** — Run frontend (`node:22-alpine`) and backend (`python:3.14-slim`) in separate containers, mapped via a shared Docker network.
   - Pros: Standard, robust approach. Preserves frontend and backend hot-reloading. Isolates backend dependencies from the frontend. Easily configured via a single `docker-compose.yml`.
   - Cons: Requires Vite proxy target to be adjusted to `http://backend:8000` (resolves to the backend service container) instead of `http://localhost:8000`.
   - Effort: Low/Medium

### Recommendation
Use **Approach 2 (Multi-Container Architecture)**. It provides a native development experience matching the production topology while preserving hot-reloading for both React and FastAPI.

Key details to implement:
- **Base Images**: Use `python:3.14-slim` for the backend to ensure a minimal but standard Debian-based environment, and `node:22-alpine` for the frontend to minimize image footprint.
- **Local Volumes for Development**:
  - For backend: Mount `./backend:/app` and mask `/app/.venv` (anonymous volume) to prevent OS-level virtual environment conflicts.
  - For frontend: Mount `./frontend:/app` and mask `/app/node_modules` (anonymous volume) to prevent local/host dependency conflicts.
- **Vite Proxy & Host Configuration**:
  - Expose Vite container to the host by setting `server.host: true` (binds to `0.0.0.0`).
  - Read target dynamically in [vite.config.ts](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/vite.config.ts):
    ```typescript
    target: process.env.VITE_API_URL || 'http://localhost:8000'
    ```
  - Set `VITE_API_URL=http://backend:8000` under the frontend service environment in `docker-compose.yml`.
- **Environment Variables**:
  - Map `env_file: ./backend/.env` directly to the backend service in `docker-compose.yml` to inject `NVIDIA_API_KEY`.

### Risks
- **Python 3.14 Package Wheels**: Python 3.14 is a very recent release. Certain scientific or data-science libraries (like `pandas` or specific `langchain` sub-dependencies) might lack pre-built wheels for the Alpine/Debian architecture on Python 3.14. This could trigger source compiles during `pip install`, requiring common build utilities (`gcc`, `g++`, `python3-dev`, etc.) to be present.
  - *Mitigation*: Ensure `backend/Dockerfile` installs `build-essential` if needed, or falls back to Python 3.13 if compilation issues persist.
- **Docker Compose Networking resolution**: The Vite dev server proxies API calls. If the backend container is named `backend`, Vite must use `http://backend:8000` as the target *inside* the Docker container. This is resolved cleanly via the dynamic environment variable fallback.

### Ready for Proposal
Yes. The orchestrator should proceed to draft the Proposal specifying the Dockerfiles, Docker Compose, and Vite configuration changes.
