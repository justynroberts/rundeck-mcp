from rundeck_mcp.server import app


def main():
    """Main entry point for the rundeck-mcp command."""
    print("Starting Rundeck MCP Server. Use the --enable-write-tools flag to enable write tools.")
    app()


if __name__ == "__main__":
    main()
