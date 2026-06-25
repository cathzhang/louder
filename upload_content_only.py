#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向已存在的飞书文档写入 Markdown 内容
"""

import json
from pathlib import Path

import lark_oapi as lark
from feishu_docx.core.writer import FeishuWriter

CONFIG_PATH = Path.home() / ".feishu-docx" / "config.json"
DOCUMENT_ID = "WKSad1yy6oJbEWxEqJvcJ90tnPe"
MARKDOWN_FILE = Path(__file__).parent / "docs_for_feishu.md"


def get_tenant_token(app_id: str, app_secret: str) -> str:
    client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.ERROR)
        .build()
    )
    request = (
        lark.api.auth.v3.InternalTenantAccessTokenRequest.builder()
        .request_body(
            lark.api.auth.v3.InternalTenantAccessTokenRequestBody.builder()
            .app_id(app_id)
            .app_secret(app_secret)
            .build()
        )
        .build()
    )
    response = client.auth.v3.tenant_access_token.internal(request)
    data = json.loads(response.raw.content)
    return data["tenant_access_token"]


def main():
    print("=" * 50)
    print("写入 Markdown 内容到飞书文档")
    print("=" * 50)

    config = json.load(open(CONFIG_PATH))
    print(f"\n🔑 获取 token...")
    token = get_tenant_token(config["app_id"], config["app_secret"])
    print("   成功")

    print(f"\n📝 写入内容...")
    writer = FeishuWriter()
    writer.write_content(
        document_id=DOCUMENT_ID,
        file_path=str(MARKDOWN_FILE),
        user_access_token=token,
        append=False,
    )

    print("\n" + "=" * 50)
    print("🎉 内容写入完成！")
    print(f"   飞书文档: https://feishu.cn/docx/{DOCUMENT_ID}")
    print("=" * 50)


if __name__ == "__main__":
    main()
