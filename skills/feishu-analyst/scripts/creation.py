"""
Creation Processor for Feishu MCP

Handles responses from document/folder/block creation operations.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class CreationResult:
    """Result from a creation operation"""
    success: bool
    item_id: str
    item_type: str  # "document", "folder", "block", "table"
    url: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    raw_response: Dict = None


class CreationProcessor:
    """
    Process creation responses from Feishu MCP.

    Creation operations return:
    - Document: document_id, url, title
    - Folder: token, url
    - Blocks: array of created block info
    - Table: table_id
    """

    def __init__(self, cache_dir: str = "/tmp/feishu_mcp_cache"):
        """
        Initialize creation processor.

        Args:
            cache_dir: Directory to cache creation results
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_document_creation(self, response: Dict) -> CreationResult:
        """
        Parse response from create_feishu_document.

        Args:
            response: Raw response from create_feishu_document

        Returns:
            CreationResult with document info
        """
        # Check for error
        if "error" in response:
            return CreationResult(
                success=False,
                item_id="",
                item_type="document",
                error=response.get("error"),
                raw_response=response
            )

        return CreationResult(
            success=True,
            item_id=response.get("document_id", ""),
            item_type="document",
            url=response.get("url", ""),
            title=response.get("title", ""),
            raw_response=response
        )

    def parse_folder_creation(self, response: Dict) -> CreationResult:
        """
        Parse response from create_feishu_folder.

        Args:
            response: Raw response from create_feishu_folder

        Returns:
            CreationResult with folder info
        """
        if "error" in response:
            return CreationResult(
                success=False,
                item_id="",
                item_type="folder",
                error=response.get("error"),
                raw_response=response
            )

        return CreationResult(
            success=True,
            item_id=response.get("token", ""),
            item_type="folder",
            url=response.get("url", ""),
            raw_response=response
        )

    def parse_blocks_creation(self, response: Dict) -> CreationResult:
        """
        Parse response from batch_create_feishu_blocks.

        Args:
            response: Raw response from batch_create_feishu_blocks

        Returns:
            CreationResult with blocks info
        """
        if "error" in response:
            return CreationResult(
                success=False,
                item_id="",
                item_type="block",
                error=response.get("error"),
                raw_response=response
            )

        # Get first block ID as reference
        blocks = response.get("blocks", [])
        first_block_id = blocks[0].get("block_id", "") if blocks else ""

        return CreationResult(
            success=True,
            item_id=first_block_id,
            item_type="block",
            raw_response=response
        )

    def parse_table_creation(self, response: Dict) -> CreationResult:
        """
        Parse response from create_feishu_table.

        Args:
            response: Raw response from create_feishu_table

        Returns:
            CreationResult with table info
        """
        if "error" in response:
            return CreationResult(
                success=False,
                item_id="",
                item_type="table",
                error=response.get("error"),
                raw_response=response
            )

        return CreationResult(
            success=True,
            item_id=response.get("table_id", ""),
            item_type="table",
            raw_response=response
        )

    def format_success_message(self, result: CreationResult) -> str:
        """
        Format a user-friendly success message.

        Args:
            result: CreationResult

        Returns:
            Formatted message string
        """
        if not result.success:
            return f"❌ Failed to create {result.item_type}: {result.error}"

        type_names = {
            "document": "Document",
            "folder": "Folder",
            "block": "Content block",
            "table": "Table"
        }

        lines = [
            f"✅ {type_names.get(result.item_type, result.item_type)} created successfully!"
        ]

        if result.title:
            lines.append(f"Title: {result.title}")

        lines.append(f"ID: {result.item_id}")

        if result.url:
            lines.append(f"URL: {result.url}")

        return "\n".join(lines)

    def save_creation_result(self, result: CreationResult,
                            operation: str) -> Path:
        """
        Save creation result to file for reference.

        Args:
            result: CreationResult to save
            operation: Description of the operation

        Returns:
            Path to saved file
        """
        import hashlib
        from datetime import datetime

        # Create filename from operation and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        op_hash = hashlib.md5(operation.encode()).hexdigest()[:8]
        filename = f"creation_{result.item_type}_{op_hash}_{timestamp}.json"
        filepath = self.cache_dir / filename

        data = {
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "item_type": result.item_type,
            "item_id": result.item_id,
            "url": result.url,
            "title": result.title,
            "error": result.error,
            "raw_response": result.raw_response
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath


# Convenience functions
def extract_document_id(create_response: Dict) -> str:
    """Quick extraction of document ID from creation response."""
    processor = CreationProcessor()
    result = processor.parse_document_creation(create_response)
    return result.item_id if result.success else ""


def extract_folder_id(create_response: Dict) -> str:
    """Quick extraction of folder token from creation response."""
    processor = CreationProcessor()
    result = processor.parse_folder_creation(create_response)
    return result.item_id if result.success else ""
