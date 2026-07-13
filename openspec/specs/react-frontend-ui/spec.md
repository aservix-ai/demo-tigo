# Specification: React Frontend UI

## 1. Objective and Scope
The `react-frontend-ui` capability provides an interactive, responsive Single Page Application (SPA) for interacting with the `demo-tigo` web API. It enables users to chat with the finance agent, trigger reports, and inspect preflight check status.

## 2. Functional Requirements
- **Chat Interface**:
  - MUST allow users to input natural language questions.
  - MUST display chat messages in a conversation history log.
  - MUST stream the agent's responses in real-time token-by-token.
  - SHOULD display active tool-calling indicators while the backend invokes tools.
- **Report Executive view**:
  - MUST allow users to trigger a full gross-margin report generation.
  - MUST show an active loading state while the report is executing.
  - MUST render the final report narrative in formatted markdown once completed.
- **Preflight and System Status**:
  - MUST display the overall system readiness status (Ready / Not Ready).
  - MUST list the individual status of all preflight checks returned by the backend.
  - SHOULD provide a button to trigger data regeneration.

## 3. UI Components Layout

| Component | Purpose | User Actions |
| :--- | :--- | :--- |
| **System Status Header** | Display overall readiness and API connectivity | Click "Run Preflight Check" or "Regenerate Data" |
| **Q&A Chat Pane** | Interactive messaging area for financial questions | Input a query, submit query, view streamed answers |
| **Report Dashboard** | Display generated markdown report and KPIs | Click "Generate June 2026 Report", view loading spinner |

## 4. Scenarios

### Scenario 1: Streaming Chat Responses
```gherkin
Given the user is on the Q&A Chat page
When the user types "Show me direct costs for Bolivia" and clicks Send
Then the input field MUST be cleared and disabled
And a user message bubble MUST appear in the chat log
And a typing indicator MUST be displayed
And as the server streams chunks, the assistant message bubble MUST update dynamically
And the send button MUST be re-enabled once the stream completes
```

### Scenario 2: Executing a Financial Report
```gherkin
Given the user is on the Report Dashboard
When the user clicks the "Generate June 2026 Report" button
Then the button MUST enter a loading state
And the dashboard MUST show a progress spinner and message "Running report tools..."
And when the backend returns the completed report, the spinner MUST disappear
And the generated markdown report MUST be rendered on the screen
```

### Scenario 3: Viewing Preflight Failures
```gherkin
Given the frontend application loads
When the preflight API check returns an error state
Then the System Status Header MUST display a "System Not Ready" warning in red
And the user MUST see a list of failing check descriptions
And chat inputs MUST be disabled
```
