# 贡献指南

感谢你对 feishu-analyst skill 的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 在 [Issues](https://github.com/your-username/feishu-skill/issues) 中搜索是否已有相同问题
2. 如果没有，创建新的 Issue，详细描述：
   - 问题类型（Bug / Feature Request）
   - 复现步骤（针对 Bug）
   - 期望行为
   - 环境信息（操作系统、Python 版本等）

### 提交代码

1. **Fork 本仓库**
   ```bash
   git clone https://github.com/your-username/feishu-skill.git
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或修复 bug
   git checkout -b fix/your-bug-fix
   ```

3. **进行修改**
   - 遵循现有代码风格
   - 添加必要的注释
   - 更新相关文档

4. **提交变更**
   ```bash
   git add .
   git commit -m "feat: add xxx feature"
   ```

5. **推送到你的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 描述你的变更内容
   - 关联相关的 Issue
   - 等待代码审查

### 代码规范

- **Python 代码**：遵循 PEP 8
- **Commit 消息**：使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式
  - `feat:` 新功能
  - `fix:` Bug 修复
  - `docs:` 文档更新
  - `style:` 代码格式调整
  - `refactor:` 代码重构
  - `test:` 测试相关
  - `chore:` 构建/工具相关

### 开发环境

```bash
# 安装依赖（如需要）
pip install -r requirements.txt

# 运行测试（如需要）
pytest tests/
```

## 开发指南

### 添加新的处理器

在 `.claude/skills/feishu-analyst/scripts/` 下创建新的处理器脚本：

```python
# your_processor.py
from typing import Any, Dict

class YourProcessor:
    def process(self, data: Dict[str, Any]) -> str:
        """处理数据并返回格式化结果"""
        # 实现你的处理逻辑
        return result
```

### 更新文档

- 修改 `SKILL.md` 添加新功能说明
- 更新 `README.md`（面向用户的变更）
- 更新 `CHANGELOG.md`

## 行为准则

- 尊重所有贡献者
- 欢迎不同观点的建设性讨论
- 专注于项目本身的最优解

## 许可证

提交代码即表示你同意将你的贡献以 [MIT License](LICENSE) 发布。
