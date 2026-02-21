"""
Document Operations - 高级文档操作

提供 save_document 和 get_outline 便捷函数。
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional

from client import FeishuMCPClient
from processor import DocumentProcessor


def save_document(url_or_id: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    保存飞书文档到本地文件

    Args:
        url_or_id: 文档 URL 或 ID（支持 /docx/ 和 /wiki/ 格式）
        output_dir: 输出目录（默认系统临时目录）

    Returns:
        {
            "document_id": "xxx",
            "title": "文档标题",
            "blocks_file": "/tmp/document_xxx_blocks.json",
            "markdown_file": "/tmp/document_xxx.md"
        }
    """
    client = FeishuMCPClient()
    processor = DocumentProcessor()

    # 确定输出目录
    output_path = Path(output_dir) if output_dir else Path(tempfile.gettempdir())

    # 检测文档类型
    is_wiki = "/wiki/" in url_or_id

    # 1. 获取文档信息
    if is_wiki:
        doc_info = client.call("get_feishu_document_info", {
            "documentId": url_or_id,
            "documentType": "wiki"
        })
        document_id = doc_info.get("obj_token") or doc_info.get("documentId")
    else:
        # 从 URL 提取 ID 或直接使用
        if url_or_id.startswith("http"):
            match = re.search(r"/docx/([^/?]+)", url_or_id)
            document_id = match.group(1) if match else url_or_id
        else:
            document_id = url_or_id

        doc_info = client.call("get_feishu_document_info", {
            "documentId": document_id
        })

    document_id = document_id or doc_info.get("obj_token", doc_info.get("documentId", "unknown"))

    # 2. 生成文件路径
    safe_id = document_id.replace("/", "_").replace(":", "_")[:50]
    blocks_file = output_path / f"document_{safe_id}_blocks.json"
    markdown_file = output_path / f"document_{safe_id}.md"

    # 3. 获取文档块并保存
    blocks = client.call("get_feishu_document_blocks", {
        "documentId": document_id
    })

    with open(blocks_file, 'w', encoding='utf-8') as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)

    # 4. 转换为 Markdown 并保存
    markdown = processor.to_markdown(blocks)

    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return {
        "document_id": document_id,
        "title": doc_info.get("title", ""),
        "blocks_file": str(blocks_file),
        "markdown_file": str(markdown_file)
    }


def get_outline(blocks_file: str) -> str:
    """
    提取文档目录结构

    Args:
        blocks_file: 文档块 JSON 文件路径

    Returns:
        Markdown 格式的目录
    """
    processor = DocumentProcessor()

    with open(blocks_file, 'r', encoding='utf-8') as f:
        blocks = json.load(f)

    return processor.get_outline(blocks)
