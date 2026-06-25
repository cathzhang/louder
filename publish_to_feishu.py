#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传 Markdown 文档到飞书"大声朗读"知识库
"""

import json
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.auth.v3 import (
    InternalTenantAccessTokenRequest,
    InternalTenantAccessTokenRequestBody,
)
from lark_oapi.api.wiki.v2 import CreateSpaceNodeRequest, Node

from feishu_docx.core.writer import FeishuWriter

# 配置
CONFIG_PATH = Path.home() / ".feishu-docx" / "config.json"
SPACE_ID = "7645180380080770007"
DOC_TITLE = "大声朗读 — 技术方案与实施计划"
MARKDOWN_FILE = Path(__file__).parent / "docs_for_feishu.md"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token"""
    client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.ERROR)
        .build()
    )

    request = (
        InternalTenantAccessTokenRequest.builder()
        .request_body(
            InternalTenantAccessTokenRequestBody.builder()
            .app_id(app_id)
            .app_secret(app_secret)
            .build()
        )
        .build()
    )

    response = client.auth.v3.tenant_access_token.internal(request)
    if not response.success():
        raise RuntimeError(f"获取 token 失败: {response.msg}")

    import json
    data = json.loads(response.raw.content)
    return data["tenant_access_token"]


def create_wiki_document(space_id: str, title: str, token: str) -> str:
    """在知识库中创建文档，返回 document_id (obj_token)"""
    config = load_config()
    client = (
        lark.Client.builder()
        .app_id(config["app_id"])
        .app_secret(config["app_secret"])
        .log_level(lark.LogLevel.ERROR)
        .build()
    )

    # 方案：先创建普通文档，再移动到知识库
    # 1. 创建空白文档
    from lark_oapi.api.docx.v1 import (
        CreateDocumentRequest,
        CreateDocumentRequestBody,
    )
    body = CreateDocumentRequestBody.builder().title(title).build()
    doc_request = CreateDocumentRequest.builder().request_body(body).build()
    option = lark.RequestOption.builder().tenant_access_token(token).build()
    doc_response = client.docx.v1.document.create(doc_request, option)

    if not doc_response.success():
        raise RuntimeError(f"创建文档失败: {doc_response.msg}")

    document_id = doc_response.data.document.document_id
    print(f"✅ 空白文档已创建: {title}")
    print(f"   document_id: {document_id}")

    # 2. 移动到知识库
    from lark_oapi.api.wiki.v2 import MoveDocsToWikiSpaceNodeRequest
    from lark_oapi.api.wiki.v2.model import MoveDocsToWikiSpaceNodeRequestBody

    move_body = (
        MoveDocsToWikiSpaceNodeRequestBody.builder()
        .parent_wiki_token("")  # 空字符串表示根目录
        .obj_type("docx")
        .obj_token(document_id)
        .build()
    )
    move_request = (
        MoveDocsToWikiSpaceNodeRequest.builder()
        .space_id(space_id)
        .request_body(move_body)
        .build()
    )
    move_response = client.wiki.v2.space_node.move_docs_to_wiki(move_request, option)

    if not move_response.success():
        # 移动失败，尝试获取详细错误
        import json
        try:
            err_detail = json.loads(move_response.raw.content)
            err_msg = err_detail.get("msg", move_response.msg)
        except Exception:
            err_msg = move_response.msg
        raise RuntimeError(f"移动到知识库失败: {err_msg}")

    print(f"✅ 文档已移动到知识库: 大声朗读")
    return document_id


def upload_content(document_id: str, file_path: Path, token: str) -> None:
    """向文档写入 Markdown 内容"""
    writer = FeishuWriter()
    writer.write_content(
        document_id=document_id,
        file_path=str(file_path),
        user_access_token=token,
        append=False,
    )
    print(f"✅ 内容已写入: {file_path.name}")
    print(f"   飞书文档地址: https://feishu.cn/docx/{document_id}")


def main():
    print("=" * 50)
    print("飞书文档上传")
    print("=" * 50)

    # 1. 加载配置
    config = load_config()
    print(f"\n📋 应用: {config['app_id']}")
    print(f"📚 知识库: 大声朗读 ({SPACE_ID})")
    print(f"📄 文档: {DOC_TITLE}")
    print(f"📝 源文件: {MARKDOWN_FILE}")

    # 2. 获取 token
    print("\n🔑 获取 tenant_access_token...")
    token = get_tenant_token(config["app_id"], config["app_secret"])
    print("   成功")

    # 3. 创建知识库文档
    print("\n📤 创建知识库文档...")
    document_id = create_wiki_document(SPACE_ID, DOC_TITLE, token)

    # 4. 写入内容
    print("\n📝 写入 Markdown 内容...")
    upload_content(document_id, MARKDOWN_FILE, token)

    print("\n" + "=" * 50)
    print("🎉 上传完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
