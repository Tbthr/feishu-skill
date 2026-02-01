"""
MCP Logger for Feishu

Persistent logging for all MCP tool calls.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class MCPCallRecord:
    """Record of a single MCP tool call"""
    tool_name: str
    timestamp: str
    success: bool
    params: Dict
    response_summary: str
    response_size: int
    error: Optional[str] = None
    saved_to_file: Optional[str] = None


class MCPLogger:
    """
    Logger for Feishu MCP tool calls.

    Provides persistent logging of all MCP interactions for:
    - Debugging
    - Analysis of response patterns
    - Token usage optimization
    """

    def __init__(self, log_dir: str = "/tmp/feishu_mcp_logs"):
        """
        Initialize MCP logger.

        Args:
            log_dir: Directory to store logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "mcp_calls.jsonl"

    def log_call(self, tool_name: str, params: Dict,
                response: Any, error: str = None) -> MCPCallRecord:
        """
        Log an MCP tool call.

        Args:
            tool_name: Name of the MCP tool
            params: Parameters passed to the tool
            response: Response from the tool
            error: Error message if call failed

        Returns:
            MCPCallRecord with call details
        """
        timestamp = datetime.now().isoformat()
        success = error is None

        # Calculate response size
        response_str = json.dumps(response, ensure_ascii=False, default=str)
        response_size = len(response_str.encode('utf-8'))

        # Create summary
        if error:
            summary = f"Error: {error[:200]}"
        elif isinstance(response, dict):
            if "error" in response:
                summary = f"API Error: {response['error'][:200]}"
            else:
                keys = list(response.keys())[:5]
                summary = f"Dict with keys: {keys}"
        elif isinstance(response, list):
            summary = f"Array with {len(response)} items"
        else:
            summary = str(response)[:200]

        record = MCPCallRecord(
            tool_name=tool_name,
            timestamp=timestamp,
            success=success,
            params=params,
            response_summary=summary,
            response_size=response_size,
            error=error
        )

        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

        return record

    def save_large_response(self, tool_name: str, response: Any) -> Path:
        """
        Save a large response to a separate file.

        Args:
            tool_name: Name of the tool
            response: Response data

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{tool_name}_{timestamp}.json"
        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2, default=str)

        return filepath

    def get_stats(self) -> Dict:
        """
        Get statistics about logged calls.

        Returns:
            Dict with call statistics
        """
        if not self.log_file.exists():
            return {"total_calls": 0}

        stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "tools_used": {},
            "total_response_bytes": 0
        }

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    stats["total_calls"] += 1

                    if record.get("success"):
                        stats["successful_calls"] += 1
                    else:
                        stats["failed_calls"] += 1

                    tool = record.get("tool_name", "unknown")
                    stats["tools_used"][tool] = \
                        stats["tools_used"].get(tool, 0) + 1

                    stats["total_response_bytes"] += \
                        record.get("response_size", 0)

                except json.JSONDecodeError:
                    continue

        return stats

    def get_recent_calls(self, limit: int = 10) -> list:
        """
        Get recent call records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent MCPCallRecord dicts
        """
        if not self.log_file.exists():
            return []

        records = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        # Return last N records
        return records[-limit:]


# Convenience function for quick logging
def log_mcp_call(tool_name: str, params: Dict,
                response: Any, error: str = None) -> str:
    """
    Quick log function that returns a summary string.

    Args:
        tool_name: Name of the MCP tool
        params: Parameters passed to the tool
        response: Response from the tool
        error: Error message if call failed

    Returns:
        Summary string
    """
    logger = MCPLogger()
    record = logger.log_call(tool_name, params, response, error)

    status = "✅" if record.success else "❌"
    size_kb = record.response_size / 1024

    return f"{status} {tool_name} ({size_kb:.1f} KB)"
