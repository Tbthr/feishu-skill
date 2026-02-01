#!/bin/bash
# Feishu MCP Configuration Script
# Usage: bash scripts/setup.sh [check|install|remove]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
MCP_SERVER_NAME="Feishu-MCP"

# Detect project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
USER_CONFIG="$HOME/.claude.json"
PROJECT_CONFIG="$PROJECT_ROOT/.mcp.json"

# Print colored message
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if jq is installed
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_status "$RED" "Error: jq is not installed"
        echo "Install jq:"
        echo "  macOS:   brew install jq"
        echo "  linux:   sudo apt-get install jq"
        exit 1
    fi
}

# Choose configuration scope
choose_scope() {
    echo ""
    print_status "$CYAN" "Choose configuration scope:"
    echo ""
    echo "  1) User scope   - All projects (requires: ~/.claude.json)"
    echo "  2) Project scope - This project only (creates: .mcp.json)"
    echo ""
    read -p "Enter choice [1/2] (default: 1): " -n 1 -r
    echo ""

    case $REPLY in
        2|"2")
            echo "project"
            ;;
        *)
            echo "user"
            ;;
    esac
}

# Get config file path and scope name
get_config_info() {
    local scope=$1

    if [ "$scope" = "project" ]; then
        echo "$PROJECT_CONFIG" "Project"
    else
        echo "$USER_CONFIG" "User"
    fi
}

# Check if config exists
check_config_exists() {
    local scope=$1
    local config_file
    local scope_name
    read -r config_file scope_name < <(get_config_info "$scope")

    if [ ! -f "$config_file" ]; then
        if [ "$scope" = "project" ]; then
            # For project scope, we'll create the file
            print_status "$YELLOW" "Creating new .mcp.json file..."
            echo "{}" > "$config_file"
        else
            print_status "$RED" "Error: Claude Code config not found at $config_file"
            print_status "$YELLOW" "Please make sure Claude Code is installed and has been run at least once."
            exit 1
        fi
    fi
}

# Check MCP status in specific config
check_mcp_in_config() {
    local config_file=$1
    local scope_name=$2

    if jq -e ".mcpServers[\"$MCP_SERVER_NAME\"]" "$config_file" >/dev/null 2>&1; then
        APP_ID=$(jq -r ".mcpServers[\"$MCP_SERVER_NAME\"].env.FEISHU_APP_ID" "$config_file")
        print_status "$GREEN" "[OK] Feishu MCP configured ($scope_name scope)"
        echo "    APP_ID: ${APP_ID:0:8}..."
        return 0
    else
        return 1
    fi
}

# Check if MCP is configured
cmd_check() {
    print_status "$BLUE" "=== Feishu MCP Configuration Status ==="
    echo ""

    local found=0

    # Check user scope
    if [ -f "$USER_CONFIG" ]; then
        if check_mcp_in_config "$USER_CONFIG" "User"; then
            found=1
        fi
    fi

    # Check project scope
    if [ -f "$PROJECT_CONFIG" ]; then
        if check_mcp_in_config "$PROJECT_CONFIG" "Project"; then
            found=1
        fi
    fi

    if [ $found -eq 0 ]; then
        print_status "$RED" "[NOT CONFIGURED] Feishu MCP is not set up"
        echo ""
        print_status "$YELLOW" "To configure, run: bash scripts/setup.sh install"
    fi
}

# Configure Feishu MCP
cmd_install() {
    print_status "$BLUE" "=== Feishu MCP Configuration Wizard ==="
    echo ""

    # Choose scope
    SCOPE=$(choose_scope)
    read -r CONFIG_FILE SCOPE_NAME < <(get_config_info "$SCOPE")

    print_status "$CYAN" "Configuration scope: $SCOPE_NAME"
    print_status "$CYAN" "Config file: $CONFIG_FILE"
    echo ""

    # Check if already configured in this scope
    if [ -f "$CONFIG_FILE" ] && jq -e ".mcpServers[\"$MCP_SERVER_NAME\"]" "$CONFIG_FILE" >/dev/null 2>&1; then
        print_status "$YELLOW" "Feishu MCP is already configured in $SCOPE_NAME scope."
        read -p "Do you want to reconfigure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "$YELLOW" "Configuration cancelled."
            exit 0
        fi
    fi

    # Guide to get credentials
    echo "Step 1: Get your Feishu credentials"
    echo "-----------------------------------"
    echo "1. Visit: https://open.feishu.cn/"
    echo "2. Create a new app (or use existing)"
    echo "3. Go to 'Credentials & Basic Info'"
    echo "4. Copy App ID and App Secret"
    echo ""

    # Prompt for App ID
    while true; do
        read -p "Step 2: Enter your Feishu App ID: " APP_ID
        if [ -n "$APP_ID" ]; then
            break
        fi
        print_status "$RED" "App ID cannot be empty."
    done

    # Prompt for App Secret
    while true; do
        read -p "Step 3: Enter your Feishu App Secret: " APP_SECRET
        if [ -n "$APP_SECRET" ]; then
            break
        fi
        print_status "$RED" "App Secret cannot be empty."
    done

    # Prompt for auth type
    echo ""
    print_status "$YELLOW" "Step 4: Choose authentication type"
    echo "  1) Tenant (recommended - uses app credentials)"
    echo "  2) User (requires user authorization via browser)"
    read -p "Enter choice [1/2] (default: 1): " -n 1 -r
    echo ""

    AUTH_TYPE="tenant"
    if [[ $REPLY =~ ^[2]$ ]]; then
        AUTH_TYPE="user"
        print_status "$CYAN" "Using 'user' auth type - will require browser authorization"
    else
        print_status "$CYAN" "Using 'tenant' auth type (recommended)"
    fi
    echo ""

    print_status "$YELLOW" "Step 5: Configuring MCP..."

    # Ensure config file exists
    check_config_exists "$SCOPE"

    # Backup config
    BACKUP_FILE="$CONFIG_FILE.backup.$(date +%s)"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    print_status "$GREEN" "Backup saved to: $BACKUP_FILE"

    # Configure MCP using jq
    tmp_file=$(mktemp)
    jq --arg app_id "$APP_ID" \
       --arg app_secret "$APP_SECRET" \
       --arg auth_type "$AUTH_TYPE" \
       '.mcpServers["Feishu-MCP"] = {
           "command": "npx",
           "args": ["-y", "feishu-mcp@latest", "--stdio"],
           "env": {
               "FEISHU_APP_ID": $app_id,
               "FEISHU_APP_SECRET": $app_secret,
               "FEISHU_AUTH_TYPE": $auth_type
           },
           "type": "stdio"
       }' "$CONFIG_FILE" > "$tmp_file" && \
    mv "$tmp_file" "$CONFIG_FILE"

    print_status "$GREEN" "[OK] MCP configuration written to $CONFIG_FILE"
    echo ""
    print_status "$YELLOW" "=== Configuration Complete ==="
    echo ""
    print_status "$BLUE" "IMPORTANT: Restart Claude Code to load the MCP server."
    echo ""
    echo "After restart, verify MCP is working by running:"
    echo "  bash scripts/setup.sh check"

    # If project scope, remind about settings
    if [ "$SCOPE" = "project" ]; then
        echo ""
        print_status "$CYAN" "Note: Project MCP servers are configured in .mcp.json"
        echo "      Team members can approve this server by running:"
        echo "      claude mcp add"
    fi
}

# Remove Feishu MCP configuration
cmd_remove() {
    print_status "$YELLOW" "=== Removing Feishu MCP Configuration ==="
    echo ""

    # Check which scopes have the config
    local has_user=0
    local has_project=0

    if [ -f "$USER_CONFIG" ] && jq -e ".mcpServers[\"$MCP_SERVER_NAME\"]" "$USER_CONFIG" >/dev/null 2>&1; then
        has_user=1
    fi

    if [ -f "$PROJECT_CONFIG" ] && jq -e ".mcpServers[\"$MCP_SERVER_NAME\"]" "$PROJECT_CONFIG" >/dev/null 2>&1; then
        has_project=1
    fi

    if [ $has_user -eq 0 ] && [ $has_project -eq 0 ]; then
        print_status "$YELLOW" "Feishu MCP is not configured."
        exit 0
    fi

    # Show what will be removed
    if [ $has_user -eq 1 ]; then
        echo "Found in: User scope (~/.claude.json)"
    fi
    if [ $has_project -eq 1 ]; then
        echo "Found in: Project scope (.mcp.json)"
    fi
    echo ""

    read -p "Remove all Feishu MCP configurations? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "$YELLOW" "Removal cancelled."
        exit 0
    fi

    # Remove from user config
    if [ $has_user -eq 1 ]; then
        BACKUP_FILE="$USER_CONFIG.backup.$(date +%s)"
        cp "$USER_CONFIG" "$BACKUP_FILE"
        print_status "$GREEN" "Backup saved to: $BACKUP_FILE"

        jq 'del(.mcpServers["Feishu-MCP"])' "$USER_CONFIG" > "${USER_CONFIG}.tmp" && \
        mv "${USER_CONFIG}.tmp" "$USER_CONFIG"

        print_status "$GREEN" "[OK] Removed from User scope"
    fi

    # Remove from project config
    if [ $has_project -eq 1 ]; then
        BACKUP_FILE="$PROJECT_CONFIG.backup.$(date +%s)"
        cp "$PROJECT_CONFIG" "$BACKUP_FILE"
        print_status "$GREEN" "Backup saved to: $BACKUP_FILE"

        jq 'del(.mcpServers["Feishu-MCP"])' "$PROJECT_CONFIG" > "${PROJECT_CONFIG}.tmp" && \
        mv "${PROJECT_CONFIG}.tmp" "$PROJECT_CONFIG"

        print_status "$GREEN" "[OK] Removed from Project scope"
    fi

    echo ""
    print_status "$YELLOW" "Restart Claude Code to apply changes."
}

# Main
check_jq

case "${1:-check}" in
    check)
        cmd_check
        ;;
    install)
        cmd_install
        ;;
    remove)
        cmd_remove
        ;;
    *)
        echo "Feishu MCP Configuration Script"
        echo ""
        echo "Usage: bash scripts/setup.sh [command]"
        echo ""
        echo "Commands:"
        echo "  check      - Check Feishu MCP configuration status"
        echo "  install    - Interactive configuration wizard"
        echo "  remove     - Remove Feishu MCP configuration"
        echo ""
        exit 1
        ;;
esac
