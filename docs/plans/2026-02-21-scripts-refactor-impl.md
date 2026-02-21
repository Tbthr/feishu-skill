# Scripts 模块重构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 scripts 模块，提供 CLI + Python API 双入口，删除冗余代码

**Architecture:** CLI 用于 slash command 固定流程，Python API 用于动态场景。`client.py` 提供纯 MCP 调用，`document.py` 提供高级文档操作。

**Tech Stack:** Python 3.8+, argparse, json, subprocess, tempfile

---

## Task 1: 创建 `cli.py` CLI 入口

**Files:**
- Create: `skills/feishu-analyst/scripts/cli.py`

**Step 1: 创建 cli.py 基础结构**

```python
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
    subparsers = parser.add_parsers(dest='command')

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
```

**Step 2: 验证 CLI 帮助信息**

Run: `python skills/feishu-analyst/scripts/cli.py --help`
Expected: 显示帮助信息

**Step 3: Commit**

```bash
git add skills/feishu-analyst/scripts/cli.py
git commit -m "feat(scripts): 添加 cli.py CLI 入口

- 支持 save/outline/list/describe/call 命令
- 使用子命令结构替代 --flag 形式"
```

---

## Task 2: 创建 `client.py` 核心 MCP 客户端

**Files:**
- Create: `skills/feishu-analyst/scripts/client.py`

**Step 1: 创建 client.py**

```python
"""
Feishu MCP Client - Zero-Context MCP Tool Caller

纯 MCP 调用客户端，不包含业务逻辑。
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


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
            self.scripts_dir = Path(__file__).parent

        self.executor_path = self.scripts_dir / "executor.py"

        if not self.executor_path.exists():
            raise FileNotFoundError(f"executor.py not found: {self.executor_path}")

    def _run_executor(self, *args: str, timeout: int = 120) -> str:
        """
        执行 executor.py 并返回 stdout

        Args:
            *args: 传递给 executor.py 的参数
            timeout: 超时时间（秒）

        Returns:
            stdout 内容

        Raises:
            RuntimeError: 如果执行失败
        """
        result = subprocess.run(
            [sys.executable, str(self.executor_path)] + list(args),
            cwd=str(self.scripts_dir),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Executor failed: {result.stderr}")

        return result.stdout

    def list_tools(self) -> List[Dict]:
        """列出所有可用工具"""
        stdout = self._run_executor("--list", timeout=60)
        return json.loads(stdout)

    def describe_tool(self, tool_name: str) -> Dict:
        """获取工具详细 schema"""
        stdout = self._run_executor("--describe", tool_name, timeout=60)
        data = json.loads(stdout)
        return data if data else None

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用 MCP 工具

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

        stdout = self._run_executor("--call", json.dumps(call_data), timeout=120)

        # 尝试解析 JSON，失败则返回原始文本
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return stdout.strip()
```

**Step 2: 验证 client.py**

Run: `python -c "from skills.feishu-analyst.scripts.client import FeishuMCPClient; print('OK')"`
Expected: 输出 "OK"

**Step 3: Commit**

```bash
git add skills/feishu-analyst/scripts/client.py
git commit -m "feat(scripts): 添加 client.py 核心 MCP 客户端

- FeishuMCPClient 类提供 list_tools/describe_tool/call 方法
- 提取 _run_executor 私有方法消除重复代码"
```

---

## Task 3: 创建 `document.py` 文档高级操作

**Files:**
- Create: `skills/feishu-analyst/scripts/document.py`

**Step 1: 创建 document.py**

```python
"""
Document Operations - 高级文档操作

提供 save_document 和 get_outline 便捷函数。
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional

from client import FeishuMCPClient
from processor import DocumentProcessor


def save_document(url_or_id: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    保存飞书文档到本地文件

    Args:
        url_or_id: 文档 URL 或 ID（支持 /docx/ 和 /wiki/ 格式）
        output_dir: 输出目录（默认系统临时目录）

    Returns:
        {
            "document_id": "xxx",
            "title": "文档标题",
            "blocks_file": "/tmp/document_xxx_blocks.json",
            "markdown_file": "/tmp/document_xxx.md"
        }
    """
    client = FeishuMCPClient()
    processor = DocumentProcessor()

    # 确定输出目录
    output_path = Path(output_dir) if output_dir else Path(tempfile.gettempdir())

    # 检测文档类型
    is_wiki = "/wiki/" in url_or_id

    # 1. 获取文档信息
    if is_wiki:
        doc_info = client.call("get_feishu_document_info", {
            "documentId": url_or_id,
            "documentType": "wiki"
        })
        document_id = doc_info.get("obj_token") or doc_info.get("documentId")
    else:
        # 从 URL 提取 ID 或直接使用
        if url_or_id.startswith("http"):
            match = re.search(r"/docx/([^/?]+)", url_or_id)
            document_id = match.group(1) if match else url_or_id
        else:
            document_id = url_or_id

        doc_info = client.call("get_feishu_document_info", {
            "documentId": document_id
        })

    document_id = document_id or doc_info.get("obj_token", doc_info.get("documentId", "unknown"))

    # 2. 生成文件路径
    safe_id = document_id.replace("/", "_").replace(":", "_")[:50]
    blocks_file = output_path / f"document_{safe_id}_blocks.json"
    markdown_file = output_path / f"document_{safe_id}.md"

    # 3. 获取文档块并保存
    blocks = client.call("get_feishu_document_blocks", {
        "documentId": document_id
    })

    with open(blocks_file, 'w', encoding='utf-8') as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)

    # 4. 转换为 Markdown 并保存
    markdown = processor.to_markdown(blocks)

    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return {
        "document_id": document_id,
        "title": doc_info.get("title", ""),
        "blocks_file": str(blocks_file),
        "markdown_file": str(markdown_file)
    }


def get_outline(blocks_file: str) -> str:
    """
    提取文档目录结构

    Args:
        blocks_file: 文档块 JSON 文件路径

    Returns:
        Markdown 格式的目录
    """
    processor = DocumentProcessor()

    with open(blocks_file, 'r', encoding='utf-8') as f:
        blocks = json.load(f)

    return processor.get_outline(blocks)
```

**Step 2: Commit**

```bash
git add skills/feishu-analyst/scripts/document.py
git commit -m "feat(scripts): 添加 document.py 高级文档操作

- save_document(): 保存文档到本地文件
- get_outline(): 提取文档目录结构
- 使用 tempfile.gettempdir() 替代硬编码 /tmp"
```

---

## Task 4: 重命名现有文件

**Files:**
- Rename: `document_processor.py` → `processor.py`
- Rename: `table_processor.py` → `table.py`
- Rename: `setup_feishu.py` → `setup.py`
- Rename: `mcp_client.py` → `_mcp_client_old.py` (临时保留)

**Step 1: 重命名文件**

```bash
cd skills/feishu-analyst/scripts
mv document_processor.py processor.py
mv table_processor.py table.py
mv setup_feishu.py setup.py
mv mcp_client.py _mcp_client_old.py
```

**Step 2: 更新 processor.py 中的导入（如果有）**

检查 processor.py 是否有导入 table_processor，如有则更新为 `from table import ...`

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor(scripts): 重命名文件

- document_processor.py → processor.py
- table_processor.py → table.py
- setup_feishu.py → setup.py
- mcp_client.py → _mcp_client_old.py (临时保留)"
```

---

## Task 5: 创建 `__init__.py` 导出公共 API

**Files:**
- Create: `skills/feishu-analyst/scripts/__init__.py`

**Step 1: 创建 __init__.py**

```python
"""
Feishu MCP Scripts - 公共 API

导出用户在动态场景下使用的 Python API。
"""

from client import FeishuMCPClient
from document import save_document, get_outline

__all__ = [
    "FeishuMCPClient",
    "save_document",
    "get_outline",
]
```

**Step 2: Commit**

```bash
git add skills/feishu-analyst/scripts/__init__.py
git commit -m "feat(scripts): 添加 __init__.py 导出公共 API"
```

---

## Task 6: 删除旧文件

**Files:**
- Delete: `skills/feishu-analyst/scripts/_mcp_client_old.py`

**Step 1: 确认新文件工作正常**

Run: `python skills/feishu-analyst/scripts/cli.py --help`
Expected: 显示帮助信息

**Step 2: 删除旧文件**

```bash
rm skills/feishu-analyst/scripts/_mcp_client_old.py
```

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor(scripts): 删除旧的 mcp_client.py"
```

---

## Task 7: 更新 SKILL.md

**Files:**
- Modify: `skills/feishu-analyst/SKILL.md`

**Step 1: 更新入口选择表格和 Python API 示例**

将 SKILL.md 中的：
- `--fetch` 命令替换为 `cli.py save`
- `--process` 命令替换为 `cli.py outline`
- Python API 示例更新为使用 `from client import ...` 和 `from document import ...`

主要修改：
1. 更新 Quick Start 部分
2. 更新 Python API 示例
3. 删除旧的 CLI 命令示例
4. 更新 CLI 使用说明

**Step 2: Commit**

```bash
git add skills/feishu-analyst/SKILL.md
git commit -m "docs(skill): 更新 SKILL.md 使用新的 API 入口"
```

---

## Task 8: 更新 feishu-prd-analyse.md

**Files:**
- Modify: `commands/feishu-prd-analyse.md`

**Step 1: 更新 CLI 命令**

将：
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/mcp_client.py" --fetch "<FEISHU_URL>"
```

替换为：
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" save "<FEISHU_URL>"
```

将：
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/mcp_client.py" --process /tmp/document_xxx_blocks.json --format markdown
```

替换为：
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" outline /tmp/document_xxx_blocks.json
```

**Step 2: 更新 allowed-tools**

将：
```yaml
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/mcp_client.py:*)"]
```

替换为：
```yaml
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py:*)"]
```

**Step 3: Commit**

```bash
git add commands/feishu-prd-analyse.md
git commit -m "docs(command): 更新 feishu-prd-analyse 使用新 CLI"
```

---

## Task 9: 更新 README.md

**Files:**
- Modify: `README.md`

**Step 1: 更新 CLI 使用示例**

将所有 `mcp_client.py --fetch` 替换为 `cli.py save`
将所有 `mcp_client.py --process` 替换为 `cli.py outline`

**Step 2: 更新项目结构说明**

更新文件结构部分：
```
scripts/
├── __init__.py           # 导出公共 API
├── client.py             # FeishuMCPClient
├── document.py           # save_document(), get_outline()
├── cli.py                # CLI 入口
├── executor.py           # MCP 执行器
├── processor.py          # DocumentProcessor
├── table.py              # TableProcessor
├── validator.py          # 响应验证
├── logger.py             # 日志
└── setup.py              # 凭证配置
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: 更新 README.md 使用新 CLI 和 API"
```

---

## Task 10: 最终验证

**Step 1: 验证 CLI**

```bash
python skills/feishu-analyst/scripts/cli.py --help
python skills/feishu-analyst/scripts/cli.py list
```

**Step 2: 验证 Python API**

```python
import sys
sys.path.insert(0, "skills/feishu-analyst/scripts")
from client import FeishuMCPClient
from document import save_document, get_outline
print("API import OK")
```

**Step 3: 最终 Commit**

```bash
git add -A
git commit -m "refactor(scripts): 完成模块重构

- 新增 cli.py 作为 CLI 入口
- 新增 client.py 提供 FeishuMCPClient
- 新增 document.py 提供 save_document/get_outline
- 重命名文件简化命名
- 更新文档"
```

---

## 文件变更总结

| 操作 | 文件 |
|------|------|
| 新增 | `scripts/__init__.py` |
| 新增 | `scripts/client.py` |
| 新增 | `scripts/document.py` |
| 新增 | `scripts/cli.py` |
| 重命名 | `document_processor.py` → `processor.py` |
| 重命名 | `table_processor.py` → `table.py` |
| 重命名 | `setup_feishu.py` → `setup.py` |
| 删除 | `scripts/mcp_client.py` |
| 修改 | `SKILL.md` |
| 修改 | `commands/feishu-prd-analyse.md` |
| 修改 | `README.md` |
