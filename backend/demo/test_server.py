import json
import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk

from demo.server import app

client = TestClient(app)


class MockToolCallMessage:
    def __init__(self, name, args):
        self.tool_calls = [{"name": name, "args": args}]


class MockFinalMessage:
    def __init__(self, content):
        self.content = content


class MockAgent:
    async def astream(self, inputs, config, stream_mode):
        yield "updates", {
            "tools": {
                "messages": [MockToolCallMessage("get_pnl_summary", {"country": "Guatemala"})]
            }
        }
        yield "messages", (AIMessageChunk(content="Hola"), None)
        yield "messages", (AIMessageChunk(content=" Mundo"), None)

    async def ainvoke(self, inputs, config):
        return {
            "messages": [MockFinalMessage("Informe de prueba en markdown")]
        }


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_preflight_success():
    mock_checks = [
        ("Check 1", lambda: None),
        ("Check 2", lambda: None),
    ]
    with patch("demo.server.CHECKS", mock_checks):
        response = client.get("/api/preflight")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ready"] is True
        assert len(data["checks"]) == 2
        assert data["checks"][0]["passed"] is True


def test_get_preflight_failure():
    mock_checks = [
        ("Check 1", lambda: "Failed check 1"),
        ("Check 2", lambda: None),
    ]
    with patch("demo.server.CHECKS", mock_checks):
        response = client.get("/api/preflight")
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert data["ready"] is False
        assert data["error"] == "Failed check 1"
        assert len(data["checks"]) == 2
        assert data["checks"][0]["passed"] is False
        assert data["checks"][1]["passed"] is True


def test_chat_missing_prompt():
    response = client.post("/api/chat", json={})
    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_chat_missing_api_key():
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/api/chat", json={"prompt": "Hola"})
        assert response.status_code == 500
        assert "NVIDIA_API_KEY" in response.json()["error"]


@patch("demo.server.get_agent")
def test_chat_success(mock_get_agent):
    mock_get_agent.return_value = MockAgent()
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
        response = client.post("/api/chat", json={"prompt": "Hola"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Read the stream content line by line
        lines = list(response.iter_lines())
        # Filter for data: prefixes
        data_lines = [line for line in lines if line.startswith("data: ")]
        payloads = [json.loads(line[6:]) for line in data_lines]

        # We expect a tool call, a token, another token, and a done
        assert len(payloads) == 4
        assert payloads[0]["type"] == "tool"
        assert payloads[0]["name"] == "get_pnl_summary"
        assert payloads[0]["args"] == {"country": "Guatemala"}
        assert payloads[1]["type"] == "token"
        assert payloads[1]["content"] == "Hola"
        assert payloads[2]["type"] == "token"
        assert payloads[2]["content"] == " Mundo"
        assert payloads[3]["type"] == "done"


def test_report_missing_api_key():
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/api/report")
        assert response.status_code == 500
        assert "NVIDIA_API_KEY" in response.json()["error"]


@patch("demo.server.get_agent")
def test_report_success(mock_get_agent):
    mock_get_agent.return_value = MockAgent()
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}):
        response = client.post("/api/report")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["report"] == "Informe de prueba en markdown"


@patch("demo.server.generate")
@patch("demo.server.DATA_DIR")
def test_regenerate_data_success(mock_data_dir, mock_generate):
    mock_data_dir.exists.return_value = True
    mock_csv_file = MagicMock()
    mock_data_dir.glob.return_value = [mock_csv_file]

    with patch("os.remove") as mock_remove:
        response = client.post("/api/data/regenerate")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_remove.assert_called_once_with(mock_csv_file)
        mock_generate.assert_called_once_with(verbose=False)
