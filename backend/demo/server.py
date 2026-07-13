import contextlib
import json
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.globals import set_debug
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from demo.agent import REPORT_REQUEST, build_agent
from demo.config import DATA_DIR
from demo.datagen import generate
from demo.preflight import CHECKS

# Enable LangChain verbose debugging to print model responses in the console
set_debug(True)

app = FastAPI(title="Demo Tigo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



_agent_container: dict[str, Any] = {}


def get_agent():
    if "agent" not in _agent_container:
        _agent_container["agent"] = build_agent()
    return _agent_container["agent"]


class ChatRequest(BaseModel):
    prompt: str | None = None
    message: str | None = None
    thread_id: str = "demo"


async def event_generator(prompt: str, thread_id: str, agent) -> AsyncGenerator[dict]:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        async for mode, data in agent.astream(
            {"messages": [{"role": "user", "content": prompt}]},
            config,
            stream_mode=["updates", "messages"],
        ):
            if mode == "messages":
                token, _meta = data
                if isinstance(token, AIMessageChunk) and token.text:
                    print(token.text, end="", flush=True)
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "token", "content": token.text}),
                    }
            elif mode == "updates":
                for _node, update in (data or {}).items():
                    for msg in (update or {}).get("messages", []):
                        for tc in getattr(msg, "tool_calls", None) or []:
                            print(f"\n[Tool] {tc['name']}({tc['args']})\n", flush=True)
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "tool",
                                    "name": tc["name"],
                                    "args": tc["args"],
                                    "content": "",
                                }),
                            }
    except Exception as e:
        print(f"\n[Error in event generator] {e}\n", flush=True)
        yield {
            "event": "message",
            "data": json.dumps({"type": "error", "content": str(e)}),
        }
    finally:
        print("\n[Stream finished]\n", flush=True)
        yield {
            "event": "message",
            "data": json.dumps({"type": "done", "content": ""}),
        }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/preflight")
def get_preflight():
    results = []
    all_passed = True
    first_error = None

    for name, check_fn in CHECKS:
        try:
            error = check_fn()
        except Exception as e:
            error = f"Exception in check: {e}"

        if error:
            all_passed = False
            if first_error is None:
                first_error = error
            results.append(
                {
                    "name": name,
                    "passed": False,
                    "error": error,
                }
            )
        else:
            results.append(
                {
                    "name": name,
                    "passed": True,
                    "error": None,
                }
            )

    if not all_passed:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "ready": False,
                "error": first_error,
                "checks": results,
            },
        )

    return {
        "status": "success",
        "ready": True,
        "checks": results,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.prompt or request.message
    if not query:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "Prompt or message is required"},
        )

    if "NVIDIA_API_KEY" not in os.environ:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "NVIDIA_API_KEY environment variable is not configured.",
            },
        )

    try:
        agent = get_agent()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": f"Failed to initialize agent: {e}"},
        )

    return EventSourceResponse(event_generator(query, request.thread_id, agent))


@app.post("/api/report")
async def generate_report():
    if "NVIDIA_API_KEY" not in os.environ:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "NVIDIA_API_KEY environment variable is not configured.",
            },
        )

    try:
        agent = get_agent()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": f"Failed to initialize agent: {e}"},
        )

    try:
        thread_id = f"report-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": REPORT_REQUEST}]}, config
        )

        final_msg = result["messages"][-1]

        report_content = ""
        if hasattr(final_msg, "content"):
            content = final_msg.content
            if isinstance(content, str):
                report_content = content
            elif isinstance(content, list):
                report_content = "".join(
                    b.get("text", "") for b in content if isinstance(b, dict)
                )

        return {"status": "success", "report": report_content}

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})


@app.post("/api/data/regenerate")
def regenerate_data():
    try:
        if DATA_DIR.exists():
            for f in DATA_DIR.glob("*.csv"):
                with contextlib.suppress(Exception):
                    os.remove(f)
        generate(verbose=False)
        return {"status": "success", "message": "Dataset regenerated successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})
