#!/usr/bin/env python3
"""
Feishu MCP Credential Setup

Configure your Feishu credentials for the feishu-analyst skill.
Credentials are stored in ~/.feishu-mcp/config.json
"""
import json
import os
from pathlib import Path


def main():
    print("=== Feishu MCP Credential Setup ===\n")

    # Check existing config
    config_path = Path.home() / ".feishu-mcp" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                existing = json.load(f)
            print(f"Found existing config at {config_path}")
            existing_id = existing.get("env", {}).get("FEISHU_APP_ID", "")
            if existing_id:
                print(f"Current APP_ID: {existing_id[:8]}...\n")
            input("Press Enter to reconfigure, or Ctrl+C to cancel...\n")
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not read existing config, will overwrite.\n")

    # Get credentials
    print("Step 1: Get your Feishu credentials")
    print("  Visit: https://open.feishu.cn/")
    print("  Navigate to: App Settings > Credentials & Basic Info\n")

    app_id = input("Step 2: Enter Feishu App ID: ").strip()
    if not app_id:
        print("Error: App ID is required")
        return 1

    app_secret = input("Step 3: Enter Feishu App Secret: ").strip()
    if not app_secret:
        print("Error: App Secret is required")
        return 1

    print("\nStep 4: Choose authentication type")
    print("  1) tenant - App credentials (recommended)")
    print("  2) user   - User authorization via browser")
    auth_choice = input("Enter choice [1/2, default: 1]: ").strip() or "1"
    auth_type = "tenant" if auth_choice == "1" else "user"

    # Create config directory
    config_dir = Path.home() / ".feishu-mcp"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write config
    config = {
        "env": {
            "FEISHU_APP_ID": app_id,
            "FEISHU_APP_SECRET": app_secret,
            "FEISHU_AUTH_TYPE": auth_type
        }
    }

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Set permissions (readable only by owner)
    os.chmod(config_path, 0o600)

    print(f"\n✓ Configuration saved to: {config_path}")
    print("\n--- Alternative: Environment Variables ---")
    print("You can also set these environment variables:")
    print(f"  export FEISHU_APP_ID='{app_id}'")
    print(f"  export FEISHU_APP_SECRET='***'")

    return 0


if __name__ == "__main__":
    exit(main())
