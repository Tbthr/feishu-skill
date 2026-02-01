"""
Document Processor for Feishu MCP

Handles large document responses that may exceed token limits.
Uses file-based processing for efficiency.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator
from dataclasses import dataclass


@dataclass
class DocumentInfo:
    """Parsed document information from get_document_info response"""
    document_id: str
    title: str
    doc_type: str  # "document" or "wiki"
    obj_token: Optional[str] = None  # For wiki nodes
    node_token: Optional[str] = None  # For wiki nodes
    space_id: Optional[str] = None  # For wiki nodes


@dataclass
class BlockInfo:
    """Simplified block information"""
    block_id: str
    block_type: int
    block_type_name: str
    text: str
    level: Optional[int] = None  # For headings
    children_count: int = 0


class DocumentProcessor:
    """
    Process Feishu document responses efficiently.

    Key features:
    - Extract document info from both document and wiki types
    - Process large block files incrementally
    - Convert blocks to Markdown or plain text
    - Search within blocks without loading all into memory
    """

    # Block type mapping (from Feishu documentation)
    BLOCK_TYPES = {
        0: "page",
        1: "text",
        2: "heading1",
        3: "heading2",
        4: "heading3",
        5: "heading4",
        6: "heading5",
        7: "heading6",
        8: "heading7",
        9: "heading8",
        10: "heading9",
        11: "bullet",
        12: "ordered",
        13: "code",
        14: "quote",
        15: "todo",
        16: "divider",
        17: "image",
        18: "table",
        19: "callout",
        20: "file",
        21: "video",
        22: "bookmark",
        23: "unknown",
        24: "view",
        25: "bitable",
        26: "mindnote",
        27: "docx",
        28: "sheet",
        29: "folder",
        30: "wiki",
        31: "board",
        32: "calendar",
        33: "group",
        34: "chart",
        35: "poll",
        36: "form",
        37: "flow",
        38: "multi_person",
        39: "bullet_sub",
        40: "ordered_sub",
        41: "todo_sub",
        42: "quote_sub",
        43: "whiteboard",
        45: "chat",
        46: "link_card",
        47: "audio",
    }

    def __init__(self, cache_dir: str = "/tmp/feishu_mcp_cache"):
        """
        Initialize document processor.

        Args:
            cache_dir: Directory to cache large document files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_document_info(self, response: Dict) -> DocumentInfo:
        """
        Parse document info from get_document_info response.

        Handles both document and wiki response types.

        Args:
            response: Raw response from get_feishu_document_info

        Returns:
            DocumentInfo with parsed information
        """
        doc_type = response.get("_type", "document")

        if doc_type == "wiki":
            # Wiki response is flat structure
            return DocumentInfo(
                document_id=response.get("documentId", response.get("obj_token", "")),
                title=response.get("title", ""),
                doc_type="wiki",
                obj_token=response.get("obj_token"),
                node_token=response.get("node_token"),
                space_id=response.get("space_id")
            )
        else:
            # Document response has nested structure
            doc_data = response.get("document", response)
            return DocumentInfo(
                document_id=doc_data.get("document_id", ""),
                title=doc_data.get("title", ""),
                doc_type="document"
            )

    def get_document_id_for_blocks(self, doc_info_response: Dict) -> str:
        """
        Get the correct document ID to use for get_document_blocks.

        For wiki nodes, this is the obj_token value.
        For documents, this is the document_id.

        Args:
            doc_info_response: Response from get_feishu_document_info

        Returns:
            Document ID string to use for get_document_blocks
        """
        info = self.parse_document_info(doc_info_response)
        if info.doc_type == "wiki" and info.obj_token:
            return info.obj_token
        return info.document_id

    def normalize_blocks(self, raw_blocks: Any) -> List:
        """
        Normalize various Feishu MCP response formats to standard block list.

        Feishu MCP may return blocks in different formats:
        1. Direct array of blocks
        2. Wrapped format: [{"type": "text", "text": "<JSON string>"}]
        3. Wrapped format with extra text (e.g., whiteboard hints)

        Args:
            raw_blocks: Raw response from get_document_blocks

        Returns:
            Normalized list of block objects
        """
        # Check if it's the wrapped format
        if isinstance(raw_blocks, list) and len(raw_blocks) == 1:
            first = raw_blocks[0]
            if isinstance(first, dict) and "text" in first:
                text_content = first["text"]
                if isinstance(text_content, str):
                    # Try parsing the full text content first
                    try:
                        parsed = json.loads(text_content)
                        if isinstance(parsed, list):
                            return parsed
                    except json.JSONDecodeError:
                        # If parsing fails, try extracting JSON from text with extra content
                        # Feishu MCP sometimes appends hint text after the JSON
                        json_part = self._extract_json_from_text(text_content)
                        if json_part:
                            try:
                                parsed = json.loads(json_part)
                                if isinstance(parsed, list):
                                    return parsed
                            except json.JSONDecodeError:
                                pass

        # Return as-is if it's already a block array
        if isinstance(raw_blocks, list):
            return raw_blocks

        # Return empty list for unknown format
        return []

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON array from text that may have extra content after it.

        Finds the first complete JSON array by matching brackets.

        Args:
            text: Text that starts with JSON but may have extra content

        Returns:
            JSON string or None if not found
        """
        if not text.startswith('['):
            return None

        bracket_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        return text[:i + 1]

        return None

    def save_blocks_to_file(self, blocks: List, document_id: str) -> Path:
        """
        Save blocks to a JSON file for efficient processing.

        Args:
            blocks: Raw blocks response from get_feishu_document_blocks
            document_id: Document ID for filename

        Returns:
            Path to the saved file
        """
        filename = f"blocks_{document_id}.json"
        filepath = self.cache_dir / filename

        # Normalize before saving
        normalized = self.normalize_blocks(blocks)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        return filepath

    def load_blocks_from_file(self, filepath: str) -> List:
        """Load blocks from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def iter_blocks(self, blocks: List, max_depth: int = 100) -> Iterator[BlockInfo]:
        """
        Iterate through all blocks in a document tree.

        Yields blocks one at a time to avoid loading everything into memory.

        Args:
            blocks: Block array from get_document_blocks (raw or normalized)
            max_depth: Maximum recursion depth

        Yields:
            BlockInfo for each block
        """
        # Normalize the input first
        normalized_blocks = self.normalize_blocks(blocks)

        def traverse(block_list, depth=0):
            if depth > max_depth:
                return
            for block in block_list:
                # Skip string entries (block IDs in children arrays)
                if not isinstance(block, dict):
                    continue

                block_id = block.get("block_id", "")
                block_type = block.get("block_type", 0)
                block_type_name = self.BLOCK_TYPES.get(block_type, f"unknown_{block_type}")

                # Extract text content
                # Handle various text field formats
                text = ""
                if "text" in block and block["text"]:
                    text_data = block["text"]
                    if isinstance(text_data, str):
                        # text is a string (may contain JSON)
                        text = text_data
                    elif isinstance(text_data, dict):
                        # text is an object - try different field names
                        # Feishu uses "elements" (not "textElements")
                        text_elements = text_data.get("elements") or text_data.get("textElements", [])
                        if text_elements:
                            text = "".join(
                                elem.get("text_run", {}).get("content", "")
                                for elem in text_elements
                            )

                # Also check heading fields (heading1, heading2, etc.)
                for h in ["heading1", "heading2", "heading3", "heading4", "heading5", "heading6", "heading7", "heading8", "heading9"]:
                    if h in block and isinstance(block[h], dict):
                        heading_data = block[h]
                        elements = heading_data.get("elements") or heading_data.get("textElements", [])
                        if elements:
                            heading_text = "".join(
                                elem.get("text_run", {}).get("content", "")
                                for elem in elements
                            )
                            if heading_text and not text:
                                text = heading_text
                            break

                # Check code blocks
                if "code" in block and isinstance(block["code"], dict):
                    code_text = block["code"].get("code", "")
                    if code_text and not text:
                        text = code_text

                # Check list items (bullet, ordered, todo)
                # List items use "bullet" field with elements
                if "bullet" in block and isinstance(block["bullet"], dict):
                    bullet_data = block["bullet"]
                    bullet_elements = bullet_data.get("elements") or bullet_data.get("textElements", [])
                    if bullet_elements and not text:
                        bullet_text = "".join(
                            elem.get("text_run", {}).get("content", "")
                            for elem in bullet_elements
                        )
                        text = bullet_text

                # Get heading level if applicable
                level = None
                if 2 <= block_type <= 10:
                    level = block_type - 1  # heading1 -> level 1

                # Count children
                children = block.get("children", [])
                children_count = len(children) if children else 0

                yield BlockInfo(
                    block_id=block_id,
                    block_type=block_type,
                    block_type_name=block_type_name,
                    text=text,
                    level=level,
                    children_count=children_count
                )

                # Recursively process children
                if children:
                    yield from traverse(children, depth + 1)

        yield from traverse(normalized_blocks)

    def to_markdown(self, blocks: List, max_depth: int = 100) -> str:
        """
        Convert document blocks to Markdown format.

        Args:
            blocks: Block array from get_document_blocks
            max_depth: Maximum recursion depth

        Returns:
            Markdown string
        """
        lines = []

        for block in self.iter_blocks(blocks, max_depth):
            text = block.text

            if block.block_type == 1:  # text
                if text:
                    lines.append(text)
                    lines.append("")  # Blank line after paragraph

            elif 2 <= block.block_type <= 10:  # headings
                level = block.level
                prefix = "#" * level
                lines.append(f"{prefix} {text}")
                lines.append("")

            elif block.block_type in (11, 39):  # bullet, bullet_sub
                lines.append(f"- {text}")

            elif block.block_type in (12, 40):  # ordered, ordered_sub
                lines.append(f"1. {text}")

            elif block.block_type == 13:  # code
                lines.append("```")
                lines.append(text)
                lines.append("```")
                lines.append("")

            elif block.block_type == 14:  # quote
                lines.append(f"> {text}")
                lines.append("")

            elif block.block_type == 15:  # todo
                lines.append(f"- [ ] {text}")

            elif block.block_type == 16:  # divider
                lines.append("---")
                lines.append("")

            elif block.block_type == 17:  # image
                if text:
                    lines.append(f"[Image: {text}]")
                else:
                    lines.append("[Image]")
                lines.append("")

            elif block.block_type == 18:  # table
                lines.append(f"[Table with {block.children_count} cells]")
                lines.append("")

        return "\n".join(lines)

    def extract_text(self, blocks: List, max_depth: int = 100) -> str:
        """
        Extract plain text from document blocks.

        Args:
            blocks: Block array from get_document_blocks
            max_depth: Maximum recursion depth

        Returns:
            Plain text content
        """
        texts = []
        for block in self.iter_blocks(blocks, max_depth):
            if block.text:
                texts.append(block.text)

        return "\n\n".join(texts)

    def find_blocks_by_type(self, blocks: List, block_type: int) -> List[BlockInfo]:
        """
        Find all blocks of a specific type.

        Args:
            blocks: Block array from get_document_blocks
            block_type: Block type number (e.g., 2 for heading1)

        Returns:
            List of BlockInfo matching the type
        """
        return [b for b in self.iter_blocks(blocks) if b.block_type == block_type]

    def search_blocks(self, blocks: List, query: str,
                     case_sensitive: bool = False) -> List[BlockInfo]:
        """
        Search for blocks containing specific text.

        Args:
            blocks: Block array from get_document_blocks
            query: Search query
            case_sensitive: Whether to use case-sensitive search

        Returns:
            List of BlockInfo containing the query
        """
        if not case_sensitive:
            query = query.lower()

        results = []
        for block in self.iter_blocks(blocks):
            text = block.text if case_sensitive else block.text.lower()
            if query in text:
                results.append(block)

        return results

    def get_outline(self, blocks: List) -> str:
        """
        Get document outline from headings.

        Args:
            blocks: Block array from get_document_blocks

        Returns:
            Outline string with heading hierarchy
        """
        lines = []
        for block in self.iter_blocks(blocks):
            if 2 <= block.block_type <= 10:  # Is heading
                indent = "  " * (block.level - 1)
                lines.append(f"{indent}{block.level}. {block.text}")

        return "\n".join(lines)

    def get_document_summary(self, blocks: List) -> Dict:
        """
        Get a summary of document structure.

        Args:
            blocks: Block array from get_document_blocks

        Returns:
            Dict with document statistics
        """
        block_type_counts = {}
        total_text_length = 0
        block_count = 0

        for block in self.iter_blocks(blocks):
            block_count += 1
            block_type_counts[block.block_type_name] = \
                block_type_counts.get(block.block_type_name, 0) + 1
            total_text_length += len(block.text)

        return {
            "total_blocks": block_count,
            "block_type_distribution": block_type_counts,
            "total_text_length": total_text_length,
            "estimated_reading_time_minutes": total_text_length / 500
        }


# Convenience functions
def extract_document_id(doc_info_response: Dict) -> str:
    """Get the correct document ID for blocks from document info response."""
    processor = DocumentProcessor()
    return processor.get_document_id_for_blocks(doc_info_response)


def blocks_to_markdown(blocks: List) -> str:
    """Quick conversion of blocks to Markdown."""
    processor = DocumentProcessor()
    return processor.to_markdown(blocks)


def get_document_outline(blocks: List) -> str:
    """Quick extraction of document outline."""
    processor = DocumentProcessor()
    return processor.get_outline(blocks)
