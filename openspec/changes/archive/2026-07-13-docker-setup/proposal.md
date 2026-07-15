# Proposal: docker-setup

## Intent
Dockerize the project for consistent running across any machine.

## Scope
### In Scope
- Containerizing backend (`python:3.14-slim`).
- Containerizing frontend (`node:22-alpine`).
- Docker Compose setup (`docker-compose.yml`) for multi-container orchestration.
- Adapting Vite configuration (`frontend/vite.config.ts`) to handle dynamic API URL and bind to host.

### Out of Scope
- Production Kubernetes configs or Helm charts.
- CI/CD container build/deployment workflows.

## Capabilities
### New Capabilities
- `docker-development-environment`: Docker Compose orchestration for running frontend and backend in isolated containers.

### Modified Capabilities
None.

## Approach
Implement a multi-container setup via Docker Compose using a shared Docker bridge network:
1. **Backend**: Build via Dockerfile (`python:3.14-slim`), mapping `backend/.env` environment variables (e.g. `NVIDIA_API_KEY`), and mounting `./backend:/app` for hot-reloading with `/app/.venv` volume masking.
2. **Frontend**: Build via Dockerfile (`node:22-alpine`), exposing port `5173`, mounting `./frontend:/app` for hot-reloading with `/app/node_modules` volume masking.
3. **Routing**: Configure Vite proxy dynamically to target `http://backend:8000` via `VITE_API_URL` when in Docker environment.

## Affected Areas
- [backend/Dockerfile](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/Dockerfile) (new)
- [frontend/Dockerfile](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/Dockerfile) (new)
- [docker-compose.yml](file:///Users/alephzero/projects/demo-tigo/demo-tigo/docker-compose.yml) (new)
- [frontend/vite.config.ts](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/vite.config.ts) (modified)
- [backend/.env](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/.env) (input dependency)

## Risks
- **Python 3.14 Package Wheels**: Potential dependency compilation issues due to lack of pre-built wheels for Python 3.14.
  - *Mitigation*: Fallback to Python 3.13 if necessary or install `build-essential` in the backend container.
- **Service Resolution**: Vite proxy must resolve the backend container name within the bridge network.
  - *Mitigation*: Use environment variable `VITE_API_URL=http://backend:8000` in Compose configuration.

## Rollback Plan
Run the following commands:
```bash
rm -f backend/Dockerfile frontend/Dockerfile docker-compose.yml
git checkout -- frontend/vite.config.ts
```

## Dependencies
- Docker and Docker Compose installed on host machine.
- Valid `backend/.env` file containing configuration like `NVIDIA_API_KEY`.

## Success Criteria
- Running `docker compose up` successfully boots frontend and backend containers.
- Local volume mounts support hot-reloading on host file changes.
- Frontend container successfully proxies `/api` requests to backend container.
- Verification checks pass when `NVIDIA_API_KEY` is configured.
