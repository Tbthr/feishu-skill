# Feishu Analyst Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://github.com/anthropics/anthropic-agent-skills)

> 飞书文档智能分析 skill - 零上下文 MCP 调用，高效分析飞书文档

## 特性

- **零上下文调用** - MCP 工具调用不注入 context，节省大量 tokens
- **极简配置** - 一键配置飞书凭证
- **PRD 智能分析** - 专用 `/feishu-prd-analyse` 命令，系统化评审产品需求文档
- **类型完整** - 支持文档、Wiki、表格、白板等所有飞书内容类型
- **Markdown 转换** - 自动转换为结构化 Markdown，便于分析
- **临时文件处理** - 大文档自动保存到临时文件，避免 context 溢出

## 安装方式

```bash
# 1. 添加 marketplace
/plugin marketplace add Tbthr/feishu-skill

# 2. 安装 plugin
/plugin install feishu-skills
```

## 快速开始

### 1. 配置飞书凭证

```bash
# 运行配置脚本
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/setup.py"
```

按提示输入你的飞书 **App ID** 和 **App Secret**。

### 2. 获取飞书凭据

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建自建应用（或使用现有应用）
3. 进入「凭证与基础信息」页面
4. 复制 **App ID** 和 **App Secret**
5. 添加以下权限：

```
docx:document:block:convert
base:app:read
bitable:app
bitable:app:readonly
board:whiteboard:node:create
board:whiteboard:node:read
contact:user.employee_id:readonly
docs:document.content:read
docx:document
docx:document:create
docx:document:readonly
drive:drive
drive:drive:readonly
drive:file
drive:file:upload
sheets:spreadsheet
sheets:spreadsheet:readonly
space:document:retrieve
space:folder:create
wiki:space:read
wiki:space:retrieve
wiki:wiki
wiki:wiki:readonly
```

### 3. 使用

```
/feishu-prd-analyse https://xxx.feishu.cn/wiki/xxxxx
```

## 使用示例

### PRD 智能分析（推荐）

使用专用的 slash command 进行产品需求文档分析：

```
/feishu-prd-analyse https://xxx.feishu.cn/docx/xxxxx
```

### 手动分析文档

```bash
# 获取文档并保存到临时文件（推荐）
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" save "https://xxx.feishu.cn/wiki/xxxxx"

# 输出：
# {
#   "document_id": "G85TdPCcTo91CYx4aYzcLKCnnFe",
#   "title": "文档标题",
#   "blocks_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe_blocks.json",
#   "markdown_file": "/tmp/document_G85TdPCcTo91CYx4aYzcLKCnnFe.md"
# }

# 获取文档大纲
python "${CLAUDE_PLUGIN_ROOT}/skills/feishu-analyst/scripts/cli.py" outline /tmp/document_xxx_blocks.json
```

## 实现原理

### 零上下文架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Claude Code                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐      ┌──────────────────────────────┐  │
│  │ feishu-analyst│─────▶│  cli.py                      │  │
│  │    Skill      │      │  save / outline / call       │  │
│  │               │      │                              │  │
│  │               │      │  ┌────────────────────────┐  │  │
│  │               │      │  │ executor.py            │  │  │
│  │               │      │  │ (启动 MCP Server)      │  │  │
│  │               │      │  └────────────────────────┘  │  │
│  └───────────────┘      └──────────────────────────────┘  │
│         │                         │                        │
│         │ 临时文件（不注入 context）                       │
│         ▼                         ▼                        │
│  ┌─────────────────────────────────────────────┐          │
│  │  /tmp/document_{id}_blocks.json             │          │
│  │  /tmp/document_{id}.md                      │          │
│  └─────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Feishu MCP     │
                    │  (npx feishu-mcp│
                    │   --stdio)      │
                    └─────────────────┘
```

### 核心脚本说明

**用户入口**：

| 脚本 | 功能 | CLI |
|------|------|-----|
| `cli.py` | **CLI 入口**：获取文档、提取大纲、调用工具 | `save` / `outline` / `call` |
| `setup.py` | 交互式凭证配置 | 直接运行 |

**Python API**：

```python
from client import FeishuMCPClient
from document import save_document, get_outline
```

**底层模块**（内部实现）：

| 模块 | 功能 |
|------|------|
| `executor.py` | 零上下文 MCP 执行器，启动 Feishu MCP Server |
| `processor.py` | 文档处理：Markdown 转换、大纲提取、摘要生成 |
| `table.py` | 表格数据提取和格式化 |
| `validator.py` | MCP 响应验证、错误提取 |
| `logger.py` | MCP 调用日志记录 |

### Slash Commands

| 命令 | 功能 |
|------|------|
| `/feishu-prd-analyse` | PRD 智能分析，自动应用系统化评审框架 |

## 项目结构

```
feishu-skill/
├── LICENSE
├── README.md
├── requirements.txt
├── CHANGELOG.md
├── CONTRIBUTING.md
├── commands/
│   └── feishu-prd-analyse.md      # PRD 分析命令
└── skills/
    └── feishu-analyst/
        ├── SKILL.md               # Skill 定义文件
        ├── scripts/
        │   ├── __init__.py        # 导出公共 API
        │   ├── cli.py             # CLI 入口 ⭐
        │   ├── client.py          # FeishuMCPClient ⭐
        │   ├── document.py        # save_document/get_outline ⭐
        │   ├── setup.py           # 凭证配置脚本 ⭐
        │   ├── executor.py        # 零上下文 MCP 执行器
        │   ├── processor.py       # 文档处理
        │   ├── table.py           # 表格处理
        │   ├── search.py          # 搜索处理
        │   ├── creation.py        # 创建处理
        │   ├── validator.py       # 响应验证
        │   └── logger.py          # 日志记录
        └── references/
            └── prd_checklist.md   # PRD 分析清单
```

## 故障排查

### 凭证未配置

```bash
python skills/feishu-analyst/scripts/setup.py
```

### 权限错误

确保飞书应用有完整的 MCP 依赖权限（见上方权限列表）。

## 相关资源

- [Feishu MCP Server](https://github.com/cso1z/Feishu-MCP)
- [Claude Agent Skills](https://github.com/anthropics/anthropic-agent-skills)
- [MCP to Skill Converter](https://github.com/GBSOSS/-mcp-to-skill-converter)
- [飞书开放平台](https://open.feishu.cn/)

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。
