# Tigo — React Frontend Application

This folder contains the frontend application for the Tigo Financial Analysis AI Agent. Built with **React 19**, **TypeScript**, and **Vite**, it provides a sleek, interactive dual-pane user interface.

---

## Features

- **Dual-Pane Layout**: An interactive chat window on the left and a dedicated report viewer on the right.
- **Preflight Verification Indicator**: Header displays real-time backend preflight status check.
- **SSE Streaming Support**: Receives tokens and tool call indicators in real-time from the agent.
- **Interactive Financial Alarms**: Visualized severity-colored alarm lists linked to detailed telemetry.
- **Robust Markdown Rendering**: Custom markdown parsing component featuring syntax highlight and tables.

---

## Local Setup & Development

### 1. Install Dependencies
```bash
npm install
```

### 2. Start the Vite Dev Server
```bash
npm run dev
```
Starts the development server at `http://localhost:5173`.

### 3. Build for Production
```bash
npm run build
```
This runs TypeScript compiler checks (`tsc -b`) and bundles the static assets using Vite (`vite build`) to `dist/`.

---

## Available Commands

- `npm run dev`: Starts the development server.
- `npm run build`: Type-checks and builds the production-ready bundle.
- `npm run lint`: Fast linting with `oxlint`.
- `npm run test`: Runs unit tests with Vitest.
- `npx tsc -b`: Performs static type checking across the project.

---

## API Proxy Configuration

Vite is configured with a development proxy in `vite.config.ts`. Any requests starting with `/api` are automatically proxied to `http://localhost:8000` (the FastAPI server's default port):

```ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

---

## Key Components

- **`App.tsx`**: Main entry and application layout. Manages global view state (tabs, thread ID, and active report context).
- **`components/Header.tsx`**: Renders the top header bar and checks `/api/preflight` to report server readiness.
- **`components/Sidebar.tsx`**: Navigation menu sidebar.
- **`components/ChatWindow.tsx`**: Manages the message thread state and processes the Server-Sent Events (SSE) chat stream.
- **`components/ReportViewer.tsx`**: Invokes `/api/report` to fetch or regenerate the gross-margin report, displaying the report markdown and alarms list.
- **`components/Markdown.tsx`**: A component to safely and nicely format markdown content, supporting standard elements like lists, tables, headers, and code blocks.
