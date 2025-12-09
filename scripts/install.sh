#!/bin/bash
#
# Rundeck MCP Server - Quick Install Script
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/justynroberts/rundeck-mcp/main/scripts/install.sh | bash
#
# Or run locally:
#   ./scripts/install.sh
#

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════╗"
echo "║       Rundeck MCP Server Installer        ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}✓ uv installed${NC}"
else
    echo -e "${GREEN}✓ uv found${NC}"
fi

# Test the package
echo -e "\n${BLUE}Testing rundeck-mcp installation...${NC}"
if uvx rundeck-mcp --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓ rundeck-mcp is working${NC}"
else
    echo -e "${RED}✗ Failed to run rundeck-mcp${NC}"
    exit 1
fi

# Prompt for configuration
echo -e "\n${BLUE}Configuration${NC}"
echo "─────────────────────────────────────────────"

read -p "Rundeck URL [http://localhost:4440]: " RUNDECK_URL
RUNDECK_URL=${RUNDECK_URL:-http://localhost:4440}

read -p "Rundeck API Token: " RUNDECK_TOKEN
if [ -z "$RUNDECK_TOKEN" ]; then
    echo -e "${YELLOW}⚠ No token provided. You'll need to set RUNDECK_API_TOKEN later.${NC}"
fi

read -p "Enable write tools (job execution)? [y/N]: " ENABLE_WRITE
if [[ "$ENABLE_WRITE" =~ ^[Yy]$ ]]; then
    WRITE_FLAG="--enable-write-tools"
else
    WRITE_FLAG=""
fi

# Detect MCP client
echo -e "\n${BLUE}Select MCP Client to configure:${NC}"
echo "  1) Claude Desktop"
echo "  2) VS Code"
echo "  3) Cursor"
echo "  4) Show config only (manual setup)"
read -p "Choice [1-4]: " CLIENT_CHOICE

generate_config() {
    local client=$1

    case $client in
        1) # Claude Desktop
            if [[ "$OSTYPE" == "darwin"* ]]; then
                CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
            else
                CONFIG_PATH="$HOME/.config/Claude/claude_desktop_config.json"
            fi

            CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "rundeck-mcp": {
      "command": "uvx",
      "args": ["rundeck-mcp"${WRITE_FLAG:+, \"$WRITE_FLAG\"}],
      "env": {
        "RUNDECK_API_TOKEN": "${RUNDECK_TOKEN}",
        "RUNDECK_URL": "${RUNDECK_URL}"
      }
    }
  }
}
EOF
)
            ;;
        2) # VS Code
            CONFIG_PATH="$HOME/.vscode/settings.json"
            CONFIG=$(cat <<EOF
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
        "args": ["rundeck-mcp"${WRITE_FLAG:+, \"$WRITE_FLAG\"}],
        "env": {
          "RUNDECK_API_TOKEN": "\${input:rundeck-api-token}",
          "RUNDECK_URL": "${RUNDECK_URL}"
        }
      }
    }
  }
}
EOF
)
            ;;
        3) # Cursor
            CONFIG_PATH="Cursor Settings"
            CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "rundeck-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["rundeck-mcp"${WRITE_FLAG:+, \"$WRITE_FLAG\"}],
      "env": {
        "RUNDECK_API_TOKEN": "\${input:rundeck-api-token}",
        "RUNDECK_URL": "${RUNDECK_URL}"
      }
    }
  }
}
EOF
)
            ;;
        4) # Manual
            CONFIG_PATH="manual"
            CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "rundeck-mcp": {
      "command": "uvx",
      "args": ["rundeck-mcp"${WRITE_FLAG:+, \"$WRITE_FLAG\"}],
      "env": {
        "RUNDECK_API_TOKEN": "${RUNDECK_TOKEN:-<your-token>}",
        "RUNDECK_URL": "${RUNDECK_URL}"
      }
    }
  }
}
EOF
)
            ;;
    esac
}

generate_config $CLIENT_CHOICE

echo -e "\n${BLUE}Generated Configuration:${NC}"
echo "─────────────────────────────────────────────"
echo "$CONFIG"
echo "─────────────────────────────────────────────"

if [[ "$CLIENT_CHOICE" == "1" && -n "$CONFIG_PATH" ]]; then
    read -p "Write config to $CONFIG_PATH? [y/N]: " WRITE_CONFIG
    if [[ "$WRITE_CONFIG" =~ ^[Yy]$ ]]; then
        mkdir -p "$(dirname "$CONFIG_PATH")"
        if [ -f "$CONFIG_PATH" ]; then
            echo -e "${YELLOW}⚠ Config file exists. Backing up to ${CONFIG_PATH}.bak${NC}"
            cp "$CONFIG_PATH" "${CONFIG_PATH}.bak"
        fi
        echo "$CONFIG" > "$CONFIG_PATH"
        echo -e "${GREEN}✓ Config written to $CONFIG_PATH${NC}"
    fi
fi

echo -e "\n${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation Complete!           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Copy the config above to your MCP client"
echo "  2. Restart your MCP client"
echo "  3. Try: 'List all jobs in project <your-project>'"
echo ""
echo "Documentation: https://github.com/justynroberts/rundeck-mcp"
