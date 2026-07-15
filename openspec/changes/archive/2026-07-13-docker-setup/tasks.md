# Tasks: docker-setup

## Review Workload Forecast
- Decision needed before apply: No
- Chained PRs recommended: No
- Chain strategy: size-exception
- 400-line budget risk: Low

## Suggested Work Units
| Task ID | Description | Est. Lines |
|---|---|---|
| Task 1 | Create backend/Dockerfile | ~15 |
| Task 2 | Create frontend/Dockerfile | ~10 |
| Task 3 | Create docker-compose.yml | ~35 |
| Task 4 | Modify frontend/vite.config.ts | ~10 |
| Task 5 | Verify the setup | N/A |

---

## Phase 1: Foundation / Infrastructure
- [x] **Task 1: Create backend/Dockerfile**
  - Create [backend/Dockerfile](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/Dockerfile) with Python 3.14-slim, build tools, requirements installation, and uvicorn command.
- [x] **Task 2: Create frontend/Dockerfile**
  - Create [frontend/Dockerfile](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/Dockerfile) with Node 22-alpine, install packages, and set CMD to npm run dev.

## Phase 2: Core Implementation
- [x] **Task 3: Create docker-compose.yml at the root**
  - Create [docker-compose.yml](file:///Users/alephzero/projects/demo-tigo/demo-tigo/docker-compose.yml) at the root containing both services, mounts, env configuration, and network settings.

## Phase 3: Integration / Wiring
- [x] **Task 4: Modify frontend/vite.config.ts**
  - Update [frontend/vite.config.ts](file:///Users/alephzero/projects/demo-tigo/demo-tigo/frontend/vite.config.ts) to set host binding, enable watch polling, and proxy request target using VITE_API_URL.

## Phase 4: Testing / Verification
- [x] **Task 5: Verify the setup**
  - Build and start services using docker compose, then verify the environment by running the preflight script inside the backend container.

## Phase 5: Cleanup / Documentation
- [x] **Verify documentation and clean temporary artifacts**
  - Confirm the container builds are fully documented and readmes updated if needed.
