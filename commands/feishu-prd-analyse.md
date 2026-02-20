---
description: "Analyze Feishu PRD documents using the feishu-analyst skill with auto-loaded PRD checklist framework"
---

You are analyzing a Product Requirements Document (PRD) from Feishu. Follow these steps:

## 执行步骤

### 1. 获取文档（推荐：使用 --fetch 保存到临时文件）

> ⚠️ **重要**：使用 `--fetch` 将文档保存到临时文件，**避免文档内容注入 context**。

```bash
cd $SKILL_DIR/scripts

# 获取文档并保存到 /tmp
python mcp_client.py --fetch "<FEISHU_URL>"

# 输出示例：
# {
#   "document_id": "G85TdPCcTo91CYx4aYzcLKCnnFe",
#   "title": "文档标题",
#   "blocks_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe_blocks.json",
#   "markdown_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe.md"
# }
```

### 2. 处理文档

```bash
# 转换为 Markdown
python mcp_client.py --process /tmp/document_xxx_blocks.json --format markdown

# 获取文档大纲
python mcp_client.py --process /tmp/document_xxx_blocks.json --format outline

# 获取文档摘要
python mcp_client.py --process /tmp/document_xxx_blocks.json --format summary
```

### 3. 应用 PRD 分析框架

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
- **ALWAYS use --fetch to save document to file, avoid loading content into context**

## 输出格式

Generate a structured review with:
- Executive summary
- Critical findings (ambiguities, contradictions, data issues, gaps)
- Questions for product team
- Recommendations
- Overall assessment (Ready/Needs Revision/Major Gaps)

The user will provide a Feishu document URL (either `/docx/` or `/wiki/` format).
