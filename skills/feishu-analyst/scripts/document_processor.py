"""
Document Processor for Feishu MCP

Handles large document responses that may exceed token limits.
Uses file-based processing for efficiency.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator, Tuple
from dataclasses import dataclass, field


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
class InlineStyle:
    """Inline style information"""
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    code: bool = False
    link: Optional[str] = None
    underline: bool = False
    # Combined text with markdown styles applied
    styled_text: str = ""


@dataclass
class BlockInfo:
    """Simplified block information"""
    block_id: str
    block_type: int
    block_type_name: str
    text: str
    level: Optional[int] = None  # For headings
    children_count: int = 0
    # Text with inline styles applied (Markdown formatted)
    inline_text: str = ""
    # For todo/checkbox blocks
    checked: bool = False


class DocumentProcessor:
    """
    Process Feishu document responses efficiently.

    Key features:
    - Extract document info from both document and wiki types
    - Process large block files incrementally
    - Convert blocks to Markdown or plain text
    - Search within blocks without loading all into memory
    """

    # Block type mapping (based on actual Feishu API responses)
    BLOCK_TYPES = {
        1: "page",
        2: "text",
        3: "heading1",
        4: "heading2",
        5: "heading3",
        6: "heading4",
        7: "heading5",
        8: "heading6",
        9: "heading7",
        10: "heading8",
        11: "heading9",
        12: "bullet",         # bullet and ordered both use 'bullet' field
        13: "ordered",
        14: "code",
        15: "quote",
        16: "todo",
        17: "divider",
        18: "image",
        19: "table",
        # Additional types from documentation
        20: "callout",
        21: "file",
        22: "video",
        23: "bookmark",
        24: "view",
        25: "bitable",
        26: "mindnote",
        27: "docx",
        28: "sheet",
        29: "folder",
        30: "wiki",
        31: "table",          # Actual table block type in API responses
        32: "table_cell",     # Table cell
        33: "calendar",
        34: "group",
        35: "chart",
        36: "poll",
        37: "form",
        38: "flow",
        39: "multi_person",
        40: "bullet_sub",
        41: "ordered_sub",
        42: "todo_sub",
        43: "whiteboard",     # board/whiteboard
        44: "chat",
        45: "link_card",
        46: "audio",
    }

    def __init__(self, cache_dir: str = "/tmp/feishu_mcp_cache",
                 enable_logging: bool = False,
                 log_level: int = logging.INFO):
        """
        Initialize document processor.

        Args:
            cache_dir: Directory to cache large document files
            enable_logging: Enable detailed logging for diagnostics (default: False)
            log_level: Logging level (default: INFO)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Setup logger (optional, backward compatible)
        self.enable_logging = enable_logging
        self.logger = None
        if enable_logging:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(log_level)

            # Avoid duplicate handlers
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

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

    def detect_response_format(self, raw_blocks: Any) -> str:
        """
        Detect the format of Feishu MCP response for debugging.

        Args:
            raw_blocks: Raw response from get_document_blocks

        Returns:
            Format description string
        """
        if not isinstance(raw_blocks, list):
            return "UNKNOWN_NOT_LIST"

        if len(raw_blocks) == 0:
            return "EMPTY_LIST"

        # Check if it looks like a normal block array first
        if isinstance(raw_blocks[0], dict):
            if "block_id" in raw_blocks[0] or "block_type" in raw_blocks[0]:
                return "NORMAL_BLOCK_ARRAY"

        # Then check for wrapped format
        if len(raw_blocks) == 1:
            first = raw_blocks[0]
            if isinstance(first, dict):
                if "text" in first:
                    text_content = first["text"]
                    if isinstance(text_content, str):
                        if text_content.startswith('['):
                            return "WRAPPED_JSON_IN_TEXT"
                        else:
                            return "WRAPPED_TEXT_WITH_HINTS"
                return "SINGLE_DICT_WITHOUT_TEXT"
            return "SINGLE_NON_DICT"

        return "MULTI_ITEM_UNKNOWN_FORMAT"

    def normalize_blocks(self, raw_blocks: Any) -> List:
        """
        Normalize various Feishu MCP response formats to standard block list.

        Enhanced with detailed logging for debugging response format issues.
        """
        if self.logger:
            format_type = self.detect_response_format(raw_blocks)
            self.logger.info(f"normalize_blocks: Detected format '{format_type}'")

            if isinstance(raw_blocks, list):
                self.logger.debug(f"normalize_blocks: Input has {len(raw_blocks)} items")

        # Check if it's the wrapped format
        if isinstance(raw_blocks, list) and len(raw_blocks) == 1:
            first = raw_blocks[0]

            if self.logger:
                self.logger.debug(f"normalize_blocks: Single item with keys: {list(first.keys()) if isinstance(first, dict) else 'N/A'}")

            if isinstance(first, dict) and "text" in first:
                text_content = first["text"]

                if self.logger:
                    text_preview = text_content[:100] if isinstance(text_content, str) else str(text_content)[:100]
                    self.logger.debug(f"normalize_blocks: Text preview: {text_preview}...")

                if isinstance(text_content, str):
                    # Try parsing the full text content first
                    try:
                        if self.logger:
                            self.logger.debug("normalize_blocks: Attempting direct JSON parse")

                        parsed = json.loads(text_content)
                        if isinstance(parsed, list):
                            if self.logger:
                                self.logger.info(f"normalize_blocks: Successfully parsed {len(parsed)} blocks from wrapped JSON")
                            return parsed
                        else:
                            if self.logger:
                                self.logger.warning(f"normalize_blocks: Parsed JSON but not a list (type: {type(parsed).__name__})")

                    except json.JSONDecodeError as e:
                        if self.logger:
                            self.logger.debug(f"normalize_blocks: Direct parse failed: {e}")
                            self.logger.debug("normalize_blocks: Attempting bracket matching extraction")

                        # Try extracting JSON from text with extra content
                        json_part = self._extract_json_from_text(text_content)

                        if json_part is None:
                            if self.logger:
                                self.logger.error(
                                    f"normalize_blocks: Failed to extract JSON\n"
                                    f"  Text preview (first 200 chars): {text_content[:200]}\n"
                                    f"  Text length: {len(text_content)} chars"
                                )
                        else:
                            if self.logger:
                                self.logger.info(f"normalize_blocks: Extracted {len(json_part)} chars via bracket matching")

                            try:
                                parsed = json.loads(json_part)
                                if isinstance(parsed, list):
                                    if self.logger:
                                        self.logger.info(f"normalize_blocks: Successfully parsed {len(parsed)} blocks after extraction")
                                    return parsed
                                else:
                                    if self.logger:
                                        self.logger.warning(f"normalize_blocks: Extracted JSON but not a list (type: {type(parsed).__name__})")

                            except json.JSONDecodeError as e:
                                if self.logger:
                                    self.logger.error(
                                        f"normalize_blocks: Failed to parse extracted JSON: {e}\n"
                                        f"  Extracted preview (first 200 chars): {json_part[:200]}"
                                    )

        # Return as-is if it's already a block array
        if isinstance(raw_blocks, list):
            if self.logger:
                self.logger.info(f"normalize_blocks: Returning raw list as-is ({len(raw_blocks)} items)")

                if raw_blocks and isinstance(raw_blocks[0], dict):
                    has_block_id = "block_id" in raw_blocks[0]
                    has_block_type = "block_type" in raw_blocks[0]
                    self.logger.debug(f"normalize_blocks: First item has block_id={has_block_id}, block_type={has_block_type}")

            return raw_blocks

        # Return empty list for unknown format
        if self.logger:
            self.logger.warning(
                f"normalize_blocks: Unknown format, returning empty list\n"
                f"  Input type: {type(raw_blocks).__name__}\n"
                f"  Input preview: {str(raw_blocks)[:200]}"
            )

        return []

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON array from text that may have extra content after it.

        Enhanced with detailed logging for bracket matching process.
        """
        if self.logger:
            self.logger.debug(f"_extract_json_from_text: Input length={len(text)}, starts_with '['={text.startswith('[')}")

        if not text.startswith('['):
            if self.logger:
                self.logger.debug(
                    f"_extract_json_from_text: Text doesn't start with '[', returning None\n"
                    f"  First 50 chars: {text[:50]}"
                )
            return None

        bracket_count = 0
        in_string = False
        escape_next = False

        if self.logger:
            self.logger.debug("_extract_json_from_text: Starting bracket matching")

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

                    if self.logger and bracket_count in [1, 2, 3]:
                        self.logger.debug(f"_extract_json_from_text: Bracket count={bracket_count} at position {i}")

                    if bracket_count == 0:
                        result = text[:i + 1]

                        if self.logger:
                            self.logger.info(
                                f"_extract_json_from_text: Successfully matched brackets\n"
                                f"  Extracted length: {len(result)} chars\n"
                                f"  Position: {i}\n"
                                f"  Preview: {result[:100]}..."
                            )

                        return result

        if self.logger:
            self.logger.error(
                f"_extract_json_from_text: Failed to match brackets\n"
                f"  Final bracket_count: {bracket_count}\n"
                f"  in_string: {in_string}\n"
                f"  Text length: {len(text)}\n"
                f"  Last 200 chars: {text[-200:]}"
            )

        return None

    def _extract_text_with_styles(self, text_data: Dict) -> str:
        """
        Extract text content with inline styles converted to Markdown.

        Handles: bold, italic, strikethrough, underline, code, links

        Args:
            text_data: Text data dict from Feishu API (contains 'elements')

        Returns:
            Markdown formatted text with inline styles
        """
        elements = text_data.get("elements") or text_data.get("textElements", [])
        if not elements:
            return ""

        result_parts = []

        for elem in elements:
            text_run = elem.get("text_run", {})
            content = text_run.get("content", "")

            if not content:
                # Check for inline component (like mentions, links)
                inline_component = elem.get("inline_component", {})
                if inline_component:
                    component_type = inline_component.get("type", "")
                    if component_type == "mention_doc":
                        # Document mention as link
                        url = inline_component.get("raw_url", "")
                        title = inline_component.get("title", content)
                        if url:
                            result_parts.append(f"[{title}]({url})")
                            continue
                    elif component_type == "user":
                        # User mention - render as @name or code
                        user_name = text_run.get("content", "@user")
                        result_parts.append(f"`{user_name}`")
                        continue

            # Check for link in text_run (some API versions put link here)
            link = text_run.get("link")
            if link:
                content = f"[{content}]({link})"

            # Get text element style
            style = text_run.get("text_element_style", {})

            # Apply styles in correct order (strikethrough -> underline -> italic -> bold)
            # Note: Markdown doesn't support underline, we'll use HTML for that
            if style.get("strikethrough"):
                content = f"~~{content}~~"
            if style.get("underline"):
                content = f"<u>{content}</u>"
            if style.get("italic"):
                content = f"*{content}*"
            if style.get("bold"):
                content = f"**{content}**"

            # Check for inline code (code style)
            if style.get("code"):
                content = f"`{content}`"

            # Check for color/background (use HTML for these)
            color = style.get("color")
            bg_color = style.get("background")
            if color or bg_color:
                color_style = f"color:{color}" if color else ""
                bg_style = f"background-color:{bg_color}" if bg_color else ""
                styles = ";".join(s for s in [color_style, bg_style] if s)
                content = f'<span style="{styles}">{content}</span>'

            result_parts.append(content)

        return "".join(result_parts)

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

    def iter_blocks(self, blocks: List, max_depth: int = 100,
                    skip_table_cells: bool = False) -> Iterator[BlockInfo]:
        """
        Iterate through all blocks in a document tree.

        Yields blocks one at a time to avoid loading everything into memory.

        Args:
            blocks: Block array from get_document_blocks (raw or normalized)
            max_depth: Maximum recursion depth
            skip_table_cells: Whether to skip table_cell blocks (default False)

        Yields:
            BlockInfo for each block
        """
        # Normalize the input first
        normalized_blocks = self.normalize_blocks(blocks)

        # Build a set of blocks that are children of table cells (to skip them)
        skip_block_ids = set()
        if skip_table_cells:
            for b in normalized_blocks:
                if isinstance(b, dict) and b.get("block_type") == 32:
                    # This is a table cell, skip it and all its descendants
                    skip_block_ids.add(b.get("block_id", ""))
                    # Also add all children (recursively)
                    def add_descendants(block_dict):
                        children = block_dict.get("children", [])
                        for child_id in children:
                            if isinstance(child_id, str):
                                skip_block_ids.add(child_id)
                                # Find the child block and add its descendants
                                for child_block in normalized_blocks:
                                    if isinstance(child_block, dict) and child_block.get("block_id") == child_id:
                                        add_descendants(child_block)
                                        break

                    add_descendants(b)

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

                # Skip table cells if requested (they're part of table blocks)
                if skip_table_cells and block_type == 32:
                    # Skip this block and don't recurse into children
                    continue

                # Skip children of table cells (they are extracted via _extract_table_markdown)
                if block_id in skip_block_ids:
                    continue

                # Extract text content and inline styles
                # Handle various text field formats
                text = ""
                inline_text = ""
                checked = False

                def extract_from_data(data: Dict, for_inline: bool = False) -> Tuple[str, str]:
                    """Extract plain text and styled text from a data dict.
                    Returns (plain_text, styled_text)
                    """
                    if not data or not isinstance(data, dict):
                        return "", ""

                    elements = data.get("elements") or data.get("textElements", [])
                    if not elements:
                        return "", ""

                    plain_parts = []
                    for elem in elements:
                        text_run = elem.get("text_run", {})
                        content = text_run.get("content", "")

                        # Skip deleted/strikethrough text for plain extraction
                        style = text_run.get("text_element_style", {})
                        if not style.get("strikethrough"):
                            plain_parts.append(content)

                    plain = "".join(plain_parts)

                    if for_inline:
                        styled = self._extract_text_with_styles(data)
                        return plain, styled

                    return plain, ""

                if "text" in block and block["text"]:
                    text_data = block["text"]
                    if isinstance(text_data, str):
                        # text is a string (may contain JSON)
                        text = text_data
                        inline_text = text_data
                    elif isinstance(text_data, dict):
                        plain, styled = extract_from_data(text_data, for_inline=True)
                        text = plain
                        inline_text = styled if styled else plain

                # Also check heading fields (heading1, heading2, etc.)
                for h in ["heading1", "heading2", "heading3", "heading4", "heading5", "heading6", "heading7", "heading8", "heading9"]:
                    if h in block and isinstance(block[h], dict):
                        heading_data = block[h]
                        plain, styled = extract_from_data(heading_data, for_inline=True)
                        if plain and not text:
                            text = plain
                        if styled and not inline_text:
                            inline_text = styled
                        break

                # Check code blocks
                if "code" in block and isinstance(block["code"], dict):
                    code_text = block["code"].get("code", "")
                    if code_text and not text:
                        text = code_text
                        inline_text = code_text

                # Check list items (bullet, ordered, todo)
                # List items use "bullet" field with elements
                if "bullet" in block and isinstance(block["bullet"], dict):
                    bullet_data = block["bullet"]
                    plain, styled = extract_from_data(bullet_data, for_inline=True)
                    if plain and not text:
                        text = plain
                    if styled and not inline_text:
                        inline_text = styled

                    # Check for todo/checkbox done state
                    if block_type == 16:  # todo
                        checked = block.get("todo", {}).get("done", False)

                # Get heading level if applicable
                # heading1 (type=3) -> level=1, heading3 (type=5) -> level=3
                level = None
                if 3 <= block_type <= 11:
                    level = block_type - 2  # heading1 -> level 1

                # Count children
                children = block.get("children", [])
                children_count = len(children) if children else 0

                # For table blocks, don't recursively process children when extract_tables=True
                # because table content is extracted separately
                should_recurse = True
                if skip_table_cells and block_type == 31:
                    should_recurse = False

                yield BlockInfo(
                    block_id=block_id,
                    block_type=block_type,
                    block_type_name=block_type_name,
                    text=text,
                    level=level,
                    children_count=children_count,
                    inline_text=inline_text if inline_text else text,
                    checked=checked
                )

                # Recursively process children
                if should_recurse and children:
                    yield from traverse(children, depth + 1)

        yield from traverse(normalized_blocks)

    def to_markdown(self, blocks: List, max_depth: int = 100,
                    extract_tables: bool = True,
                    extract_whiteboards: bool = False,
                    merge_lists: bool = True) -> str:
        """
        Convert document blocks to Markdown format.

        Args:
            blocks: Block array from get_document_blocks
            max_depth: Maximum recursion depth
            extract_tables: Whether to extract table content (default True)
            extract_whiteboards: Whether to extract whiteboard content (default False)
            merge_lists: Whether to merge consecutive list items (default True)

        Returns:
            Markdown string
        """
        # First pass: collect all blocks as (type, content) tuples
        items = []
        normalized_blocks = self.normalize_blocks(blocks)
        block_map = {b.get("block_id"): b for b in normalized_blocks if isinstance(b, dict)}
        skip_cells = extract_tables

        for block in self.iter_blocks(blocks, max_depth, skip_table_cells=skip_cells):
            # Use inline_text (with styles) instead of plain text
            text = block.inline_text if block.inline_text else block.text
            block_type = block.block_type
            level = block.level
            checked = block.checked

            if block_type == 1:  # page - skip
                items.append(("skip", None, None))
                continue

            elif block_type == 2:  # text/paragraph
                if text:
                    items.append(("paragraph", text, None))

            elif 3 <= block_type <= 11:  # headings (heading1-heading9)
                items.append(("heading", text, level))

            elif block_type == 12:  # bullet
                items.append(("bullet", text, None))

            elif block_type == 13:  # ordered
                items.append(("ordered", text, None))

            elif block_type == 14:  # code
                items.append(("code", text, None))

            elif block_type == 15:  # quote
                items.append(("quote", text, None))

            elif block_type == 16:  # todo
                items.append(("todo", text, checked))

            elif block_type == 17:  # divider
                items.append(("divider", None, None))

            elif block_type == 18:  # image
                if text:
                    items.append(("image", text, None))
                else:
                    items.append(("image", "", None))

            elif block_type == 19:  # callout
                items.append(("callout", text, None))

            elif block_type == 31:  # table
                if extract_tables:
                    table_md = self._extract_table_markdown_with_styles(block.block_id, normalized_blocks, block_map)
                    items.append(("table", table_md, None))
                else:
                    items.append(("table", f"[Table with {block.children_count} cells]", None))

            elif block_type == 43:  # whiteboard
                if extract_whiteboards:
                    block_data = block_map.get(block.block_id, {})
                    board_token = block_data.get("board", {}).get("token", "")
                    if board_token:
                        items.append(("whiteboard", f"[Whiteboard: {board_token}]", None))
                    else:
                        items.append(("whiteboard", "[Whiteboard]", None))
                else:
                    items.append(("whiteboard", f"[Whiteboard/画板]", None))

        # Second pass: merge lists if enabled
        if merge_lists:
            items = self._merge_lists(items)

        # Third pass: render to markdown lines
        lines = []
        for item_type, content, extra in items:
            if item_type == "skip":
                continue
            elif item_type == "paragraph":
                if content:
                    lines.append(content)
                    lines.append("")
            elif item_type == "heading":
                level = extra or 1
                prefix = "#" * level
                lines.append(f"{prefix} {content}")
                lines.append("")
            elif item_type == "bullet":
                lines.append(f"- {content}")
            elif item_type == "ordered":
                lines.append(f"1. {content}")
            elif item_type == "todo":
                checked = extra if extra is not None else False
                checkbox = "- [x]" if checked else "- [ ]"
                lines.append(f"{checkbox} {content}")
            elif item_type == "code":
                lines.append("```")
                lines.append(content)
                lines.append("```")
                lines.append("")
            elif item_type == "quote":
                lines.append(f"> {content}")
                lines.append("")
            elif item_type == "divider":
                lines.append("---")
                lines.append("")
            elif item_type == "image":
                if content:
                    lines.append(f"[Image: {content}]")
                else:
                    lines.append("[Image]")
                lines.append("")
            elif item_type == "callout":
                lines.append(f"> {content}")
                lines.append("")
            elif item_type == "table":
                lines.append(content)
                lines.append("")
            elif item_type == "whiteboard":
                lines.append(content)
                lines.append("")

        return "\n".join(lines)

    def _merge_lists(self, items: List[Tuple[str, str, Any]]) -> List[Tuple[str, str, Any]]:
        """
        Merge consecutive list items into proper Markdown lists.

        Args:
            items: List of (type, content, extra) tuples

        Returns:
            List with merged lists
        """
        result = []
        i = 0

        while i < len(items):
            item_type, content, extra = items[i]

            # Check if this is a list item
            if item_type in ("bullet", "ordered", "todo"):
                # Start of a list - collect consecutive items of same type
                list_type = item_type
                list_items = [(content, extra)]
                j = i + 1

                while j < len(items):
                    next_type, next_content, next_extra = items[j]

                    # Same list type or compatible types
                    if next_type == list_type:
                        list_items.append((next_content, next_extra))
                        j += 1
                    elif next_type in ("bullet", "ordered", "todo"):
                        # Different list type - end current list
                        break
                    else:
                        # Not a list item - end current list
                        break

                # Render the merged list
                if list_type == "bullet":
                    for content, _ in list_items:
                        result.append(("bullet", content, None))
                elif list_type == "ordered":
                    for idx, (content, _) in enumerate(list_items, 1):
                        result.append(("ordered", content, idx))
                elif list_type == "todo":
                    for content, checked in list_items:
                        result.append(("todo", content, checked))

                # Add blank line after list unless next item is also a list
                if j < len(items) and items[j][0] not in ("bullet", "ordered", "todo"):
                    # Insert a marker for blank line
                    result.append(("blank", "", None))

                i = j
            else:
                result.append((item_type, content, extra))
                i += 1

        return result

    def _extract_table_markdown(self, table_block_id: str, blocks: List, block_map: Dict) -> str:
        """
        Extract table content as markdown table.

        Args:
            table_block_id: The block_id of the table block
            blocks: All blocks in the document
            block_map: Mapping of block_id to block data

        Returns:
            Markdown table string
        """
        table_block = block_map.get(table_block_id, {})
        table_data = table_block.get("table", {})

        if not table_data:
            return f"[Table: unable to extract content]"

        # Get table dimensions
        property_data = table_data.get("property", {})
        row_size = property_data.get("row_size", 0)
        column_size = property_data.get("column_size", 0)

        if row_size == 0 or column_size == 0:
            return f"[Table: empty table]"

        # Get cell block IDs
        cell_ids = table_data.get("cells", [])

        # Extract cell content
        cell_contents = []
        for cell_id in cell_ids:
            cell_text = ""
            # Find the cell block and extract its text
            if cell_id in block_map:
                cell_block = block_map[cell_id]
                # Cell content is in children
                children = cell_block.get("children", [])
                if children and children[0] in block_map:
                    child_block = block_map[children[0]]
                    # Extract text from child block
                    for field in ["text", "heading1", "heading2", "heading3", "heading4", "heading5",
                                  "heading6", "heading7", "heading8", "heading9", "bullet"]:
                        if field in child_block and isinstance(child_block[field], dict):
                            field_data = child_block[field]
                            elements = field_data.get("elements", [])
                            cell_text = "".join(
                                elem.get("text_run", {}).get("content", "")
                                for elem in elements
                                # Skip text with strikethrough style
                                if not elem.get("text_run", {}).get("text_element_style", {}).get("strikethrough", False)
                            )
                            if cell_text:
                                break
            cell_contents.append(cell_text.strip() if cell_text.strip() else "")

        # Build markdown table
        md_lines = []

        # Build rows
        for row in range(row_size):
            row_cells = []
            for col in range(column_size):
                idx = row * column_size + col
                if idx < len(cell_contents):
                    cell_text = cell_contents[idx].replace("|", "\\|")  # Escape pipes
                    row_cells.append(cell_text)
                else:
                    row_cells.append("")
            md_lines.append("| " + " | ".join(row_cells) + " |")

            # Add separator after first row (header)
            if row == 0:
                separator = "| " + " | ".join(["---"] * column_size) + " |"
                md_lines.append(separator)

        return "\n".join(md_lines)

    def _extract_table_markdown_with_styles(self, table_block_id: str, blocks: List, block_map: Dict) -> str:
        """
        Extract table content as markdown table with inline styles.

        Args:
            table_block_id: The block_id of the table block
            blocks: All blocks in the document
            block_map: Mapping of block_id to block data

        Returns:
            Markdown table string with styled text
        """
        table_block = block_map.get(table_block_id, {})
        table_data = table_block.get("table", {})

        if not table_data:
            return f"[Table: unable to extract content]"

        # Get table dimensions
        property_data = table_data.get("property", {})
        row_size = property_data.get("row_size", 0)
        column_size = property_data.get("column_size", 0)

        if row_size == 0 or column_size == 0:
            return f"[Table: empty table]"

        # Get cell block IDs
        cell_ids = table_data.get("cells", [])

        # Extract cell content with styles
        cell_contents = []
        for cell_id in cell_ids:
            cell_text = ""
            # Find the cell block and extract its text
            if cell_id in block_map:
                cell_block = block_map[cell_id]
                # Cell content is in children
                children = cell_block.get("children", [])
                if children and children[0] in block_map:
                    child_block = block_map[children[0]]
                    # Extract styled text from child block
                    for field in ["text", "heading1", "heading2", "heading3", "heading4", "heading5",
                                  "heading6", "heading7", "heading8", "heading9", "bullet"]:
                        if field in child_block and isinstance(child_block[field], dict):
                            field_data = child_block[field]
                            styled = self._extract_text_with_styles(field_data)
                            if styled:
                                cell_text = styled
                                break
            cell_contents.append(cell_text.strip() if cell_text.strip() else "")

        # Build markdown table
        md_lines = []

        # Build rows
        for row in range(row_size):
            row_cells = []
            for col in range(column_size):
                idx = row * column_size + col
                if idx < len(cell_contents):
                    cell_text = cell_contents[idx].replace("|", "\\|")  # Escape pipes
                    row_cells.append(cell_text)
                else:
                    row_cells.append("")
            md_lines.append("| " + " | ".join(row_cells) + " |")

            # Add separator after first row (header)
            if row == 0:
                separator = "| " + " | ".join(["---"] * column_size) + " |"
                md_lines.append(separator)

        return "\n".join(md_lines)

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
            if 3 <= block.block_type <= 11:  # Is heading (heading1-heading9)
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
