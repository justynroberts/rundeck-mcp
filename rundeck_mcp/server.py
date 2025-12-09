import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import typer
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from rundeck_mcp.models import MCPContext
from rundeck_mcp.tools import read_tools, write_tools
from rundeck_mcp.utils import get_mcp_context

logging.basicConfig(level=logging.WARNING)


app = typer.Typer()

MCP_SERVER_INSTRUCTIONS = """
When the user asks about Rundeck jobs or executions, use the available tools to query
the Rundeck API.

CRITICAL: When listing jobs, you MUST display the numbered markdown table exactly as
returned by list_jobs. Do NOT summarize or reorganize the results. The user needs to
see the exact table with job numbers (# column) so they can reference jobs by number
(e.g., "run job 3"). Always show the full table first, then add any commentary after.

When running a job with options:
1. First use get_job to retrieve the job definition and see available options
2. Review the options_summary field to understand required options and allowed values
3. Provide all required options that don't have defaults
4. For options with allowed values (enforced=true), use only values from the list

READ operations are safe to use. WRITE operations (run_job) can trigger actual job
executions in your environment. Always confirm with the user before running jobs,
especially in production environments.
"""


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[MCPContext]:
    """Lifespan context manager for the MCP server.

    Initializes the Rundeck client and creates the context that will be
    available to all tools during the server's lifetime.

    Args:
        server: The MCP server instance

    Yields:
        MCPContext with server configuration
    """
    try:
        yield get_mcp_context()
    finally:
        pass


def add_read_only_tool(mcp_instance: FastMCP, tool: Callable) -> None:
    """Add a read-only tool with appropriate safety annotations.

    Read-only tools are marked as safe (non-destructive) and idempotent,
    meaning they can be called multiple times without side effects.

    Args:
        mcp_instance: The MCP server instance
        tool: The tool function to add
    """
    mcp_instance.add_tool(
        tool,
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    )


def add_write_tool(mcp_instance: FastMCP, tool: Callable) -> None:
    """Add a write tool with appropriate safety annotations.

    Write tools are marked as potentially destructive and non-idempotent,
    indicating they can modify state and may have different effects on
    repeated calls.

    Args:
        mcp_instance: The MCP server instance
        tool: The tool function to add
    """
    mcp_instance.add_tool(
        tool,
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False),
    )


@app.command()
def run(*, enable_write_tools: bool = False) -> None:
    """Run the Rundeck MCP server.

    Starts the MCP server with read-only tools enabled by default.
    Use --enable-write-tools to also enable job execution capabilities.

    Args:
        enable_write_tools: Flag to enable write tools (job execution)
    """
    mcp = FastMCP(
        "Rundeck MCP Server",
        lifespan=app_lifespan,
        instructions=MCP_SERVER_INSTRUCTIONS,
    )

    # Register read-only tools (always available)
    for tool in read_tools:
        add_read_only_tool(mcp, tool)

    # Register write tools only if explicitly enabled
    if enable_write_tools:
        for tool in write_tools:
            add_write_tool(mcp, tool)

    mcp.run()
