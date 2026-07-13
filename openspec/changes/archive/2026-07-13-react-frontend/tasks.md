# React Frontend Tasks

## Review Workload Forecast
- **Decision needed before apply**: Yes
- **Chained PRs recommended**: Yes
- **Chain strategy**: feature-branch-chain
- **400-line budget risk**: High

## Suggested Work Units

| Work Unit | Scope / Description | Est. Lines |
|---|---|---|
| **Unit 1** | Backend FastAPI Foundation, server command, and `/api/preflight` endpoint. | ~150 |
| **Unit 2** | Backend API Router (`/api/chat`, `/api/report`, `/api/data`) and integration tests. | ~200 |
| **Unit 3** | Frontend setup, scaffolding Vite+React+TS, and setting up proxy configurations. | ~100 |
| **Unit 4** | Frontend UI implementation (Chat components, report viewer, integration). | ~350 |
| **Unit 5** | End-to-end verification and cleanup. | ~50 |

---

## Phase 1: Foundation / Infrastructure
- [x] **Task 1.1: Install backend dependencies**
  Add `fastapi`, `uvicorn`, and `sse-starlette` to [requirements.txt](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/requirements.txt).
- [x] **Task 1.2: Add backend server command**
  Update [main.py](file:///Users/alephzero/projects/demo-tigo/demo-tigo/backend/main.py) to support a `server` subcommand parser calling `uvicorn.run("demo.server:app")`.
- [x] **Task 1.3: Initialize FastAPI server app**
  Create `backend/demo/server.py` with the app instance, CORS middleware, and a basic `/health` route.
- [x] **Task 1.4: Scaffold frontend directory**
  Initialize a Vite project inside `frontend/` with React, TypeScript, and standard config files.
- [x] **Task 1.5: Set up frontend proxy**
  Configure Vite's dev proxy in `frontend/vite.config.ts` to redirect `/api` calls to `http://localhost:8000`.

## Phase 2: Core Implementation
- [x] **Task 2.1: Implement preflight endpoint**
  Add `GET /api/preflight` in `backend/demo/server.py` calling the preflight module and returning verification metrics.
- [x] **Task 2.2: Implement chat streaming endpoint**
  Add `POST /api/chat` using SSE (`sse-starlette`) to stream tokens (`token`, `tool`, `done` types) from LangChain Agent.
- [x] **Task 2.3: Implement report generation endpoint**
  Add `POST /api/report` to run the gross-margin report generation and return markdown text response.
- [x] **Task 2.4: Implement dataset regeneration endpoint**
  Add `POST /api/data/regenerate` to clean and rebuild the mock CSV files, returning confirmation.
- [x] **Task 2.5: Implement core frontend components**
  Create UI components in `frontend/src/components/` for `Header.tsx`, `Sidebar.tsx`, `ChatWindow.tsx`, and `ReportViewer.tsx`.

## Phase 3: Integration / Wiring
- [x] **Task 3.1: Connect frontend layout**
  Update `frontend/src/App.tsx` to mount layout, manage view state (chat vs. report), and maintain thread ID.
- [x] **Task 3.2: Wire frontend API client**
  Write fetch logic in frontend components to request preflight status, trigger report, and handle `/api/chat` stream.

## Phase 4: Testing / Verification
- [x] **Task 4.1: Write backend router tests**
  Create integration tests using `TestClient` to verify endpoints and mock data regeneration.
- [x] **Task 4.2: Write frontend unit/component tests**
  Add Vitest and React Testing Library tests verifying message inputs, status indicators, and rendering of markdown.

## Phase 5: Cleanup / Documentation
- [x] **Task 5.1: Clean up unused files and lints**
  Resolve any TypeScript or ESLint errors, clean up unused imports, and formats.
- [x] **Task 5.2: Document local setup steps**
  Add running instructions for both server and Vite UI to `README.md` and/or `frontend/README.md`.
