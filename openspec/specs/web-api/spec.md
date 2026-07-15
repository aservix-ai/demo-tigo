# Specification: Web API

## 1. Objective and Scope
The `web-api` capability MUST expose the core functionalities of the `demo-tigo` financial engine over HTTP. This includes chat with the AI agent, report execution, data regeneration, and preflight status verification.

## 2. Functional Requirements
- **Chat Endpoint**: MUST accept user messages and stream agent responses in real time using Server-Sent Events (SSE).
- **Report Execution**: MUST run the report narrative generation sequence and save/output the generated markdown.
- **Data Regeneration**: MUST regenerate the simulated CSV datasets deterministically.
- **Preflight Verification**: MUST execute all system checks and return the status of each check as JSON.
- **Error Handling**: All endpoints MUST return standard HTTP error status codes (e.g., 400 for bad parameters, 500 for internal errors) with a descriptive JSON payload.

## 3. Endpoints

| Method | Path | Description | Streaming / Response |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/chat` | Send a query to the agent | SSE (`text/event-stream`) streaming text chunks |
| `POST` | `/api/report` | Trigger financial report execution | JSON containing execution status and markdown report |
| `POST` | `/api/data/regenerate` | Regenerate all simulated financial CSV files | JSON confirmation message |
| `GET` | `/api/preflight` | Run pre-demo system verification checks | JSON array of check results and overall status |

## 4. Scenarios

### Scenario 1: System Preflight Checks Succeed
```gherkin
Given the NVIDIA_API_KEY environment variable is configured
And all CSV datasets are intact and consistent
When the client sends a GET request to "/api/preflight"
Then the response status code MUST be 200
And the response body MUST indicate a ready status for all checks
```

### Scenario 2: System Preflight Checks Fail
```gherkin
Given the NVIDIA_API_KEY environment variable is not configured
When the client sends a GET request to "/api/preflight"
Then the response status code MUST be 500
And the response body MUST contain the specific failure description
```

### Scenario 3: Real-Time Chat Streaming
```gherkin
Given a running chat session
When the client sends a POST request to "/api/chat" with prompt "What is the EBITDA margin?"
Then the server MUST respond with Content-Type "text/event-stream"
And each streamed chunk MUST contain partial assistant tokens or tool invocation logs
And the stream MUST end with a final completed event
```

### Scenario 4: Triggering Data Regeneration
```gherkin
Given the simulated CSV data exists in the filesystem
When the client sends a POST request to "/api/data/regenerate"
Then the server MUST delete and recreate the CSV files with seed 42
And the response status code MUST be 200
```
