# 更新日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 支持飞书多维表格
- 支持飞书表单数据提取
- 添加更多文档格式导出选项

## [1.1.0] - 2026-02-20

### 新增
- **零上下文 MCP 调用** - 通过 Python 启动 MCP Client 调用服务，响应不注入 context
- **用户凭证配置** - `setup-feishu.py` 交互式配置脚本，支持环境变量覆盖
- **统一 CLI 入口** - `mcp_client.py --fetch` 获取文档并保存到临时文件
- **临时文件命名** - 使用 `document_{id}_blocks.json` 格式，便于管理

### 变更
- 移除硬编码凭证 `mcp-config.json`，改为用户配置
- 移除 `mcp_utils.md`，API 文档整合到 `SKILL.md`
- `document_processor.py` 不再提供 CLI 入口，统一通过 `mcp_client.py` 调用

### 改进
- 节省 ~15,000 tokens（MCP 工具定义不加载到 context）
- 节省大量 tokens（文档响应保存到临时文件，不注入 context）

## [1.0.0] - 2026-02-01

### 新增
- 初始版本发布
- 飞书文档分析功能
- 支持 Wiki 和普通文档
- Markdown 自动转换
- 表格数据提取
- 文档搜索功能
- Token 节省优化（96-99%）
- 一键安装配置脚本
- 完整的 Python 处理脚本
- PRD 分析参考清单

### 文档
- 完整的 README 说明
- SKILL.md 定义文件
- 故障排查指南

[Unreleased]: https://github.com/Tbthr/feishu-skill/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Tbthr/feishu-skill/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Tbthr/feishu-skill/releases/tag/v1.0.0
