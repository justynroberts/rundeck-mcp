# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains the **Rundeck MCP Server** - an MCP (Model Context Protocol) server that provides tools to interact with Rundeck for listing jobs, running jobs with options, and retrieving execution status and logs.

The `reference/pagerduty-mcp-server/` directory contains PagerDuty's official MCP server which was used as the reference implementation.

## Architecture

```
rundeck_mcp/
├── __init__.py           # Package metadata (DIST_NAME)
├── __main__.py           # Entry point: main()
├── server.py             # FastMCP server, tool registration with safety annotations
├── client.py             # Rundeck API client (httpx-based)
├── utils.py              # Option validation, context helpers
├── models/
│   ├── __init__.py       # Export all models
│   ├── base.py           # ListResponseModel[T], pagination constants
│   ├── context.py        # MCPContext
│   ├── jobs.py           # Job, JobOption, JobQuery, JobRunRequest
│   └── executions.py     # Execution, ExecutionOutput, ExecutionQuery, LogEntry
└── tools/
    ├── __init__.py       # read_tools, write_tools lists
    ├── jobs.py           # list_jobs, get_job, run_job
    └── executions.py     # list_executions, get_execution, get_execution_output
```

Key patterns:
- Write tools (`run_job`) disabled by default, enabled with `--enable-write-tools`
- Tools use `ToolAnnotations` to mark `readOnlyHint`, `destructiveHint`, `idempotentHint`
- Job options are validated before execution (required options, allowed values)
- Pydantic models validate all inputs/outputs with Google-style docstrings

## Development Commands

```bash
# Install dependencies
uv sync                           # production deps
uv sync --group dev               # with dev deps (pytest, ruff, coverage)

# Run tests
make test                         # all unit tests
uv run python -m pytest tests/ -v
uv run python -m pytest tests/test_jobs.py -v  # single file

# Linting and formatting
make lint                         # ruff check
make format                       # ruff format

# Coverage
make test-coverage                # with coverage report
make test-html-coverage           # HTML report in htmlcov/

# Run MCP server locally
uv run python -m rundeck_mcp --enable-write-tools

# Debug with MCP inspector
make debug
```

## Configuration

Environment variables:
- `RUNDECK_API_TOKEN` - API token (required)
- `RUNDECK_URL` - Server URL (default: `http://localhost:4440`)
- `RUNDECK_API_VERSION` - API version (default: `44`)

## Tech Stack

- Python 3.12 (managed via asdf)
- uv for package management
- FastMCP (`mcp[cli]~=1.8`) for MCP server
- httpx for HTTP requests
- Pydantic for data validation
- Typer for CLI
- pytest for testing
- ruff for linting/formatting (line-length 120, Google docstring convention)

## Commit Conventions

This project uses conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, etc. Keep titles lowercase with no period at end.
