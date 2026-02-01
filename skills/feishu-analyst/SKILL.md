---
name: feishu-analyst
description: Intelligent interaction with Feishu/Lark documents via Feishu MCP. Use when analyzing, extracting content from, or querying Feishu documents (.docx, /wiki/ URLs) including text extraction, markdown conversion, table data analysis, and document search. Requires Feishu MCP server configured.
---

# Feishu Document Analyst

Analyze Feishu documents efficiently with token-optimized processing.

## Prerequisites

**Feishu MCP Server is REQUIRED.** Check for `mcp__Feishu-MCP__*` tools in available tools.

If not configured, guide user to run:
```bash
bash scripts/setup.sh install
```

## Quick Start

### 1. Extract Document ID

**Document** (`/docx/DOC_ID`): Use `DOC_ID` directly
**Wiki** (`/wiki/NODE_TOKEN`): Use `get_feishu_document_info(documentType="wiki")` and extract `obj_token`

### 2. Fetch and Process

```python
# For wiki URLs
doc_info = await mcp__Feishu-MCP__get_feishu_document_info(
    documentId=url, documentType="wiki"
)
doc_id = doc_info.get("obj_token") or doc_info.get("documentId")

# Get blocks (may be very large!)
blocks = await mcp__Feishu-MCP__get_feishu_document_blocks(documentId=doc_id)

# CRITICAL: Save large responses to file (not to context)
import json
with open("doc_blocks.json", "w") as f:
    json.dump(blocks, f)
```

### 3. Process with Skill Scripts

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from validator import MCPResponseValidator
from document_processor import DocumentProcessor

v = MCPResponseValidator()
result = v.validate_response(blocks)
processor = DocumentProcessor()
summary = processor.get_document_summary(blocks)
markdown = processor.to_markdown(blocks)
```

## Token Efficiency

| Size | Direct Load | File Processing | Savings |
|------|-------------|-----------------|---------|
| 50KB | ~15K tokens | ~1K tokens | 93% |
| 177KB | ~54K tokens | ~2K tokens | 96% |
| 684KB | ~210K tokens | ~2.5K tokens | 98.8% |

**ALWAYS save large responses (>10KB) to file before processing.**

## Available Scripts

Located in `scripts/`:

| Script | Purpose |
|--------|---------|
| `validator.py` | Response validation, error extraction |
| `document_processor.py` | Document handling, Markdown conversion, outline generation |
| `search_processor.py` | Search result formatting |
| `table_processor.py` | Table data extraction |
| `creation_processor.py` | Creation response parsing |
| `logger.py` | MCP call logging |

## Analysis Approaches

### For Text Analysis (PRDs, wikis, notes)
1. Save blocks to file
2. Use `document_processor.to_markdown()` for conversion
3. Process Markdown for analysis
4. For PRDs, see [prd_checklist.md](references/prd_checklist.md)

### For Data Querying (tables, schedules, lists)
1. Save blocks to file
2. Use `table_processor` for table data
3. Write Python to query and filter
4. Return results from code output

## Error Handling

- **MCP not available**: User needs to run `bash scripts/setup.sh install`
- **Permission Denied**: Check document access or bot visibility
- **API Errors**: Run `bash scripts/setup.sh check`
- **Authorization Required**: User must authorize via browser (user mode)

## Reference Documentation

- [prd_checklist.md](references/prd_checklist.md) - PRD analysis checklist
- [mcp_utils.md](references/mcp_utils.md) - Complete mcp_utils API guide
