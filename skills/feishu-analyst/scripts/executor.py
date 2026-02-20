#!/usr/bin/env python3
"""
MCP Skill Executor
==================
Handles dynamic communication with the MCP server.

Configuration is loaded from multiple sources (in order of priority):
1. Environment variables (highest priority)
2. User config file: ~/.feishu-mcp/config.json
"""

import json
import os
import sys
import asyncio
import argparse
from pathlib import Path

# Check if mcp package is available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("Warning: mcp package not installed. Install with: pip install mcp", file=sys.stderr)


def load_config():
    """
    Load config from multiple sources with priority:
    1. Environment variables (highest priority)
    2. User config file: ~/.feishu-mcp/config.json
    """
    # Base MCP server config (hardcoded, no sensitive data)
    config = {
        "command": "npx",
        "args": ["-y", "feishu-mcp@latest", "--stdio"],
        "env": {
            "FEISHU_APP_ID": "",
            "FEISHU_APP_SECRET": "",
            "FEISHU_AUTH_TYPE": "tenant"
        },
        "type": "stdio"
    }

    # 1. Load user config (~/.feishu-mcp/config.json)
    user_config_path = Path.home() / ".feishu-mcp" / "config.json"
    if user_config_path.exists():
        try:
            with open(user_config_path) as f:
                user_config = json.load(f)
                config["env"].update(user_config.get("env", {}))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load user config: {e}", file=sys.stderr)

    # 2. Override with environment variables (highest priority)
    if os.environ.get("FEISHU_APP_ID"):
        config["env"]["FEISHU_APP_ID"] = os.environ["FEISHU_APP_ID"]
    if os.environ.get("FEISHU_APP_SECRET"):
        config["env"]["FEISHU_APP_SECRET"] = os.environ["FEISHU_APP_SECRET"]
    if os.environ.get("FEISHU_AUTH_TYPE"):
        config["env"]["FEISHU_AUTH_TYPE"] = os.environ["FEISHU_AUTH_TYPE"]

    # 3. Validate required credentials
    if not config["env"].get("FEISHU_APP_ID") or not config["env"].get("FEISHU_APP_SECRET"):
        print("Error: Feishu credentials not configured!", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please configure using one of these methods:", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Method 1 - Run setup script:", file=sys.stderr)
        print("    python scripts/setup_feishu.py", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Method 2 - Set environment variables:", file=sys.stderr)
        print("    export FEISHU_APP_ID='your-app-id'", file=sys.stderr)
        print("    export FEISHU_APP_SECRET='your-app-secret'", file=sys.stderr)
        print("", file=sys.stderr)
        print("Get credentials from: https://open.feishu.cn/", file=sys.stderr)
        sys.exit(1)

    return config


class MCPExecutor:
    """Execute MCP tool calls dynamically."""

    def __init__(self, server_config):
        if not HAS_MCP:
            raise ImportError("mcp package is required. Install with: pip install mcp")

        self.server_config = server_config
        self.session = None
        self.exit_stack = None

    async def __aenter__(self):
        """Async context manager entry."""
        server_params = StdioServerParameters(
            command=self.server_config["command"],
            args=self.server_config.get("args", []),
            env=self.server_config.get("env")
        )

        # Use async with to properly handle the context manager
        from contextlib import AsyncExitStack
        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()

        read_stream, write_stream = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.session = ClientSession(read_stream, write_stream)
        await self.exit_stack.enter_async_context(self.session)
        await self.session.initialize()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.exit_stack:
            await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self):
        """Get list of available tools."""
        response = await self.session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in response.tools
        ]

    async def describe_tool(self, tool_name: str):
        """Get detailed schema for a specific tool."""
        response = await self.session.list_tools()
        for tool in response.tools:
            if tool.name == tool_name:
                return {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
        return None

    async def call_tool(self, tool_name: str, arguments: dict):
        """Execute a tool call."""
        response = await self.session.call_tool(tool_name, arguments)
        return response.content


async def main():
    parser = argparse.ArgumentParser(description="MCP Skill Executor")
    parser.add_argument("--call", help="JSON tool call to execute")
    parser.add_argument("--describe", help="Get tool schema")
    parser.add_argument("--list", action="store_true", help="List all tools")

    args = parser.parse_args()

    if not HAS_MCP:
        print("Error: mcp package not installed", file=sys.stderr)
        print("Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # Load config from environment or user config file
    config = load_config()
    
    async with MCPExecutor(config) as executor:
        if args.list:
            tools = await executor.list_tools()
            print(json.dumps(tools, indent=2))

        elif args.describe:
            schema = await executor.describe_tool(args.describe)
            if schema:
                print(json.dumps(schema, indent=2))
            else:
                print(f"Tool not found: {args.describe}", file=sys.stderr)
                sys.exit(1)

        elif args.call:
            call_data = json.loads(args.call)
            result = await executor.call_tool(
                call_data["tool"],
                call_data.get("arguments", {})
            )

            # Format result
            if isinstance(result, list):
                for item in result:
                    if hasattr(item, 'text'):
                        print(item.text)
                    else:
                        print(json.dumps(item.__dict__ if hasattr(item, '__dict__') else item, indent=2))
            else:
                print(json.dumps(result.__dict__ if hasattr(result, '__dict__') else result, indent=2))
        else:
            parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
