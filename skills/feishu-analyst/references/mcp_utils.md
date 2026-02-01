# mcp_utils Reference Guide

Complete guide for using mcp_utils modules in Feishu document processing.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Validator Module](#validator-module)
3. [Document Processor](#document-processor)
4. [Search Processor](#search-processor)
5. [Table Processor](#table-processor)
6. [Creation Processor](#creation-processor)
7. [Logger Module](#logger-module)
8. [Block Types](#block-types)

---

## Quick Start

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from validator import MCPResponseValidator
from document_processor import DocumentProcessor

# Validate MCP response
v = MCPResponseValidator()
result = v.validate_response(mcp_response)
if result.has_error:
    return result.error_message

# Process document
processor = DocumentProcessor()
summary = processor.get_document_summary(mcp_response)
outline = processor.get_outline(mcp_response)
markdown = processor.to_markdown(mcp_response)
```

---

## Validator Module

Universal validation for all Feishu MCP responses.

### MCPResponseValidator

```python
from validator import MCPResponseValidator

validator = MCPResponseValidator()

# Validate response
result = validator.validate(mcp_response, tool_name="get_document_blocks")

if result.has_error:
    error_type = result.error_data.get("type")
    if error_type == "authorization_required":
        print("需要授权")
    else:
        print(f"错误: {result.error_message}")

# Save raw response for debugging
filepath = validator.log_response("get_document_blocks", mcp_response)
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    valid: bool              # Response is valid
    has_error: bool          # Contains error
    error_message: str       # Error description
    error_data: dict         # Parsed error info
```

---

## Document Processor

Core document handling, text extraction, and Markdown conversion.

### DocumentProcessor

```python
from document_processor import DocumentProcessor

processor = DocumentProcessor()
```

### Document Info Parsing

```python
# Parse document info response
info = processor.parse_document_info(doc_info_response)
print(f"Title: {info.title}")
print(f"Type: {info.doc_type}")  # "document" or "wiki"
print(f"Document ID: {info.document_id}")

# Wiki: extract correct ID for blocks
doc_id = processor.get_document_id_for_blocks(wiki_info_response)
# For wiki, returns obj_token value
```

### Content Extraction

```python
# Get document summary
summary = processor.get_document_summary(blocks)
# Returns: {
#   "total_blocks": 180,
#   "block_types": {"heading1": 5, "text": 120, ...},
#   "total_text_length": 15216,
#   "has_tables": True,
#   "has_code": True
# }

# Get outline (hierarchical)
outline = processor.get_outline(blocks)
# Returns: [
#   {"level": 1, "title": "Introduction", "index": 0},
#   {"level": 2, "title": "Background", "index": 5},
#   ...
# ]

# Extract all text
text = processor.extract_text(blocks)

# Convert to Markdown
markdown = processor.to_markdown(blocks)
```

### Block Operations

```python
# Search for content
matches = processor.search_blocks(blocks, "keyword")
# Returns: List of matching blocks with context

# Find blocks by type
headings = processor.find_blocks_by_type(blocks, block_type=2)  # heading1
code_blocks = processor.find_blocks_by_type(blocks, block_type=13)  # code

# Iterate through blocks (memory efficient)
for block in processor.iter_blocks(blocks):
    if block.text:
        print(block.text)
```

### Wiki vs Document IDs

**Document URL**: `https://xxx.feishu.cn/docx/DOC_ID`
- Use `DOC_ID` directly

**Wiki URL**: `https://xxx.feishu.cn/wiki/NODE_TOKEN`
```python
# Step 1: Get wiki info
wiki_info = await mcp__get_feishu_document_info(
    documentId=wiki_url,
    documentType="wiki"
)

# Step 2: Extract obj_token for blocks
doc_id = processor.get_document_id_for_blocks(wiki_info)

# Step 3: Use obj_token as documentId
blocks = await mcp__get_feishu_document_blocks(documentId=doc_id)
```

---

## Search Processor

Search result formatting and pagination.

```python
from search_processor import SearchProcessor

processor = SearchProcessor()

# Parse search results
results = processor.parse_response(search_response)

# Format for display
formatted = processor.format_results(results)

# Save results
filepath = processor.save_results(results, "查询关键词")

# Get pagination info
next_params = processor.get_next_page_params(results)
if next_params:
    # Use next_params to fetch next page
    pass
```

---

## Table Processor

Table data extraction and querying.

```python
from table_processor import TableProcessor

processor = TableProcessor()

# Parse table from response
table = processor.parse_table(table_response)

# Get cell value
cell = processor.get_cell(table, row=0, column=0)
text = processor.extract_cell_text(cell)

# Convert to Markdown
markdown = processor.to_markdown(table)

# Get as DataFrame dict
rows_dict = processor.to_dataframe_dict(table)

# Filter rows
def is_important(row):
    return row[0] == "重要"

filtered = processor.filter_rows(table, is_important)

# Get entire column
column = processor.get_column(table, column_index=0)
```

---

## Creation Processor

Parse creation operation responses.

```python
from creation_processor import CreationProcessor

processor = CreationProcessor()

# Parse document creation
result = processor.parse_document_creation(create_response)

# Parse folder creation
result = processor.parse_folder_creation(create_response)

# Parse blocks creation
result = processor.parse_blocks_creation(create_response)

# Parse table creation
result = processor.parse_table_creation(create_response)

# Format success message
msg = processor.format_success_message(result)

# Save creation record
filepath = processor.save_creation_result(result, "创建文档")
```

---

## Logger Module

MCP call logging and statistics.

```python
from logger import MCPLogger, log_mcp_call

# Quick logging
summary = log_mcp_call("get_document_blocks", {"doc_id": "xxx"}, response)
print(summary)  # ✅ get_document_blocks (50.2 KB)

# Full logging
logger = MCPLogger()

record = logger.log_call(
    tool_name="get_document_blocks",
    params={"documentId": "xxx"},
    response=response,
    error=None
)

# Get statistics
stats = logger.get_stats()
print(f"Total: {stats['total_calls']}")
print(f"Success: {stats['successful_calls']}")

# Recent calls
recent = logger.get_recent_calls(limit=10)
```

---

## Block Types

Feishu block type mapping:

| block_type | Name | Description |
|-----------|------|-------------|
| 1 | text | Plain text |
| 2 | heading1 | Level 1 heading |
| 3 | heading2 | Level 2 heading |
| 4-10 | heading3-9 | Level 3-9 headings |
| 11 | bullet | Unordered list |
| 12 | ordered | Ordered list |
| 13 | code | Code block |
| 14 | quote | Quote block |
| 18 | table | Table |
| 43 | whiteboard | Whiteboard (needs special handling) |

---

## Token Efficiency

| Response Size | Direct Load | Utils | Savings |
|--------------|-------------|-------|---------|
| 50KB | ~15K tokens | ~1K | 93% |
| 177KB | ~54K tokens | ~2K | 96% |
| 684KB | ~210K tokens | ~2.5K | 98.8% |

**Key principle**: Save large responses to file, then process with mcp_utils.

---

## Wrapped JSON Format

Feishu MCP may return wrapped format:
```json
[{
  "type": "text",
  "text": "[{\"block_id\": \"...\", ...}]"
}]
```

`DocumentProcessor.normalize_blocks()` handles this automatically.

---

## Best Practices

1. **Always validate first**
   ```python
   result = validator.validate_response(response)
   if result.has_error:
       return result.error_message
   ```

2. **Save large documents to file**
   ```python
   with open("doc.json", "w") as f:
       json.dump(blocks, f)
   ```

3. **Use iterators for large docs**
   ```python
   for block in processor.iter_blocks(blocks):
       process(block)
   ```

4. **Selective processing**
   ```python
   headings = processor.find_blocks_by_type(blocks, block_type=2)
   matches = processor.search_blocks(blocks, "keyword")
   ```
