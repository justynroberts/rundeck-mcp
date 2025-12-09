from pydantic import BaseModel


class MCPContext(BaseModel):
    """MCP server context containing connection information.

    This context is created during server startup and made available to tools
    via the lifespan context manager.
    """

    server_url: str
    api_version: int
