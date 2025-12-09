import logging
import os
from contextvars import ContextVar
from functools import lru_cache
from importlib import metadata
from typing import Any

import httpx
from dotenv import load_dotenv

from rundeck_mcp import DIST_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_TOKEN = os.getenv("RUNDECK_API_TOKEN")
RUNDECK_URL = os.getenv("RUNDECK_URL", "http://localhost:4440")
API_VERSION = int(os.getenv("RUNDECK_API_VERSION", "44"))


class RundeckClient:
    """HTTP client for the Rundeck API.

    Handles authentication, request formatting, and response parsing for
    all Rundeck API operations.
    """

    def __init__(self, api_token: str, base_url: str, api_version: int = 44):
        """Initialize the Rundeck client.

        Args:
            api_token: Rundeck API token for authentication
            base_url: Base URL of the Rundeck server (e.g., 'http://localhost:4440')
            api_version: API version to use (default: 44)
        """
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self._client = httpx.Client(
            headers={
                "X-Rundeck-Auth-Token": api_token,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
            timeout=30.0,
        )

    @property
    def user_agent(self) -> str:
        """Generate User-Agent string for API requests."""
        try:
            version = metadata.version(DIST_NAME)
        except metadata.PackageNotFoundError:
            version = "dev"
        return f"{DIST_NAME}/{version}"

    def _url(self, path: str) -> str:
        """Build full API URL for a given path."""
        # Handle paths that already include the API version
        if path.startswith("/api/"):
            return f"{self.base_url}{path}"
        # Add API version prefix
        return f"{self.base_url}/api/{self.api_version}{path}"

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request to the Rundeck API.

        Args:
            path: API endpoint path (e.g., '/project/myproject/jobs')
            params: Optional query parameters

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = self._client.get(self._url(path), params=params)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Make a POST request to the Rundeck API.

        Args:
            path: API endpoint path
            json: Request body as dictionary

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        response = self._client.post(self._url(path), json=json or {})
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


# Context variable for multi-tenancy support (remote MCP server scenarios)
ClientFactory = type[RundeckClient] | None
rundeck_client_factory: ContextVar[ClientFactory] = ContextVar("rundeck_client_factory", default=None)


@lru_cache(maxsize=1)
def _get_cached_client(api_token: str, base_url: str, api_version: int) -> RundeckClient:
    """Get a cached Rundeck client instance."""
    return RundeckClient(api_token, base_url, api_version)


def get_client() -> RundeckClient:
    """Get the Rundeck client, using cached configuration if available.

    This function returns a configured RundeckClient instance. In standard
    local MCP server mode, it uses environment variables and caches the client.
    In remote/multi-tenant scenarios, a context variable can override the
    client factory.

    Returns:
        Configured RundeckClient instance

    Raises:
        ValueError: If RUNDECK_API_TOKEN is not configured
    """
    factory = rundeck_client_factory.get(None)
    if factory is not None:
        return factory(API_TOKEN, RUNDECK_URL, API_VERSION)

    if not API_TOKEN:
        raise ValueError(
            "RUNDECK_API_TOKEN environment variable is required. "
            "Generate a token in Rundeck under User Profile > User API Tokens."
        )

    return _get_cached_client(API_TOKEN, RUNDECK_URL, API_VERSION)
