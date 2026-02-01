"""
Universal Response Validator for Feishu MCP

This module provides common validation and error handling for ALL Feishu MCP tools.
It's the "universal layer" that every MCP response should pass through.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class ValidationResult:
    """Result of MCP response validation"""
    is_valid: bool
    has_error: bool
    error_message: Optional[str] = None
    error_data: Optional[Dict] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class MCPResponseValidator:
    """
    Universal validator for Feishu MCP responses.

    All Feishu MCP responses follow similar patterns:
    - Errors are typically nested in dict values with an "error" key
    - Successful responses have specific keys per tool type
    - Some responses are paginated with "has_more" and "page_token"
    """

    # Expected keys for each tool type
    # Note: get_feishu_document_info returns different structures for document vs wiki
    # - Wiki: title, documentId, node_token, obj_token, space_id, _type="wiki"
    # - Document: title, document_id, type, url
    EXPECTED_KEYS = {
        "get_feishu_document_info": ["title"],  # Only require title, structure varies by type
        "get_feishu_document_blocks": ["blocks"],
        "search_feishu_documents": ["items"],
        "get_feishu_root_folder_info": ["root_folder", "wiki_spaces", "my_library"],
        "get_feishu_folder_files": ["items"],
        "create_feishu_document": ["document_id", "url", "title"],
        "create_feishu_folder": ["token", "url"],
        "batch_create_feishu_blocks": ["blocks"],
        "create_feishu_table": ["table_id"],
        "get_feishu_whiteboard_content": ["elements"],
    }

    # Error messages that indicate authorization issues
    AUTH_ERROR_PATTERNS = [
        "请在浏览器打开以下链接进行授权",
        "authorization",
        "unauthorized",
        "401",
        "403"
    ]

    def __init__(self, log_dir: str = None):
        """
        Initialize validator.

        Args:
            log_dir: Directory to save raw responses for debugging
        """
        self.log_dir = Path(log_dir) if log_dir else Path("/tmp/feishu_mcp_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def validate(self, response: Any, tool_name: str = None) -> ValidationResult:
        """
        Validate a Feishu MCP response.

        Args:
            response: Raw response from MCP tool
            tool_name: Name of the tool that was called

        Returns:
            ValidationResult with validation status and any errors
        """
        result = ValidationResult(is_valid=True, has_error=False)

        # Check for error patterns in response
        error = self._extract_error(response)
        if error:
            result.has_error = True
            result.error_message = error
            result.is_valid = False

            # Check if it's an authorization error
            if self._is_auth_error(error):
                result.error_data = {"type": "authorization_required"}

            return result

        # Validate expected structure if tool_name provided
        if tool_name and result.is_valid:
            expected_keys = self.EXPECTED_KEYS.get(tool_name, [])
            if expected_keys:
                missing_keys = self._check_keys(response, expected_keys)
                if missing_keys:
                    result.warnings.append(
                        f"Missing expected keys: {missing_keys}"
                    )

        return result

    def _extract_error(self, response: Any) -> Optional[str]:
        """
        Extract error message from response.

        Feishu MCP errors can appear in several patterns:
        1. Direct error: {"error": "message"}
        2. Nested error: {"root_folder": {"error": "message"}}
        3. Error field with code: {"error": "message", "code": -1}
        """
        if response is None:
            return "Response is None"

        # Direct error
        if isinstance(response, dict):
            # Check top-level error
            if "error" in response:
                return response.get("error")

            # Check nested errors (common in Feishu responses)
            for key, value in response.items():
                if isinstance(value, dict) and "error" in value:
                    return value["error"]

                # Check for error in arrays
                if isinstance(value, list) and value:
                    for item in value:
                        if isinstance(item, dict) and "error" in item:
                            return item["error"]

        return None

    def _is_auth_error(self, error_message: str) -> bool:
        """Check if error is authorization-related"""
        error_lower = error_message.lower()
        return any(pattern.lower() in error_lower
                  for pattern in self.AUTH_ERROR_PATTERNS)

    def _check_keys(self, response: Dict, expected_keys: List[str]) -> List[str]:
        """Check which expected keys are missing from response"""
        if not isinstance(response, dict):
            return expected_keys

        missing = []
        for key in expected_keys:
            if key not in response:
                missing.append(key)
        return missing

    def log_response(self, tool_name: str, response: Any,
                     params: Dict = None) -> str:
        """
        Persist raw response to file for debugging and analysis.

        Args:
            tool_name: Name of the MCP tool
            response: Raw response data
            params: Parameters passed to the tool

        Returns:
            Path to the saved log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{tool_name}_{timestamp}.json"
        filepath = self.log_dir / filename

        log_data = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "params": params or {},
            "response": response
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)

        return str(filepath)

    def get_error_help(self, result: ValidationResult) -> str:
        """
        Get helpful message for validation result.

        Args:
            result: ValidationResult from validate()

        Returns:
            Helpful error message
        """
        if not result.has_error:
            return "Response is valid"

        if result.error_data and result.error_data.get("type") == "authorization_required":
            return (
                "Authorization Required\n"
                "The Feishu MCP server needs user authorization.\n"
                "Please check the MCP response for the authorization link."
            )

        return f"Error: {result.error_message}"


# Convenience functions
def validate_response(response: Any, tool_name: str = None) -> ValidationResult:
    """Quick validation without instantiating validator"""
    validator = MCPResponseValidator()
    return validator.validate(response, tool_name)


def extract_error(response: Any) -> Optional[str]:
    """Quick error extraction"""
    validator = MCPResponseValidator()
    return validator._extract_error(response)
