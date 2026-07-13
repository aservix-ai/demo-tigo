# Design: docker-setup

## Technical Approach
We will containerize the `demo-tigo` application using a multi-container Docker setup. The application consists of a FastAPI backend (running on Python 3.14) and a React frontend (built with Vite and Node.js 22). Both containers will run within a shared Docker bridge network, mapping host filesystems to the containers for hot-reloading while isolating node/python environment binaries.

---

## Architecture Decisions

1. **Backend Base Image: `python:3.14-slim`**
   - **Rationale:** Python 3.14 is a modern release, which may lack pre-built wheels for certain libraries on Linux. Using `-slim` minimizes the base size, but we must install development tools (`build-essential`, `curl`) to ensure source-compilation of dependencies behaves correctly.
2. **Frontend Base Image: `node:22-alpine`**
   - **Rationale:** Minimizes the image footprint for Node/Vite web serving.
3. **Volume Isolation:**
   - **Rationale:** To avoid conflicts between host-compiled virtual environment/node dependencies and container environments, we use anonymous volumes (`/app/.venv` for backend, `/app/node_modules` for frontend) to mask host dependencies.
4. **Dynamic API Routing:**
   - **Rationale:** Vite dev server proxies requests from the browser to the backend. We make the API proxy target dynamic by using `process.env.VITE_API_URL` to route requests to the backend container (`http://backend:8000`).

---

## Data Flow

```mermaid
graph TD
    subgraph Host Machine
        Browser["Browser (Port 5173)"]
        FS_FE["frontend/ (Host Directory)"]
        FS_BE["backend/ (Host Directory)"]
    end

    subgraph Docker Bridge Network (demo-network)
        FE["frontend service (node:22-alpine)"]
        BE["backend service (python:3.14-slim)"]
    end

    Browser -- "HTTP Requests (Port 5173)" --> FE
    Browser -- "HTTP/API Requests (Port 8000)" --> BE
    FE -- "Proxy /api requests to VITE_API_URL" --> BE
    FS_FE -- "Mounted to /app" --> FE
    FS_BE -- "Mounted to /app" --> BE
```

---

## File Changes

### 1. `backend/Dockerfile` (new)
```dockerfile
FROM python:3.14-slim

WORKDIR /app

# Install compilation tools to support Python 3.14 source builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py", "server", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 2. `frontend/Dockerfile` (new)
```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
```

### 3. `docker-compose.yml` (new)
```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - /app/.venv
    env_file:
      - ./backend/.env
    networks:
      - demo-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://backend:8000
    networks:
      - demo-network
    depends_on:
      - backend

networks:
  demo-network:
     driver: bridge
```

### 4. `frontend/vite.config.ts` (modified)
Modify the config to read from `process.env` and enable network bindings and polling.
```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Bind to 0.0.0.0
    watch: {
      usePolling: true, // Needed for consistent reloading inside containers
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
```

---

## Interfaces / Contracts
- **Vite Proxy Routing:** Any request made by the client to the relative path `/api/*` is proxied by the frontend development server to the address specified in the `VITE_API_URL` environment variable.
- **Service Ports:** Backend listens on port 8000; Frontend listens on port 5173.

---

## Testing Strategy
1. **Verification of compilation:** Run `docker compose build` to verify backend libraries compile correctly under Python 3.14-slim with the installed OS package dependencies.
2. **Container lifecycle validation:** Execute `docker compose up -d` to verify both services reach the running state.
3. **Connectivity validation:** Curl `http://localhost:5173/api/docs` or other API endpoints through the frontend proxy to ensure route resolution.
4. **Hot-Reload testing:** Update a string in a frontend component or backend file and verify live reloading.
5. **Consistency Suit:** Run `docker compose exec backend python3 main.py preflight` to confirm full CLI verification passes inside Docker.

---

## Migration / Rollout
No database migration is required. Developers will only need to configure `./backend/.env` with `NVIDIA_API_KEY`, install Docker on their host machines, and execute `docker compose up`.

---

## Open Questions
- None.
