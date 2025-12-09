# Rundeck MCP Server

Rundeck's local MCP (Model Context Protocol) server which provides tools to interact with your Rundeck instance, allowing you to list jobs, run jobs with options, and retrieve execution status and logs directly from your MCP-enabled client.

## Prerequisites

*   [asdf-vm](https://asdf-vm.com/) installed.
*   [uv](https://github.com/astral-sh/uv) installed globally.
*   A Rundeck **API Token**.
    To obtain a Rundeck API Token, follow these steps:

    1. **Log in to your Rundeck instance** and click on your username in the top-right corner.
    2. Navigate to **User Profile** and then **User API Tokens**.
    3. Click **Generate New Token**, provide a name, and select the appropriate roles.
    4. **Copy the generated token and store it securely**. You will need this token to configure the MCP server.

    > **Note:** API tokens inherit the permissions of the user who created them. Ensure your user has appropriate access to the jobs you want to manage.

## Using with MCP Clients

### Cursor Integration

You can configure this MCP server directly within Cursor's `settings.json` file, by following these steps:

1.  Open Cursor settings (Cursor Settings > Tools > Add MCP, or `Cmd+,` on Mac, or `Ctrl+,` on Windows/Linux).
2.  Add the following configuration:

    ```json
    {
      "mcpServers": {
        "rundeck-mcp": {
          "type": "stdio",
          "command": "uvx",
          "args": [
            "rundeck-mcp",
            "--enable-write-tools"
            // This flag enables write operations on the MCP Server enabling you to run jobs
          ],
          "env": {
            "RUNDECK_API_TOKEN": "${input:rundeck-api-token}",
            "RUNDECK_URL": "http://localhost:4440"
          }
        }
      }
    }
    ```

### VS Code Integration

You can configure this MCP server directly within Visual Studio Code's `settings.json` file, allowing VS Code to manage the server lifecycle.

1.  Open VS Code settings (File > Preferences > Settings, or `Cmd+,` on Mac, or `Ctrl+,` on Windows/Linux).
2.  Search for "mcp" and ensure "Mcp: Enabled" is checked under Features > Chat.
3.  Click "Edit in settings.json" under "Mcp > Discovery: Servers".
4.  Add the following configuration:

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
                    "args": [
                        "rundeck-mcp",
                        "--enable-write-tools"
                        // This flag enables write operations on the MCP Server enabling you to run jobs
                    ],
                    "env": {
                        "RUNDECK_API_TOKEN": "${input:rundeck-api-token}",
                        "RUNDECK_URL": "http://localhost:4440"
                        // Update this to your Rundeck server URL
                    }
                }
            }
        }
    }
    ```

#### Trying it in VS Code Chat (Agent)

1.  Ensure MCP is enabled in VS Code settings (Features > Chat > "Mcp: Enabled").
2.  Configure the server as described above.
3.  Open the Chat view in VS Code (`View` > `Chat`).
4.  Make sure `Agent` mode is selected. In the Chat view, you can enable or disable specific tools by clicking the tools icon.
5.  Enter a command such as `List all jobs in project myproject` or `Run the deploy job with version 1.2.3` to interact with your Rundeck instance through the MCP server.
6.  You can start, stop, and manage your MCP servers using the command palette (`Cmd+Shift+P`/`Ctrl+Shift+P`) and searching for `MCP: List Servers`. Ensure the server is running before sending commands. You can also try to restart the server if you encounter any issues.

### Claude Desktop Integration

You can configure this MCP server to work with Claude Desktop by adding it to Claude's configuration file.

1.  **Locate your Claude Desktop configuration file:**
    -   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
    -   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

2.  **Create or edit the configuration file** and add the following configuration:

    ```json
    {
      "mcpServers": {
        "rundeck-mcp": {
          "command": "uvx",
          "args": [
            "rundeck-mcp",
            "--enable-write-tools"
          ],
          "env": {
            "RUNDECK_API_TOKEN": "your-rundeck-api-token-here",
            "RUNDECK_URL": "http://localhost:4440"
          }
        }
      }
    }
    ```

3.  **Replace the placeholder values:**
    -   Replace `your-rundeck-api-token-here` with your actual Rundeck API Token
    -   Replace `http://localhost:4440` with your Rundeck server URL

4.  **Restart Claude Desktop** completely for the changes to take effect.

5.  **Test the integration** by starting a conversation with Claude and asking something like "List all jobs in project myproject" or "Show me recent executions" to verify the MCP server is working.

    > **Security Note:** Unlike VS Code's secure input prompts, Claude Desktop requires you to store your API token directly in the configuration file. Ensure this file has appropriate permissions (readable only by your user account) and consider the security implications of storing credentials in plain text.

## Set up locally

1.  **Clone the repository**

2. **Install `asdf` plugins**
    ```shell
    asdf plugin add python
    asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git
    asdf plugin add uv
    ```

3.  **Install tool versions** using `asdf`:
    ```shell
    asdf install
    ```

4.  **Create a virtual environment and install dependencies** using `uv` (now that `asdf` has set the correct Python and `uv` versions):

    ```shell
    uv sync
    ```

5.  **Ensure `uv` is available globally.**

    The MCP server can be run from different places so you need `uv` to be available globally. To do so, follow the [official documentation](https://docs.astral.sh/uv/getting-started/installation/).


    > **Tip:** You may need to restart your terminal and/or VS Code for the changes to take effect.

6. **Run it locally**

    To run your cloned Rundeck MCP Server you need to update your configuration to use `uv` instead of `uvx`.

    ```json
    "rundeck-mcp": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "/path/to/your/mcp-server-directory",
            // Replace with the full path to the directory where you cloned the MCP server, e.g. "/Users/yourname/code/rundeck-mcp",
            "python",
            "-m",
            "rundeck_mcp",
            "--enable-write-tools"
            // This flag enables write operations on the MCP Server enabling you to run jobs
        ],
        "env": {
            "RUNDECK_API_TOKEN": "${input:rundeck-api-token}",
            "RUNDECK_URL": "http://localhost:4440"
            // Update this to your Rundeck server URL
        }
    }
    ```

## Available Tools and Resources

This section describes the tools provided by the Rundeck MCP server. They are categorized based on whether they only read data or can modify data in your Rundeck instance.

> **Important:** By default, the MCP server only exposes read-only tools. To enable tools that can modify your Rundeck instance (write-mode tools), you must explicitly start the server with the `--enable-write-tools` flag. This helps prevent accidental job executions.

| Tool                   | Area               | Description                                         | Read-only |
|------------------------|--------------------|-----------------------------------------------------|-----------|
| list_jobs              | Jobs               | Lists jobs in a project with optional filtering     | ✅         |
| get_job                | Jobs               | Retrieves job details including options and defaults| ✅         |
| list_executions        | Executions         | Lists executions with filtering by status or time   | ✅         |
| get_execution          | Executions         | Retrieves execution status and details              | ✅         |
| get_execution_output   | Executions         | Retrieves execution log output                      | ✅         |
| run_job                | Jobs               | Executes a job with options                         | ❌         |

### Job Options

When running jobs with the `run_job` tool, the server validates options before execution:

*   **Required options** must be provided (unless they have default values)
*   **Enforced options** must use values from the allowed list
*   **Option summaries** are displayed when validation fails

Example job options display:

```
Job Options:

  - version [REQUIRED]
      The version to deploy
      Allowed values (must be): '1.0', '1.1', '2.0'

  - environment [optional] (default: 'staging')
      Target environment
      Allowed values (suggested): 'dev', 'staging', 'prod'

  - dry_run [optional] (default: 'false')
      Run without making changes
```

## Configuration

| Environment Variable    | Description                      | Default                    |
|------------------------|----------------------------------|----------------------------|
| `RUNDECK_API_TOKEN`    | API token for authentication     | (required)                 |
| `RUNDECK_URL`          | Rundeck server URL               | `http://localhost:4440`    |
| `RUNDECK_API_VERSION`  | API version number               | `44`                       |

## Support

This MCP server is an open-source project. If assistance is required, please open an issue in the repository.

## Contributing

If you are interested in contributing to this project, please refer to the [PRD.md](PRD.md) for architecture decisions and implementation patterns.
