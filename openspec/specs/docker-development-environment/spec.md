# Specification: Docker Development Environment

## 1. Objective and Scope
The `docker-development-environment` capability provides multi-container orchestration for the `demo-tigo` application. It standardizes the local development environment for the React frontend and FastAPI backend using containers, guaranteeing consistency across different host systems while maintaining rapid developer feedback loops.

## 2. Functional Requirements
- **Backend Service**:
  - MUST run using Python 3.14 on a minimal Linux base image.
  - MUST expose the FastAPI backend service on port `8000`.
  - MUST load `NVIDIA_API_KEY` from the configured local environment variables.
- **Frontend Service**:
  - MUST run using Node.js 22 on an Alpine Linux base image.
  - MUST expose the Vite-driven React user interface on port `5173`.
  - MUST support proxying `/api` requests dynamically based on the network environment host using `VITE_API_URL`.
- **Orchestration**:
  - MUST run both services within a shared local bridge network.
  - MUST map the host's directory structure to the container's application directories.
  - MUST mask dependencies inside containers (`/app/.venv` for backend, `/app/node_modules` for frontend) to prevent conflict with local files.
  - MUST instantly hot-reload frontend and backend code when source files are edited on the host.

## 3. Environment Configuration

| Service | Internal Port | External Port | Environment Variables | Volumes |
| :--- | :--- | :--- | :--- | :--- |
| **Backend** | `8000` | `8000` | `NVIDIA_API_KEY` | Host `./backend` mounted to `/app`, with `/app/.venv` anonymous volume |
| **Frontend** | `5173` | `5173` | `VITE_API_URL` (dynamic backend endpoint) | Host `./frontend` mounted to `/app`, with `/app/node_modules` anonymous volume |

## 4. Scenarios

### Scenario 1: Backend Container Boots and Responds
```gherkin
Given a configured environment containing "NVIDIA_API_KEY"
When the backend container is booted via Docker Compose
Then the FastAPI application MUST respond to requests on port 8000 inside the container
And the application MUST load the "NVIDIA_API_KEY" environment variable successfully
```

### Scenario 2: Frontend Container Boots and Proxies
```gherkin
Given the backend service is running on the container network
And the environment variable "VITE_API_URL" is set to "http://backend:8000"
When the frontend container is booted via Docker Compose
Then the Vite dev server MUST respond on port 5173
And requests to "/api" made to the frontend container MUST be proxied to "http://backend:8000"
```

### Scenario 3: Volume Mount Hot-Reload
```gherkin
Given the Docker containers are running with local volumes mounted
When a developer edits a source file in the local "backend" or "frontend" directory
Then the modified file content MUST be updated inside the container instantly
And the application server MUST trigger a hot-reload automatically
```
