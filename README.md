# Feishu Analyst Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://github.com/anthropics/anthropic-agent-skills)

> 飞书文档智能分析 skill - 通过 Feishu MCP 实现高效的文档交互

## 特性

- **极简配置** - 一键安装，自动配置 MCP 服务器
- **Token 节省** - 智能处理大文档，节省 **96-99%** 的 token 消耗
- **类型完整** - 支持文档、Wiki、表格、白板等所有飞书内容类型
- **Markdown 转换** - 自动转换为结构化 Markdown，便于分析
- **表格数据提取** - 专门处理表格数据，支持结构化查询
- **文档搜索** - 支持关键词搜索飞书文档库

## 安装方式

### 方式一：Plugin Marketplace（推荐）

```bash
# 1. 添加 marketplace
/plugin marketplace add your-username/feishu-skill

# 2. 安装 plugin
/plugin install feishu-skills
```

### 方式二：Git Clone

```bash
# 克隆到用户全局目录（所有项目可用）
git clone https://github.com/your-username/feishu-skill.git ~/.claude/skills/feishu-skills

# 或克隆到项目目录（仅当前项目可用）
git clone https://github.com/your-username/feishu-skill.git .claude/skills/feishu-skills
```

### 方式三：手动下载

1. 下载 [Releases](https://github.com/your-username/feishu-skill/releases) 中的 zip 文件
2. 解压到 `.claude/skills/feishu-skills/` 目录

## 快速开始

### 1. 安装配置

```bash
# 克隆项目到本地
git clone https://github.com/your-username/feishu-skill.git
cd feishu-skill

# 运行安装脚本
bash skills/feishu-analyst/scripts/setup.sh install
```

按提示输入你的飞书 **App ID** 和 **App Secret**。

### 2. 获取飞书凭据

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建自建应用（或使用现有应用）
3. 进入「凭证与基础信息」页面
4. 复制 **App ID** 和 **App Secret**
5. 添加权限：`docx:document`、`docx:document:readonly`

### 3. 重启并使用

配置完成后，**重启 Claude Code**，然后：

```
使用 feishu-analyst skill 分析文档：https://xxx.feishu.cn/wiki/...
```

## 使用示例

### 分析 Wiki 文档

```
请帮我分析这个飞书 Wiki 中的 PRD 文档：
https://xxx.feishu.cn/wiki/xxxxx

提取核心需求、功能列表和技术要点。
```

### 提取表格数据

```
从这个飞书文档中提取所有表格数据：
https://xxx.feishu.cn/docx/xxxxx

按产品分类汇总数据。
```

### 搜索文档

```
在飞书中搜索包含 "AI Agent" 的文档。
```

## Token 效率对比

| 文档大小 | 直接加载 | Skill 处理 | 节省比例 |
|---------|---------|-----------|---------|
| 50 KB   | ~15K tokens | ~1K tokens | **93%** |
| 177 KB  | ~54K tokens | ~2K tokens | **96%** |
| 684 KB  | ~210K tokens | ~2.5K tokens | **98.8%** |

## 实现原理

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        Claude Code                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐      ┌──────────────────────────────┐  │
│  │ feishu-analyst│─────▶│  Feishu MCP Server           │  │
│  │    Skill      │      │  (cso1z/Feishu-MCP)          │  │
│  │               │◀─────│   https://github.com/cso1z/  │  │
│  └───────────────┘      └──────────────────────────────┘  │
│         │                         │                        │
│         │                         ▼                        │
│  ┌──────▼─────────────────────────────────────┐            │
│  │  Processing Scripts (Python)                │            │
│  │  ├── document_processor.py  → Markdown 转换 │            │
│  │  ├── table_processor.py     → 表格提取     │            │
│  │  ├── search_processor.py    → 搜索格式化   │            │
│  │  ├── creation_processor.py  → 创建响应     │            │
│  │  └── validator.py           → 响应验证     │            │
│  └─────────────────────────────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Feishu API     │
                    │  open.feishu.cn │
                    └─────────────────┘
```

### 工作流程

1. **文档获取** - 通过 Feishu MCP 获取原始文档块
2. **文件暂存** - 大文档保存到本地文件（避免 token 消耗）
3. **智能处理** - 根据内容类型选择合适的处理器
4. **结果返回** - 返回结构化结果（Markdown、表格数据等）

### 核心脚本说明

| 脚本 | 功能 |
|------|------|
| `validator.py` | 验证 MCP 响应，提取错误信息 |
| `document_processor.py` | 文档处理、Markdown 转换、大纲生成 |
| `search_processor.py` | 搜索结果格式化 |
| `table_processor.py` | 表格数据提取和结构化 |
| `creation_processor.py` | 文档创建响应解析 |
| `logger.py` | MCP 调用日志记录 |

## 项目结构

```
feishu-skill/
├── LICENSE                            # MIT 许可证
├── README.md                          # 项目说明（本文件）
├── .gitignore                         # Git 忽略配置
├── requirements.txt                   # Python 依赖
├── CHANGELOG.md                       # 更新日志
├── CONTRIBUTING.md                    # 贡献指南
├── .claude-plugin/
│   └── marketplace.json               # Marketplace 配置
└── skills/                            # Skills 目录
    └── feishu-analyst/
        ├── SKILL.md                   # Skill 定义文件
        ├── scripts/                   # 处理脚本
        │   ├── setup.sh               # MCP 配置脚本
        │   ├── validator.py           # 响应验证
        │   ├── document_processor.py  # 文档处理
        │   ├── search_processor.py    # 搜索处理
        │   ├── table_processor.py     # 表格处理
        │   ├── creation_processor.py  # 创建处理
        │   └── logger.py              # 日志记录
        └── references/                # 参考文档
            ├── prd_checklist.md       # PRD 分析清单
            └── mcp_utils.md           # 完整 API 指南
```

## 故障排查

### MCP 未加载

```bash
# 检查 MCP 配置状态
bash skills/feishu-analyst/scripts/setup.sh check
```

### 权限错误

确保飞书应用有以下权限：
- `docx:document` - 读取文档内容
- `docx:document:readonly` - 只读访问
- `wiki:wiki:readonly` - Wiki 只读访问（如需）

### 认证失败

```bash
# 重新配置凭据
bash skills/feishu-analyst/scripts/setup.sh install
```

## 相关资源

- [Feishu MCP Server](https://github.com/cso1z/Feishu-MCP)
- [Claude Agent Skills](https://github.com/anthropics/anthropic-agent-skills)
- [飞书开放平台](https://open.feishu.cn/)

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。
