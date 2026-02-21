#!/usr/bin/env python3
"""
Feishu MCP CLI - Command Line Interface

Usage:
    python cli.py save <url> [--output-dir DIR]
    python cli.py outline <blocks_file>
    python cli.py list
    python cli.py describe <tool>
    python cli.py call <tool> --args '{"...": "..."}' [--output FILE]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Import from local modules
sys.path.insert(0, str(Path(__file__).parent))

from client import FeishuMCPClient
from document import save_document, get_outline


def cmd_save(args):
    """Save document to files."""
    try:
        output_dir = args.output_dir or tempfile.gettempdir()
        result = save_document(args.url, output_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_outline(args):
    """Extract document outline."""
    try:
        outline = get_outline(args.blocks_file)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(outline)
            print(f"Outline saved to: {args.output}", file=sys.stderr)
        else:
            print(outline)
    except FileNotFoundError:
        print(f"Error: File not found: {args.blocks_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    """List all available tools."""
    client = FeishuMCPClient()
    tools = client.list_tools()
    print(json.dumps(tools, indent=2, ensure_ascii=False))


def cmd_describe(args):
    """Describe a specific tool."""
    client = FeishuMCPClient()
    schema = client.describe_tool(args.tool)
    if schema:
        print(json.dumps(schema, indent=2, ensure_ascii=False))
    else:
        print(f"Tool not found: {args.tool}", file=sys.stderr)
        sys.exit(1)


def cmd_call(args):
    """Call a tool with JSON arguments."""
    if not args.args:
        print("Error: --args is required for call", file=sys.stderr)
        sys.exit(1)

    try:
        arguments = json.loads(args.args)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON arguments: {e}", file=sys.stderr)
        sys.exit(1)

    client = FeishuMCPClient()
    result = client.call(args.tool, arguments)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Output saved to: {args.output}", file=sys.stderr)
    else:
        if isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Feishu MCP CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command')

    # save command
    save_parser = subparsers.add_parser('save', help='Save document to files')
    save_parser.add_argument('url', help='Document URL or ID')
    save_parser.add_argument('--output-dir', help='Output directory (default: temp)')

    # outline command
    outline_parser = subparsers.add_parser('outline', help='Extract document outline')
    outline_parser.add_argument('blocks_file', help='Blocks JSON file')
    outline_parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    # list command
    subparsers.add_parser('list', help='List all available tools')

    # describe command
    describe_parser = subparsers.add_parser('describe', help='Describe a tool')
    describe_parser.add_argument('tool', help='Tool name')

    # call command
    call_parser = subparsers.add_parser('call', help='Call a tool')
    call_parser.add_argument('tool', help='Tool name')
    call_parser.add_argument('--args', '-a', help='JSON arguments')
    call_parser.add_argument('--output', '-o', help='Output file')

    args = parser.parse_args()

    if args.command == 'save':
        cmd_save(args)
    elif args.command == 'outline':
        cmd_outline(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'describe':
        cmd_describe(args)
    elif args.command == 'call':
        cmd_call(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
