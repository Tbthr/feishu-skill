"""
Table Processor for Feishu MCP

Handles table data with cell-based operations.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class TableCell:
    """Table cell data"""
    row: int
    column: int
    block_type: str
    content: Any


@dataclass
class TableData:
    """Complete table data structure"""
    table_id: str
    row_size: int
    column_size: int
    cells: List[TableCell]
    metadata: Dict


class TableProcessor:
    """
    Process table data from Feishu MCP.

    Table responses have a 2D coordinate system:
    - cells: Array of {coordinate: {row, column}, content: {...}}
    - rowSize: Number of rows
    - columnSize: Number of columns
    """

    def __init__(self, cache_dir: str = "/tmp/feishu_mcp_cache"):
        """
        Initialize table processor.

        Args:
            cache_dir: Directory to cache table data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_table(self, response: Dict) -> TableData:
        """
        Parse table response from create_feishu_table or document blocks.

        Args:
            response: Raw response containing table data

        Returns:
            TableData with parsed cells
        """
        table_id = response.get("table_id", "")

        # Get table size
        row_size = response.get("rowSize", response.get("row_size", 0))
        column_size = response.get("columnSize", response.get("column_size", 0))

        # Parse cells
        cells = []
        raw_cells = response.get("cells", [])

        for cell_data in raw_cells:
            coord = cell_data.get("coordinate", {})
            content = cell_data.get("content", {})

            cells.append(TableCell(
                row=coord.get("row", 0),
                column=coord.get("column", 0),
                block_type=content.get("blockType", "text"),
                content=content
            ))

        return TableData(
            table_id=table_id,
            row_size=row_size,
            column_size=column_size,
            cells=cells,
            metadata=response.get("metadata", {})
        )

    def get_cell(self, table: TableData, row: int, column: int) -> Optional[TableCell]:
        """
        Get a specific cell by coordinates.

        Args:
            table: Parsed table data
            row: Row index (0-based)
            column: Column index (0-based)

        Returns:
            TableCell if found, None otherwise
        """
        for cell in table.cells:
            if cell.row == row and cell.column == column:
                return cell
        return None

    def extract_cell_text(self, cell: TableCell) -> str:
        """
        Extract text content from a cell.

        Args:
            cell: TableCell to extract from

        Returns:
            Text content
        """
        content = cell.content
        if not isinstance(content, dict):
            return str(content)

        # Handle different block types
        if cell.block_type == "text":
            text_elements = content.get("options", {}).get("text", {}).get("textStyles", [])
            return "".join(
                elem.get("text", "")
                for elem in text_elements
            )
        elif cell.block_type == "code":
            return content.get("options", {}).get("code", {}).get("code", "")
        elif cell.block_type == "heading":
            return content.get("options", {}).get("heading", {}).get("content", "")

        return str(content)

    def to_dataframe_dict(self, table: TableData) -> Dict[int, List[str]]:
        """
        Convert table to a dict of rows.

        Args:
            table: Parsed table data

        Returns:
            Dict mapping row index to list of column values
        """
        result = {}

        # Initialize empty rows
        for row in range(table.row_size):
            result[row] = [""] * table.column_size

        # Fill in cells
        for cell in table.cells:
            if cell.row < table.row_size and cell.column < table.column_size:
                result[cell.row][cell.column] = self.extract_cell_text(cell)

        return result

    def to_markdown(self, table: TableData) -> str:
        """
        Convert table to Markdown format.

        Args:
            table: Parsed table data

        Returns:
            Markdown table string
        """
        rows_dict = self.to_dataframe_dict(table)

        # Build rows
        rows = []
        for row_idx in range(table.row_size):
            rows.append(rows_dict.get(row_idx, [""] * table.column_size))

        if not rows:
            return "| Empty Table |\n|-----------|"

        # Build markdown
        lines = []

        # Header row
        header = "| " + " | ".join(str(cell) for cell in rows[0]) + " |"
        lines.append(header)

        # Separator
        separator = "| " + " | ".join("---" for _ in rows[0]) + " |"
        lines.append(separator)

        # Data rows
        for row in rows[1:]:
            line = "| " + " | ".join(str(cell) for cell in row) + " |"
            lines.append(line)

        return "\n".join(lines)

    def filter_rows(self, table: TableData,
                   condition: Callable[[List[str]], bool]) -> List[List[str]]:
        """
        Filter table rows by condition.

        Args:
            table: Parsed table data
            condition: Function that takes a row (list of cell values)
                      and returns True if row should be included

        Returns:
            List of rows that match the condition
        """
        rows_dict = self.to_dataframe_dict(table)
        matching_rows = []

        for row_idx in range(table.row_size):
            row = rows_dict.get(row_idx, [])
            if condition(row):
                matching_rows.append(row)

        return matching_rows

    def get_column(self, table: TableData, column_index: int) -> List[str]:
        """
        Get all values in a specific column.

        Args:
            table: Parsed table data
            column_index: Column index (0-based)

        Returns:
            List of cell values in the column
        """
        column_data = []

        for cell in table.cells:
            if cell.column == column_index:
                column_data.append((cell.row, self.extract_cell_text(cell)))

        # Sort by row and return values
        column_data.sort(key=lambda x: x[0])
        return [value for _, value in column_data]

    def save_table(self, table: TableData, filename: str) -> Path:
        """
        Save table data to JSON file.

        Args:
            table: Parsed table data
            filename: Name for the file

        Returns:
            Path to saved file
        """
        filepath = self.cache_dir / filename

        data = {
            "table_id": table.table_id,
            "row_size": table.row_size,
            "column_size": table.column_size,
            "cells": [
                {
                    "row": cell.row,
                    "column": cell.column,
                    "block_type": cell.block_type,
                    "text": self.extract_cell_text(cell)
                }
                for cell in table.cells
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath


# Convenience functions
def table_to_markdown(table_response: Dict) -> str:
    """Quick conversion of table response to Markdown."""
    processor = TableProcessor()
    table = processor.parse_table(table_response)
    return processor.to_markdown(table)


def get_cell_value(table_response: Dict, row: int, column: int) -> Optional[str]:
    """Quick extraction of specific cell value."""
    processor = TableProcessor()
    table = processor.parse_table(table_response)
    cell = processor.get_cell(table, row, column)
    if cell:
        return processor.extract_cell_text(cell)
    return None
