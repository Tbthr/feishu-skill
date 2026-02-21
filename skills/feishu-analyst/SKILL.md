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
python scripts/setup.py
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

#### 入口选择指南

| 场景 | 入口 | 说明 |
|------|------|------|
| 固定流程（PRD 分析） | `/feishu-prd-analyse` | 稳定、可预测 |
| 动态需求 | Python API | 灵活、可组合 |
| 命令行操作 | CLI | 直接调用 |

#### 1. CLI 命令

```bash
# 获取文档并保存到临时文件
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" save "https://xxx.feishu.cn/wiki/xxx"

# 输出示例：
# {
#   "document_id": "G85TdPCcTo91CYx4aYzcLKCnnFe",
#   "title": "文档标题",
#   "blocks_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe_blocks.json",
#   "markdown_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe.md"
# }

# 指定输出目录
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" save "https://xxx.feishu.cn/wiki/xxx" --output-dir ./output

# 获取文档大纲
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" outline /tmp/document_xxx_blocks.json

# 列出所有工具
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" list

# 获取工具描述
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" describe get_feishu_document_blocks

# 直接调用工具
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" call get_feishu_document_info \
  --args '{"documentId": "https://xxx.feishu.cn/wiki/xxx", "documentType": "wiki"}'
```

#### 2. Python API（动态场景推荐）

```python
import sys
sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts")

from client import FeishuMCPClient
from document import save_document, get_outline

# 保存文档
result = save_document("https://xxx.feishu.cn/wiki/xxx")
print(f"Markdown 文件: {result['markdown_file']}")

# 提取目录
outline = get_outline(result["blocks_file"])

# 底层调用
client = FeishuMCPClient()
info = client.call("get_feishu_document_info", {"documentId": "xxx"})
```

## ⚠️ Best Practices

> **CRITICAL: Use cli.py as Entry Point**
>
> CLI 操作应通过 `cli.py` 进行：
>
> ✅ **DO** - 使用 `cli.py save` 获取文档
> ✅ **DO** - 使用 `cli.py outline` 提取大纲
> ✅ **DO** - 使用 Python API 进行动态操作
> ❌ **DON'T** - 直接调用底层 Python 模块
>
> **Why?**
> - 内置脚本处理 **47 种块类型**（自定义解析器会遗漏很多）
> - 包含 **错误处理** 和边界情况处理
> - **持续维护** 和 bug 修复
> - 零上下文设计，节省 tokens

## 可用工具

查看完整列表：
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" list
```

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

用户入口脚本（位于 `scripts/`）：

| Script | Purpose | CLI Usage |
|--------|---------|-----------|
| `cli.py` | **CLI 入口**：获取文档、提取大纲、调用工具 | `save URL` / `outline FILE` / `call TOOL` |
| `setup.py` | 交互式凭证配置 | 直接运行 |

Python API（动态场景推荐）：

```python
from client import FeishuMCPClient
from document import save_document, get_outline
```

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

使用 `cli.py save` 和 `cli.py outline` 命令：

```bash
# 1. 获取文档并保存到临时文件
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" save "https://xxx.feishu.cn/wiki/xxx"

# 2. 获取文档大纲
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" outline /tmp/document_xxx_blocks.json
```

### For Data Querying (tables, schedules, lists)

```bash
# 1. 获取文档并保存到临时文件
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" save "https://xxx.feishu.cn/wiki/xxx"

# 2. 使用 Python API 分析数据
python -c "
import sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts')
from document import get_outline
print(get_outline('/tmp/document_xxx_blocks.json'))
"
```

## Error Handling

- **Credentials not configured**: Run `python scripts/setup.py` or set environment variables
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
/feishu-prd-analyse https://dy3m1s1v7v.feishu.cn/docx/xxx
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