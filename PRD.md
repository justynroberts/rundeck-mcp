# Product Requirements Document: Rundeck MCP Server

## Overview

A Model Context Protocol (MCP) server that provides tools to interact with Rundeck, enabling AI assistants to list jobs, run jobs with options, and retrieve execution status and logs.

This implementation follows the exact design patterns established in PagerDuty's official MCP server (`reference/pagerduty-mcp-server/`).

## Goals

- 🟢 Provide safe, read-only access to Rundeck jobs and executions by default
- 🟢 Enable job execution with options via opt-in write mode
- 🟢 Minimize tool count while maximizing utility for common use cases
- 🟢 Match the reference implementation's architecture exactly

## Use Cases

### UC1: List Available Jobs
**Actor:** User via AI assistant
**Flow:** User asks "What jobs are available in project X?" → AI calls `list_jobs` → Returns job list with names, groups, descriptions

### UC2: Get Job Details
**Actor:** User via AI assistant
**Flow:** User asks "Show me details for job Y" → AI calls `get_job` → Returns job definition including options, schedule, nodes

### UC3: Run a Job
**Actor:** User via AI assistant
**Flow:** User asks "Run the deploy job with version=1.2.3" → AI calls `run_job` with options → Returns execution ID and status

### UC4: Check Execution Status
**Actor:** User via AI assistant
**Flow:** User asks "What's the status of execution 123?" → AI calls `get_execution` → Returns status, duration, result

### UC5: Get Execution Logs
**Actor:** User via AI assistant
**Flow:** User asks "Show me the logs for execution 123" → AI calls `get_execution_output` → Returns log entries

### UC6: List Recent Executions
**Actor:** User via AI assistant
**Flow:** User asks "Show recent job runs" → AI calls `list_executions` → Returns execution history with status

## Tools Specification

### Read Tools (Safe, Non-Destructive)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_jobs` | List jobs with optional filtering | `project` (required), `group_path`, `job_filter`, `tags`, `limit` |
| `get_job` | Get job definition and metadata | `job_id` (required) |
| `list_executions` | List executions with filtering | `project`, `job_id`, `status`, `limit` |
| `get_execution` | Get execution status and details | `execution_id` (required) |
| `get_execution_output` | Get execution log output | `execution_id` (required), `last_lines`, `max_lines` |

### Write Tools (Destructive, Opt-In)

| Tool | Description | Parameters |
|------|-------------|------------|
| `run_job` | Execute a job with options | `job_id` (required), `options`, `log_level`, `as_user` |

## Architecture

### Package Structure
```
rundeck_mcp/
├── __init__.py           # Package metadata, DIST_NAME
├── __main__.py           # Entry point: main()
├── server.py             # FastMCP server, tool registration
├── client.py             # Rundeck API client wrapper
├── utils.py              # Pagination, context helpers
├── models/
│   ├── __init__.py       # Export all models
│   ├── base.py           # ListResponseModel[T], constants
│   ├── context.py        # MCPContext
│   ├── jobs.py           # Job, JobQuery
│   └── executions.py     # Execution, ExecutionQuery, ExecutionOutput
└── tools/
    ├── __init__.py       # read_tools, write_tools lists
    ├── jobs.py           # list_jobs, get_job
    └── executions.py     # list_executions, get_execution, get_execution_output, run_job
```

### Configuration

**Environment Variables:**
| Variable | Description | Default |
|----------|-------------|---------|
| `RUNDECK_API_TOKEN` | API token for authentication | (required) |
| `RUNDECK_URL` | Rundeck server URL | `http://localhost:4440` |
| `RUNDECK_API_VERSION` | API version number | `44` |

**CLI Flags:**
| Flag | Description |
|------|-------------|
| `--enable-write-tools` | Enable job execution tools |

### Safety Annotations

Read tools:
```python
ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
```

Write tools:
```python
ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False)
```

### Server Instructions
```
When the user asks about Rundeck jobs or executions, use the available tools to query
the Rundeck API.

READ operations are safe to use. WRITE operations (run_job) can trigger actual job
executions in your environment. Always confirm with the user before running jobs,
especially in production environments.
```

## Data Models

### Job
```python
class Job(BaseModel):
    id: str
    name: str
    group: str | None
    project: str
    description: str | None
    scheduled: bool
    enabled: bool
    average_duration: int | None  # milliseconds
```

### JobQuery
```python
class JobQuery(BaseModel):
    project: str = Field(description="Project name (required)")
    group_path: str | None = Field(description="Filter by group path")
    job_filter: str | None = Field(description="Filter by job name")
    tags: str | None = Field(description="Filter by tags")
    limit: int = Field(default=100, ge=1, le=1000)
```

### Execution
```python
class Execution(BaseModel):
    id: int
    status: Literal["running", "succeeded", "failed", "aborted", "timedout"]
    project: str
    job: JobReference | None
    user: str
    date_started: datetime
    date_ended: datetime | None
    duration: int | None  # milliseconds
    argstring: str | None
```

### ExecutionOutput
```python
class ExecutionOutput(BaseModel):
    id: int
    completed: bool
    exec_duration: int
    percent_loaded: float
    entries: list[LogEntry]
```

### LogEntry
```python
class LogEntry(BaseModel):
    time: datetime
    level: str
    log: str
    node: str | None
    step: str | None
```

## API Mapping

| Tool | Rundeck API Endpoint |
|------|---------------------|
| `list_jobs` | `GET /api/{version}/project/{project}/jobs` |
| `get_job` | `GET /api/{version}/job/{id}` |
| `list_executions` | `GET /api/{version}/project/{project}/executions` or `GET /api/{version}/job/{id}/executions` |
| `get_execution` | `GET /api/{version}/execution/{id}` |
| `get_execution_output` | `GET /api/{version}/execution/{id}/output` |
| `run_job` | `POST /api/{version}/job/{id}/run` |

## Dependencies

```toml
[project]
requires-python = "~=3.12.0"
dependencies = [
    "mcp[cli]~=1.8",
    "httpx~=0.28",
    "typer~=0.16.0",
]
```

Note: No official Rundeck Python SDK exists with the quality of `pagerduty~=5.3`, so we use `httpx` for HTTP requests.

## Client Integration Examples

### Claude Desktop
```json
{
  "mcpServers": {
    "rundeck-mcp": {
      "command": "uvx",
      "args": ["rundeck-mcp", "--enable-write-tools"],
      "env": {
        "RUNDECK_API_TOKEN": "your-api-token",
        "RUNDECK_URL": "https://rundeck.example.com"
      }
    }
  }
}
```

### VS Code
```json
{
  "mcp": {
    "inputs": [
      {
        "type": "promptString",
        "id": "rundeck-api-token",
        "description": "Rundeck API Token",
        "password": true
      }
    ],
    "servers": {
      "rundeck-mcp": {
        "type": "stdio",
        "command": "uvx",
        "args": ["rundeck-mcp", "--enable-write-tools"],
        "env": {
          "RUNDECK_API_TOKEN": "${input:rundeck-api-token}",
          "RUNDECK_URL": "https://rundeck.example.com"
        }
      }
    }
  }
}
```

## Testing Strategy

- Unit tests mirror tool structure: `tests/test_jobs.py`, `tests/test_executions.py`
- Mock HTTP responses using `httpx` mock transport
- Test both success and error cases
- Validate Pydantic model parsing

## Success Criteria

- 🟢 All 6 tools implemented and functional
- 🟢 Write tools disabled by default
- 🟢 Code structure matches reference implementation
- 🟢 Unit tests pass with >80% coverage on tools
- 🟢 Works with Claude Desktop, VS Code, and Cursor

## References

- [Rundeck API Documentation](https://docs.rundeck.com/docs/api/)
- Reference implementation: `reference/pagerduty-mcp-server/`
