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

## ⚠️ Best Practices

> **CRITICAL: Use Built-in Scripts**
>
> This skill includes pre-built, tested Python scripts in `scripts/`:
>
> ✅ **DO** - Import and use `DocumentProcessor`, `MCPResponseValidator`, etc.
> ❌ **DON'T** - Write your own JSON parser for Feishu blocks
>
> **Why?**
> - Built-in scripts handle **47 block types** (your parser will miss many)
> - Includes **error handling** for edge cases (malformed responses, nested structures)
> - **Actively maintained** with bug fixes
> - Saves tokens and time
>
> See "Process with Skill Scripts" below for usage.

## Quick Start

### For PRD Analysis (Recommended)

**Use the dedicated slash command**: `/feishu-prd-analyse <URL>`

Example:
```
/feishu-prd-analyse https://dy3m1s1v7v.feishu.cn/docx/CgMCdRMh8oMtDKxVcURcrb0DnVr
```

This command will automatically:
1. **Read the ENTIRE document** (all text, tables, whiteboards, images, diagrams, flowcharts, etc.)
2. Use the feishu-analyst skill to fetch the document
3. Load the PRD checklist from `references/prd_checklist.md`
4. Extract document content and convert to Markdown
5. Apply systematic analysis framework
6. Generate structured review with findings and recommendations

### Manual Analysis

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

> ⚠️ **IMPORTANT**: Always use the built-in scripts from the skill directory instead of writing your own parser. The built-in scripts are:
> - **Pre-tested** with Feishu MCP responses
> - **Feature-complete** (47 block types, error handling, edge cases)
> - **Maintained** with bug fixes and updates
>
> Writing your own parser will result in limited functionality and maintenance burden.

**Get the skill base directory** (available at the start of the skill):
```python
# The skill base directory is shown when the skill is loaded
# It follows this pattern:
# Base directory for this skill: /Users/xxx/.claude/plugins/cache/.../skills/feishu-analyst
SKILL_BASE = "/path/to/skill"  # Copy from skill output
```

**Import and use built-in scripts:**
```python
import sys
sys.path.insert(0, f"{SKILL_BASE}/scripts")

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

### For PRD Analysis (Product Requirements)

**Use the `/feishu-prd-analyse` command:**
```
/feishu-prd-analyse <URL>
```

When invoked, the command will:
1. Extract document ID from URL (docx or wiki)
2. **Fetch and read the ENTIRE document** - all text blocks, tables, whiteboards, images, diagrams, flowcharts, code blocks, and embedded content
3. Fetch document blocks via Feishu MCP
4. Automatically load `prd_checklist.md` framework
5. Apply systematic analysis across 4 dimensions:
   - **Ambiguity Check**: Vague terms, metrics, timelines
   - **Logic Consistency**: Contradictions, edge cases, preconditions
   - **Data Integrity**: Type definitions, constraints, required fields
   - **Completeness**: User stories, acceptance criteria, success metrics
5. Generate structured review using output template

### For General Text Analysis (wikis, notes)

> ⚠️ **Use the built-in `DocumentProcessor`** - don't write custom parsers!

1. Save blocks to file
2. Use `document_processor.to_markdown()` for conversion
3. Process Markdown for analysis

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

## Slash Command for PRD Analysis

A dedicated slash command `/feishu-prd-analyse` is available for PRD analysis:

```
/feishu-prd-analyse <feishu_document_url>
```

### Examples

**Analyze a PRD Document:**
```
/feishu-prd-analyse https://dy3m1s1v7v.feishu.cn/docx/CgMCdRMh8oMtDKxVcURcrb0DnVr
```

**Analyze a Wiki PRD:**
```
/feishu-prd-analyse https://xxx.feishu.cn/wiki/xxxxx
```

**What happens when invoked:**
1. Command extracts document ID from URL
2. **Reads the COMPLETE document** - all text, tables, whiteboards, images, flowcharts, and diagrams
3. Uses feishu-analyst skill to fetch document content via Feishu MCP
4. Automatically loads `prd_checklist.md` from `references/`
5. Applies systematic analysis framework
6. Returns structured review with:
   - Executive summary
   - Critical findings (ambiguities, contradictions, data issues, gaps)
   - Questions for product team
   - Recommendations
   - Overall assessment (Ready/Needs Revision/Major Gaps)

### Tips

- Use `/feishu-prd-analyse` for PRD analysis - it automatically applies the checklist
- For other document types, use the skill directly with your specific requirements
- Works with both `/docx/` and `/wiki/` URLs

## Reference Documentation

- [prd_checklist.md](references/prd_checklist.md) - PRD analysis checklist
- [mcp_utils.md](references/mcp_utils.md) - Complete mcp_utils API guide
