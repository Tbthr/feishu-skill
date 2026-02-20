"""
Feishu MCP Client - Zero-Context MCP Tool Caller

封装 executor.py 调用，提供简洁的 Python 接口。
所有 MCP 调用通过 executor.py 执行，响应不注入 Claude context。
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List


class FeishuMCPClient:
    """
    飞书 MCP 客户端 - 零上下文调用

    使用方式:
        client = FeishuMCPClient()
        result = client.call("get_feishu_document_blocks", {"documentId": "xxx"})
    """

    def __init__(self, scripts_dir: Optional[str] = None):
        """
        初始化客户端

        Args:
            scripts_dir: scripts 目录路径，默认自动检测
        """
        if scripts_dir:
            self.scripts_dir = Path(scripts_dir)
        else:
            # 自动检测：当前文件所在目录
            self.scripts_dir = Path(__file__).parent

        self.executor_path = self.scripts_dir / "executor.py"

        # 验证 executor.py 存在
        if not self.executor_path.exists():
            raise FileNotFoundError(f"executor.py not found: {self.executor_path}")

        # 注意：凭证配置通过环境变量或 setup-feishu.py 设置

    def list_tools(self) -> List[Dict]:
        """列出所有可用工具"""
        result = subprocess.run(
            [sys.executable, str(self.executor_path), "--list"],
            cwd=str(self.scripts_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to list tools: {result.stderr}")
        return json.loads(result.stdout)

    def describe_tool(self, tool_name: str) -> Dict:
        """获取工具详细 schema"""
        result = subprocess.run(
            [sys.executable, str(self.executor_path), "--describe", tool_name],
            cwd=str(self.scripts_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to describe tool: {result.stderr}")
        return json.loads(result.stdout)

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用 MCP 工具（零上下文）

        Args:
            tool_name: 工具名称，如 "get_feishu_document_blocks"
            arguments: 工具参数

        Returns:
            工具返回结果（已解析为 Python 对象）
        """
        call_data = {
            "tool": tool_name,
            "arguments": arguments
        }

        result = subprocess.run(
            [sys.executable, str(self.executor_path), "--call", json.dumps(call_data)],
            cwd=str(self.scripts_dir),
            capture_output=True,
            text=True,
            timeout=120  # 较长超时，适应大文档
        )

        if result.returncode != 0:
            raise RuntimeError(f"MCP call failed: {result.stderr}")

        # 尝试解析 JSON，失败则返回原始文本
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout

    def call_and_save(self, tool_name: str, arguments: Dict[str, Any],
                      output_file: str) -> str:
        """
        调用工具并保存结果到文件（推荐用于大响应）

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            output_file: 输出文件路径

        Returns:
            输出文件路径
        """
        result = self.call(tool_name, arguments)

        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return str(output_path)


# 全局单例
_client: Optional[FeishuMCPClient] = None


def get_client() -> FeishuMCPClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = FeishuMCPClient()
    return _client


def call_feishu_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    便捷函数：调用飞书 MCP 工具

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具返回结果
    """
    return get_client().call(tool_name, arguments)


def fetch_document(url_or_id: str, output_dir: str = "/tmp",
                   document_type: Optional[str] = None) -> Dict[str, str]:
    """
    获取飞书文档并保存到临时文件（推荐方式，避免内容注入 context）

    Args:
        url_or_id: 文档 URL 或 ID（支持 /docx/ 和 /wiki/ 格式）
        output_dir: 临时文件目录（默认 /tmp）
        document_type: 文档类型（"wiki" 或 None 自动检测）

    Returns:
        Dict with document info and file paths:
        {
            "document_id": "xxx",
            "title": "文档标题",
            "blocks_file": "/tmp/document_xxx_blocks.json",
            "markdown_file": "/tmp/document_xxx.md"
        }
    """
    client = get_client()

    # 自动检测文档类型
    is_wiki = "/wiki/" in url_or_id or document_type == "wiki"

    # 1. 获取文档信息
    if is_wiki:
        doc_info = client.call("get_feishu_document_info", {
            "documentId": url_or_id,
            "documentType": "wiki"
        })
        document_id = doc_info.get("obj_token") or doc_info.get("documentId")
    else:
        # 直接使用 documentId
        if url_or_id.startswith("http"):
            # 从 URL 提取 ID
            import re
            match = re.search(r"/docx/([^/?]+)", url_or_id)
            document_id = match.group(1) if match else url_or_id
        else:
            document_id = url_or_id

        doc_info = client.call("get_feishu_document_info", {
            "documentId": document_id
        })

    document_id = document_id or doc_info.get("obj_token", doc_info.get("documentId", "unknown"))

    # 2. 生成文件路径（使用 document_id 命名）
    safe_id = document_id.replace("/", "_").replace(":", "_")[:50]
    blocks_file = f"{output_dir}/document_{safe_id}_blocks.json"
    markdown_file = f"{output_dir}/document_{safe_id}.md"

    # 3. 获取文档块并保存
    blocks = client.call("get_feishu_document_blocks", {
        "documentId": document_id
    })

    with open(blocks_file, 'w', encoding='utf-8') as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)

    # 4. 转换为 Markdown 并保存
    from document_processor import DocumentProcessor
    processor = DocumentProcessor()
    markdown = processor.to_markdown(blocks)

    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return {
        "document_id": document_id,
        "title": doc_info.get("title", ""),
        "blocks_file": blocks_file,
        "markdown_file": markdown_file
    }


def process_document(blocks_file: str, format: str = "markdown",
                     output_file: Optional[str] = None) -> str:
    """
    处理已保存的文档块文件

    Args:
        blocks_file: 文档块 JSON 文件路径
        format: 输出格式（markdown, outline, summary）
        output_file: 输出文件路径（默认 stdout）

    Returns:
        处理结果（字符串）
    """
    from document_processor import DocumentProcessor

    with open(blocks_file, 'r', encoding='utf-8') as f:
        blocks = json.load(f)

    processor = DocumentProcessor()

    if format == "markdown":
        result = processor.to_markdown(blocks)
    elif format == "outline":
        result = processor.get_outline(blocks)
    elif format == "summary":
        summary = processor.get_document_summary(blocks)
        result = json.dumps(summary, indent=2, ensure_ascii=False)
    else:
        raise ValueError(f"Unknown format: {format}")

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        return output_file

    return result


# CLI Entry Point
if __name__ == "__main__":
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(
        description="Feishu MCP Client - Zero-context tool caller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available tools
  python mcp_client.py --list

  # Describe a specific tool
  python mcp_client.py --describe get_feishu_document_blocks

  # Call a tool with JSON arguments
  python mcp_client.py --call get_feishu_document_info --args '{"documentId": "xxx"}'

  # Fetch document and save to temp files (RECOMMENDED - avoids context injection)
  python mcp_client.py --fetch "https://xxx.feishu.cn/wiki/xxx"
  # Creates: /tmp/document_{id}_blocks.json and /tmp/document_{id}.md

  # Fetch with custom output directory
  python mcp_client.py --fetch "https://xxx.feishu.cn/docx/xxx" --output-dir ./output

  # Process saved blocks file
  python mcp_client.py --process /tmp/document_xxx_blocks.json --format markdown
  python mcp_client.py --process /tmp/document_xxx_blocks.json --format outline
  python mcp_client.py --process /tmp/document_xxx_blocks.json --format summary
        """
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available tools"
    )
    parser.add_argument(
        "--describe", "-d",
        metavar="TOOL",
        help="Describe a specific tool"
    )
    parser.add_argument(
        "--call", "-c",
        metavar="TOOL",
        help="Call a tool"
    )
    parser.add_argument(
        "--args", "-a",
        help="JSON arguments for tool call"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--fetch", "-f",
        metavar="URL",
        help="Fetch document and save to temp files (avoids context injection)"
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp",
        help="Output directory for --fetch (default: /tmp)"
    )
    parser.add_argument(
        "--process", "-p",
        metavar="FILE",
        help="Process saved blocks file"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "outline", "summary"],
        default="markdown",
        help="Output format for --process (default: markdown)"
    )

    args = parser.parse_args()

    client = FeishuMCPClient()

    if args.list:
        tools = client.list_tools()
        print(json.dumps(tools, indent=2, ensure_ascii=False))

    elif args.describe:
        schema = client.describe_tool(args.describe)
        if schema:
            print(json.dumps(schema, indent=2, ensure_ascii=False))
        else:
            print(f"Tool not found: {args.describe}", file=sys.stderr)
            sys.exit(1)

    elif args.fetch:
        result = fetch_document(args.fetch, args.output_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.process:
        try:
            result = process_document(args.process, args.format, args.output)
            if args.output:
                print(f"Output saved to: {args.output}", file=sys.stderr)
            else:
                print(result)
        except FileNotFoundError:
            print(f"Error: File not found: {args.process}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.call:
        if not args.args:
            print("Error: --args is required for --call", file=sys.stderr)
            sys.exit(1)

        try:
            arguments = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON arguments: {e}", file=sys.stderr)
            sys.exit(1)

        result = client.call(args.call, arguments)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Output saved to: {args.output}", file=sys.stderr)
        else:
            if isinstance(result, str):
                print(result)
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()
