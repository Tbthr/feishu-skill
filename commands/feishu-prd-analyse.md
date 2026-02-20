---
description: "Analyze Feishu PRD documents using the feishu-analyst skill with auto-loaded PRD checklist framework"
---

You are analyzing a Product Requirements Document (PRD) from Feishu. Follow these steps:

## 执行步骤

### 1. 提取文档 ID

**Document** (`/docx/DOC_ID`): Use `DOC_ID` directly
**Wiki** (`/wiki/NODE_TOKEN`): Use `get_feishu_document_info(documentType="wiki")` and extract `obj_token`

### 2. 获取文档信息（零上下文）

```bash
cd $SKILL_DIR/scripts
python executor.py --call '{"tool": "get_feishu_document_info", "arguments": {"documentId": "<URL>", "documentType": "wiki"}}'
```

或使用 Python：
```python
import sys
sys.path.insert(0, f"{SKILL_BASE}/scripts")
from mcp_client import call_feishu_tool

doc_info = call_feishu_tool("get_feishu_document_info", {
    "documentId": "<URL>",
    "documentType": "wiki"
})
doc_id = doc_info.get("obj_token") or doc_info.get("documentId")
```

### 3. 获取文档块（零上下文）

```bash
python executor.py --call '{"tool": "get_feishu_document_blocks", "arguments": {"documentId": "<obj_token>"}}' > /tmp/blocks.json
```

### 4. 处理文档

```python
import json
import sys
sys.path.insert(0, f"{SKILL_BASE}/scripts")
from document_processor import DocumentProcessor

with open('/tmp/blocks.json') as f:
    blocks = json.load(f)

processor = DocumentProcessor()
markdown = processor.to_markdown(blocks)
```

### 5. 应用 PRD 分析框架

Load the PRD checklist from `skills/feishu-analyst/references/prd_checklist.md`

Apply the systematic analysis framework across 4 dimensions:
   - **Ambiguity Check**: Vague terms, metrics, timelines
   - **Logic Consistency**: Contradictions, edge cases, preconditions
   - **Data Integrity**: Type definitions, constraints, required fields
   - **Completeness**: User stories, acceptance criteria, success metrics

## ⚠️ CRITICAL Requirements

- **MUST read and analyze ALL content types**, including:
  - All text blocks (headings, paragraphs, lists)
  - All tables (every row and column)
  - All whiteboards/diagrams (flowcharts, mind maps, architecture diagrams)
  - All images and screenshots
  - All code blocks
  - All embedded content
- Ensure no blocks are skipped or truncated
- Verify the document has been fully read before proceeding with analysis
- **ALWAYS save large responses (>10KB) to file before processing**

## 输出格式

Generate a structured review with:
- Executive summary
- Critical findings (ambiguities, contradictions, data issues, gaps)
- Questions for product team
- Recommendations
- Overall assessment (Ready/Needs Revision/Major Gaps)

The user will provide a Feishu document URL (either `/docx/` or `/wiki/` format).
