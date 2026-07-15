# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A rehearsed sales demo for a Tigo (Millicom) VP: an FP&A AI agent that analyzes OPEX/CAPEX/revenue for 5 LatAm markets and produces a gross-margin report with alarm detection. Two apps: a Python FastAPI backend wrapping a LangChain agent (`backend/`), and a Vite + React 19 + TypeScript SPA (`frontend/`).

**Core design principle:** every figure is computed by deterministic pandas code and every alarm fires from an auditable Python rule. The LLM only narrates and answers follow-ups — it never does arithmetic. The dataset is generated with a fixed seed (42) and committed, so the demo shows the **same 9 alarms on every run**.

**The 9-alarm manifest is sacred.** `config.EXPECTED_ALARMS` (backend/demo/config.py) lists the exact alarm ids the demo is rehearsed against, and `preflight` asserts `alarms.scan()` produces exactly that set. Any change to `datagen.py`, thresholds, or alarm rules must keep preflight green — or the README run-of-show and rehearsal fallback must be updated together with it. After touching `datagen.py`, run `python main.py data` then `git diff data/` to prove the CSVs are byte-identical.

**Language split:** the report, alarms, agent prompts, and all user-facing strings are in Spanish (deliberate); code, comments, and docs are in English.

## Commands

### Backend (run from `backend/`)

The venv's script shebangs are broken (`.venv/bin/pip` points at a deleted path) — always go through `.venv/bin/python`:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py preflight          # pre-demo verification — must print "READY FOR DEMO"
.venv/bin/python main.py server --reload    # FastAPI dev server on :8000
.venv/bin/python main.py report --chat      # the demo command (dashboard → streamed report → alarms → Q&A)
.venv/bin/python main.py chat               # interactive Q&A only
.venv/bin/python main.py data               # regenerate CSVs (deterministic, seed=42)
.venv/bin/ruff check .                      # lint (config: ruff.toml, line-length 100)
.venv/bin/ruff format .                     # format
.venv/bin/mypy main.py demo/                # type check
```

Tests: `demo/test_server.py` uses pytest with mocked agents, but pytest is not in requirements.txt or the venv — install first (`.venv/bin/python -m pip install pytest httpx`), then `.venv/bin/python -m pytest`.

`preflight` is the primary verification gate for backend changes (data integrity, financial tie-outs, exact alarm manifest, tool serializability, live LLM ping). Requires `NVIDIA_API_KEY` in `backend/.env` (copy `.env.example`); the key check and LLM ping are the only checks that need it.

ruff.toml deliberately omits PLC0415 (main.py lazy-imports heavy deps so `--help` stays instant), T20 (CLI prints by design), and PLR2004 — don't "fix" those patterns.

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev        # Vite dev server on :5173, proxies /api → http://localhost:8000
npm run test       # vitest run
npx vitest run src/components/ChatWindow.test.tsx   # single test file
npm run lint       # oxlint
npm run build      # tsc -b && vite build
npx tsc -b         # type-check only
```

### Docker

`docker compose up --build` runs both services with bind mounts for live reload; frontend proxies to the backend via `VITE_API_URL=http://backend:8000`.

## Architecture

### Backend data flow

```
data/*.csv ──► demo/finance.py ──► demo/alarms.py ──► 9 alarms (pydantic)
(committed,     (pandas: P&L,        (deterministic
 seeded)         margins, DSO...)     FP&A rules A1–A9)
                      │                    │
                      ▼                    ▼
                demo/tools.py   ◄── the LLM only sees tool outputs
                      │
                demo/agent.py   LangChain create_agent + ChatNVIDIA
                      │
        ┌─────────────┴─────────────┐
  demo/display.py             demo/server.py
  (rich CLI: dashboard,       (FastAPI: SSE chat,
   streaming, panels)          report, preflight)
```

- `demo/config.py` is the single source of truth: paths, seed, business scale (Millicom-anchored revenue per market), alarm thresholds, model id, and `EXPECTED_ALARMS`.
- `demo/tools.py` wraps the finance/alarm engines as LangChain tools. Tools return compact JSON dicts with amounts pre-converted to USD millions (`*_musd` fields) so the model can quote figures verbatim. Free-form LLM inputs (country/segment names, accents) are normalized via `_canon`; unknown values return a structured error payload listing valid options rather than raising.
- `demo/agent.py` builds the agent: `create_agent()` with an `InMemorySaver` checkpointer (conversation memory keyed by `thread_id`), model `nvidia/nemotron-3-ultra-550b-a55b` via `ChatNVIDIA` with reasoning enabled. The system prompt enforces Spanish output, the exact report section structure, the tool-call order for the full report, and the no-arithmetic rule.
- `demo/server.py` holds a lazily-built singleton agent. `/api/chat` streams SSE events — JSON payloads of `type: "token" | "tool" | "error" | "done"` — from `agent.astream(stream_mode=["updates", "messages"])`; the same `thread_id` continues a conversation. `/api/report` runs the canonical report prompt on a fresh thread and returns the full markdown. `/health`, `/api/preflight`, and `/api/data/regenerate` are the operational endpoints.
- Alarm panels in the CLI render from the Python rule engine even if the LLM call fails — degradation paths matter here (this runs live in front of a customer).

### Frontend

- `App.tsx` owns all cross-cutting state: preflight status (polled every 15s; failed checks put the UI in degraded mode and disable chat/report), the `thread_id` for the chat session, messages, and report text. Chat vs Report is a tab switch (`Sidebar`), each rendered by `ChatWindow` / `ReportViewer`.
- `ChatWindow` streams from POST `/api/chat` by hand: it reads the fetch `ReadableStream` and parses SSE frames itself (splitting on `\r?\n\r?\n` — tolerant of CRLF line endings), appending tokens and tool-call chips to the last assistant message.
- API calls use relative `/api/...` paths; the Vite dev proxy (vite.config.ts) forwards them to `VITE_API_URL` or `http://localhost:8000`.

### openspec/

Spec-driven change workflow: `openspec/specs/` holds current capability specs, `openspec/changes/archive/` holds completed change proposals/designs/verify-reports. Per `openspec/config.yaml`, the verification command for changes is `python3 main.py preflight` (no coverage tooling).
