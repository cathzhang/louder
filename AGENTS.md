# 大声朗读 — Agent 工作指南

## 飞书文档上传

**环境已配置，可直接使用。**

```bash
# 已安装的包
feishu-docx==0.2.5    # 飞书文档读写工具
lark-oapi==1.6.2      # 飞书开放平台 SDK

# 配置文件
~/.feishu-docx/config.json
```

**目标知识库：**

| 知识库名称 | space_id |
|-----------|----------|
| 大声朗读 | `7645180380080770007` |

### 上传方式

**方式一：使用已有脚本（推荐）**

项目根目录已有 `publish_to_feishu.py`，可直接运行：

```bash
cd /Users/cathy/Documents/workspace/louder
python3 publish_to_feishu.py
```

> 该脚本默认上传 `docs_for_feishu.md` 到"大声朗读"知识库。
>
> 若文档已存在，只需更新内容，可运行 `python3 upload_content_only.py`。

**方式二：自定义上传**

如需上传其他 Markdown 文件或修改标题，可直接调用 `feishu_docx` 或 `lark_oapi`：

```python
from feishu_docx.core.writer import FeishuWriter

writer = FeishuWriter()
doc = writer.create_document(title="文档标题", content="# Markdown内容")
```

或参考 `publish_to_feishu.py` 中的 `lark_oapi` 调用方式，直接操作 API。

### 注意事项
- 上传前确保飞书应用已被添加到"大声朗读"知识库的协作者中
- `MarkdownToBlocks` 转换时会过滤表格等复杂嵌套块，如需完整表格支持，需手动调整 block 结构
- 文档创建后可在飞书 wiki 中调整目录位置
