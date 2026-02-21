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

    def describe_tool(self, tool_name: str) -> Optional[Dict]:
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
