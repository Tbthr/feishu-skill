---
name: feishu-analyst
description: Intelligent interaction with Feishu/Lark documents via Feishu MCP. Use when analyzing, extracting content from, or querying Feishu documents (.docx, /wiki/ URLs) including text extraction, markdown conversion, table data analysis, and document search. Uses zero-context MCP calling via executor.py.
---

# Feishu Document Analyst

Analyze Feishu documents efficiently with **zero-context MCP calling**.

## Zero-Context MCP 调用

本 Skill 使用 **零上下文模式** 调用飞书 MCP 工具：
- 工具定义不加载到 context（节省 ~15,000 tokens）
- 工具响应不注入 context（执行时 0 tokens）
- 通过 `executor.py` 外部执行

## Prerequisites

**依赖已内置**，只需确保：
- Python 3.8+
- `mcp` package 已安装：`pip install mcp`

## 首次使用配置

**方式一：运行配置脚本（推荐）**
```bash
python scripts/setup-feishu.py
```

**方式二：设置环境变量**
```bash
export FEISHU_APP_ID='your-app-id'
export FEISHU_APP_SECRET='your-app-secret'
export FEISHU_AUTH_TYPE='tenant'  # 或 'user'
```

**获取凭证**：https://open.feishu.cn/ → 创建应用 → 凭证与基础信息

## Quick Start

### For PRD Analysis (Recommended)

**Use the dedicated slash command**: `/feishu-prd-analyse <URL>`

Example:
```
/feishu-prd-analyse https://dy3m1s1v7v.feishu.cn/docx/CgMCdRMh8oMtDKxVcURcrb0DnVr
```

This command will automatically:
1. **Read the ENTIRE document** (all text, tables, whiteboards, images, diagrams, flowcharts, etc.)
2. Use zero-context MCP calling via `executor.py`
3. Load the PRD checklist from `references/prd_checklist.md`
4. Extract document content and convert to Markdown
5. Apply systematic analysis framework
6. Generate structured review with findings and recommendations

### Manual Analysis

#### 1. 获取 Skill 基础路径

Skill 加载时会显示基础路径：
```
Base directory for this skill: /Users/xxx/.claude/plugins/cache/.../skills/feishu-analyst
```

#### 2. 推荐方式：使用 --fetch 保存到临时文件

> ⚠️ **重要**：使用 `--fetch` 将文档保存到临时文件，**避免文档内容注入 context**。
> 临时文件命名格式：`document_{document_id}_blocks.json` 和 `document_{document_id}.md`

```bash
cd $SKILL_DIR/scripts

# 获取文档并保存到 /tmp（默认）
python mcp_client.py --fetch "https://xxx.feishu.cn/wiki/xxx"

# 输出示例：
# {
#   "document_id": "G85TdPCcTo91CYx4aYzcLKCnnFe",
#   "title": "文档标题",
#   "blocks_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe_blocks.json",
#   "markdown_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe.md"
# }

# 指定输出目录
python mcp_client.py --fetch "https://xxx.feishu.cn/wiki/xxx" --output-dir ./output
```

#### 3. 处理已保存的文档文件

```bash
# 转换为 Markdown（输出到 stdout）
python mcp_client.py --process /tmp/document_xxx_blocks.json --format markdown

# 获取文档大纲
python mcp_client.py --process /tmp/document_xxx_blocks.json --format outline

# 获取文档摘要
python mcp_client.py --process /tmp/document_xxx_blocks.json --format summary

# 保存到文件
python mcp_client.py --process /tmp/document_xxx_blocks.json --format markdown --output result.md
```

**支持的格式**：
- `--format markdown` - 转换为 Markdown（默认）
- `--format outline` - 提取文档大纲
- `--format summary` - 输出文档摘要（JSON）

#### 4. 底层工具调用（可选）

```bash
# 列出所有工具
python mcp_client.py --list

# 获取工具描述
python mcp_client.py --describe get_feishu_document_blocks

# 直接调用工具（注意：响应可能很大）
python mcp_client.py --call get_feishu_document_info \
  --args '{"documentId": "https://xxx.feishu.cn/wiki/xxx", "documentType": "wiki"}'
```

#### 5. Python API

```python
import sys
sys.path.insert(0, f"{SKILL_BASE}/scripts")

from mcp_client import fetch_document, process_document

# 获取文档并保存到临时文件（推荐）
result = fetch_document("https://xxx.feishu.cn/wiki/xxx")
print(f"Markdown 文件: {result['markdown_file']}")

# 处理已保存的文件
markdown = process_document(result['blocks_file'], format="markdown")
print(markdown[:500])  # 只打印前500字符
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

## 可用工具

查看完整列表：`python executor.py --list`

常用工具：
- `get_feishu_document_info` - 获取文档信息（支持 wiki/docx）
- `get_feishu_document_blocks` - 获取文档块结构
- `search_feishu_documents` - 搜索文档
- `batch_create_feishu_blocks` - 批量创建块
- `get_feishu_whiteboard_content` - 获取白板内容
- `update_feishu_block_text` - 更新块文本
- `delete_feishu_document_blocks` - 删除块
- `get_feishu_image_resource` - 获取图片资源
- `upload_and_bind_image_to_block` - 上传图片
- `create_feishu_table` - 创建表格
- `fill_whiteboard_with_plantuml` - 用 PlantUML 填充白板
- `get_feishu_root_folder_info` - 获取根文件夹信息
- `get_feishu_folder_files` - 获取文件夹文件列表
- `create_feishu_folder` - 创建文件夹

## Available Scripts

Located in `scripts/`:

| Script | Purpose | CLI Usage |
|--------|---------|-----------|
| `mcp_client.py` | **统一入口**：获取文档、处理文档、调用工具 | `python mcp_client.py --fetch URL` / `--process FILE` / `--call TOOL` |
| `executor.py` | 底层 MCP 执行器 | `python executor.py --list` / `--call` |
| `setup-feishu.py` | 交互式凭证配置 | `python setup-feishu.py` |
| `document_processor.py` | 文档处理（Markdown/大纲/摘要） | Python import only |
| `validator.py` | 响应验证、错误提取 | Python import only |
| `table_processor.py` | 表格数据提取 | Python import only |
| `search_processor.py` | 搜索结果格式化 | Python import only |
| `creation_processor.py` | 创建响应解析 | Python import only |
| `logger.py` | MCP 调用日志 | Python import only |

## Token Efficiency

| Size | Direct MCP Load | Zero-Context + File | Savings |
|------|-----------------|---------------------|---------|
| 50KB | ~15K tokens | ~1K tokens | 93% |
| 177KB | ~54K tokens | ~2K tokens | 96% |
| 684KB | ~210K tokens | ~2.5K tokens | 98.8% |

**ALWAYS save large responses (>10KB) to file before processing.**

## Analysis Approaches

### For PRD Analysis (Product Requirements)

**Use the `/feishu-prd-analyse` command:**
```
/feishu-prd-analyse <URL>
```

When invoked, the command will:
1. Extract document ID from URL (docx or wiki)
2. **Fetch and read the ENTIRE document** - all text blocks, tables, whiteboards, images, diagrams, flowcharts, code blocks, and embedded content
3. Use zero-context MCP calling via `executor.py`
4. Automatically load `prd_checklist.md` framework
5. Apply systematic analysis across 4 dimensions:
   - **Ambiguity Check**: Vague terms, metrics, timelines
   - **Logic Consistency**: Contradictions, edge cases, preconditions
   - **Data Integrity**: Type definitions, constraints, required fields
   - **Completeness**: User stories, acceptance criteria, success metrics
6. Generate structured review using output template

### For General Text Analysis (wikis, notes)

> ⚠️ **Use the built-in `DocumentProcessor`** - don't write custom parsers!

```python
import sys
sys.path.insert(0, f"{SKILL_BASE}/scripts")

from mcp_client import call_feishu_tool
from document_processor import DocumentProcessor

# 获取文档块
blocks = call_feishu_tool("get_feishu_document_blocks", {"documentId": doc_id})

# 转换为 Markdown
processor = DocumentProcessor()
markdown = processor.to_markdown(blocks)
```

### For Data Querying (tables, schedules, lists)
```python
import sys
sys.path.insert(0, f"{SKILL_BASE}/scripts")

from mcp_client import call_feishu_tool
from table_processor import TableProcessor

# 获取文档块
blocks = call_feishu_tool("get_feishu_document_blocks", {"documentId": doc_id})

# 提取表格数据
processor = TableProcessor()
tables = processor.extract_tables(blocks)
```

## Error Handling

- **Credentials not configured**: Run `python scripts/setup-feishu.py` or set environment variables
- **mcp package not installed**: `pip install mcp`
- **Permission Denied**: Check document access or bot visibility
- **API Errors**: Verify credentials in `~/.feishu-mcp/config.json`
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
3. Uses zero-context MCP calling via `executor.py`
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
