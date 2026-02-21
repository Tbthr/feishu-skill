# Scripts 模块重构设计

> 日期：2026-02-21
> 状态：设计中

## 背景

### 当前问题

1. `mcp_client.py` 职责过重：混合了 CLI + 类 + 便捷函数（402行）
2. 冗余代码：全局单例、`call_feishu_tool()` 包装函数、`call_and_save()` 方法
3. 代码质量问题：函数内部 import、硬编码 `/tmp`、重复的 subprocess 调用模式
4. 入口混乱：同时提供 CLI + Python API + 便捷函数，AI 不知道用哪个

### 目标

- **固定场景**（如 PRD 分析）：使用 slash command → CLI，稳定可预测
- **动态场景**：AI 使用 Python API，灵活可组合

## 设计

### 文件结构

```
scripts/
├── __init__.py           # 导出公共 API
├── client.py             # FeishuMCPClient（纯 MCP 调用）
├── document.py           # save_document(), get_outline()
├── cli.py                # CLI 入口
├── executor.py           # MCP 执行器（不变）
├── processor.py          # DocumentProcessor（原 document_processor.py）
├── table.py              # TableProcessor（原 table_processor.py）
├── validator.py          # 响应验证（不变）
├── logger.py             # 日志（不变）
└── setup.py              # 凭证配置（原 setup_feishu.py）
```

### Python API

#### client.py

```python
class FeishuMCPClient:
    """飞书 MCP 客户端 - 纯 MCP 调用"""

    def __init__(self, scripts_dir: str | None = None): ...

    def call(self, tool_name: str, arguments: dict) -> Any:
        """调用任意 MCP 工具"""

    def list_tools(self) -> list[dict]:
        """列出所有可用工具"""

    def describe_tool(self, tool_name: str) -> dict:
        """获取工具详细 schema"""
```

#### document.py

```python
def save_document(url_or_id: str, output_dir: str | None = None) -> dict:
    """
    保存飞书文档到本地文件

    Args:
        url_or_id: 文档 URL 或 ID（支持 /docx/ 和 /wiki/ 格式）
        output_dir: 输出目录（默认系统临时目录）

    Returns:
        {
            "document_id": "xxx",
            "title": "文档标题",
            "markdown_file": "/tmp/xxx.md",
            "blocks_file": "/tmp/xxx_blocks.json"
        }
    """

def get_outline(blocks_file: str) -> str:
    """
    提取文档目录结构

    Args:
        blocks_file: 文档块 JSON 文件路径

    Returns:
        Markdown 格式的目录
    """
```

### CLI

```bash
python cli.py save <url> [--output-dir DIR]
python cli.py outline <blocks_file>
python cli.py list
python cli.py describe <tool>
python cli.py call <tool> --args '{"...": "..."}' [--output FILE]
```

### 入口选择指南

| 场景 | 入口 | 说明 |
|------|------|------|
| 固定流程（PRD 分析） | slash command → CLI | 稳定、可预测 |
| 动态需求 | Python API | 灵活、可组合 |

### SKILL.md 引导结构

```markdown
## 快速选择入口

| 场景 | 入口 |
|------|------|
| 固定流程（PRD 分析） | `/feishu-prd-analyse` |
| 动态需求 | Python API |

## Python API（动态场景推荐）

### 使用示例

```python
from client import FeishuMCPClient
from document import save_document, get_outline

# 保存文档
result = save_document("https://xxx.feishu.cn/wiki/xxx")
# → {"markdown_file": "/tmp/xxx.md", "blocks_file": "..."}

# 提取目录
outline = get_outline(result["blocks_file"])

# 底层调用
client = FeishuMCPClient()
info = client.call("get_feishu_document_info", {"documentId": "xxx"})
```

## CLI（slash command 使用）

```bash
python cli.py save <url>
python cli.py outline <blocks_file>
```
```

## 删除的冗余内容

| 删除项 | 原因 |
|--------|------|
| `_client` 全局单例 | 无状态，不需要 |
| `get_client()` | 直接 `FeishuMCPClient()` 即可 |
| `call_feishu_tool()` | 冗余包装 |
| `call_and_save()` | 用 `call()` + 写文件替代 |
| `process_document()` | 拆分为 `get_outline()` |
| `summary` 格式 | 价值有限，AI 基于 markdown 分析更灵活 |

## 修复的问题

| 问题 | 修复 |
|------|------|
| `import re` 在函数内部 | 移到文件顶部 |
| 硬编码 `/tmp` | 使用 `tempfile.gettempdir()` |
| 重复的 subprocess 调用模式 | 提取 `_run_executor()` 私有方法 |

## 实现步骤

1. 创建 `cli.py`，从 `mcp_client.py` 提取 CLI 代码
2. 重构 `mcp_client.py` → `client.py`，删除冗余代码
3. 创建 `document.py`，提取 `save_document()` 和 `get_outline()`
4. 重命名文件（`document_processor.py` → `processor.py` 等）
5. 创建 `__init__.py`，导出公共 API
6. 更新 `SKILL.md`，添加入口选择指南
7. 更新 `feishu-prd-analyse.md`，使用新的 CLI 命令
8. 更新 `README.md`
