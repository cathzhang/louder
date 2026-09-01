# 大声朗读

将英文有声书（PDF 文本 + 音频）进行逐句、逐词对齐，在网页/小程序上实现“点句播放、选词播放”。

已上线内容：
- 《Harry Potter and the Philosopher's Stone》Chapter 1 · The Boy Who Lived、Chapter 2 · The Vanishing Glass
- 《新概念英语第二册》全部 96 课

---

## 目录结构

```
louder/
├── archive/                  # 废弃/备份脚本
├── bin/                      # ffmpeg / ffprobe 二进制
├── cdn/                      # 待上传 CDN 的生成数据
│   └── nce2/                 # 新概念英语第二册对齐 JSON
│       ├── lesson01.json
│       ├── ...
│       ├── lesson96.json
│       └── manifest.json
├── resource/                 # 原始素材与对齐结果
│   ├── 1.英文电子书-Harry Potter and the Philosopher's Stone.pdf
│   ├── 新概念英语第二册 (亚历山大  何其莘) (Z-Library).pdf
│   ├── 新概念英语（第2册）美音（MP3+LRC）/
│   ├── 01.The Boy Who Lived.mp3      # 原始音频（Whisper 输入）
│   ├── 01.The Boy Who Lived.m4a      # 前端播放音频
│   ├── 01.The Boy Who Lived.json     # Whisper 转录结果
│   ├── chapter1_text_raw.txt         # PDF 原始文本
│   ├── chapter1_text_clean.txt       # 清洗后文本
│   ├── chapter1_sentences.txt        # 分句结果
│   └── chapter1_aligned.json         # 最终对齐结果
├── scripts/                  # 数据处理脚本
│   ├── extract_text.py       # 从 PDF 提取文本（Harry Potter）
│   ├── clean_text.py         # 清洗文本
│   ├── split_sentences.py    # 英文分句
│   ├── run_whisper.py        # Whisper 转录音频
│   ├── realign_whisper.py    # Whisper + PDF 强制对齐
│   ├── fix_alignment.py      # 对齐后处理
│   ├── check_alignment.py    # 对齐质量检查
│   ├── check_quality.py      # 对齐质量检查（另一维度）
│   └── process_nce2.py       # 新概念英语第二册批量处理
├── web/                      # H5 前端页面
│   ├── index.html            # 书目列表页
│   ├── chapters.html         # 章节目录页
│   ├── chapter.html          # 章节播放页
│   ├── app.js
│   ├── style.css
│   ├── config.js             # H5 环境配置（本地/线上 CDN）
│   └── data/                 # 前端使用的对齐数据
│       └── chapter1.json     # 由 chapter1_aligned.json 同步
├── miniprogram/              # 微信小程序源码（原生实现）
│   ├── data/                 # 小程序包内对齐数据与书目配置
│   ├── pages/                # 原生小程序页面
│   └── README.md
├── start_server.py           # 本地 HTTP 服务器（支持 Range 请求）
├── publish_to_feishu.py      # 创建并上传飞书文档
├── upload_content_only.py    # 更新已有飞书文档内容
└── docs_for_feishu.md        # 飞书知识库文档源文件
```

---

## 快速启动

```bash
# 1. 启动本地服务器
python3 start_server.py

# 2. 浏览器打开
# http://localhost:8000/web/index.html
#
# 页面导航：
#   书目列表  →  章节目录  →  章节播放页
```

服务器支持 HTTP `Range` 请求，音频可以正常 seek 和逐句播放。

---

## 完整数据处理流程

### Harry Potter

```bash
# 1. 提取 PDF 文本
python3 scripts/extract_text.py

# 2. 清洗文本
python3 scripts/clean_text.py

# 3. 英文分句
python3 scripts/split_sentences.py

# 4. Whisper 转录音频
python3 scripts/run_whisper.py

# 5. 强制对齐（Whisper 时间戳 + PDF 文本）
python3 scripts/realign_whisper.py

# 6. 后处理（排序、重编号、去重）
python3 scripts/fix_alignment.py

# 7. 质量检查
python3 scripts/check_alignment.py
python3 scripts/check_quality.py
```

### 新概念英语第二册

素材准备：
- PDF：`resource/新概念英语第二册 (亚历山大  何其莘) (Z-Library).pdf`
- 音频 + LRC：`resource/新概念英语（第2册）美音（MP3+LRC）/`

执行批量处理：

```bash
python3 scripts/process_nce2.py
```

输出：`cdn/nce2/lesson01.json` ~ `cdn/nce2/lesson96.json`，以及 `cdn/nce2/manifest.json`。

处理逻辑：
1. 用 PyMuPDF 提取 PDF 全部文本；
2. 按 `Lesson N` 分割并跳过目录页；
3. 从“听录音，然后回答以下问题。”之后到“New words and expressions”之前提取课文正文；
4. 解析 LRC 文件得到句子/短语级时间戳；
5. 把 LRC 行按顺序与 PDF 正文单词对齐，得到精确文本；
6. 按每行单词数等分时间戳，生成单词级对齐。

---

## 同步前端数据

`web/data/chapter1.json` 是 H5 前端读取的对齐数据，当前与 `resource/chapter1_aligned.json` 一致。更新对齐结果后，手动同步：

```bash
cp resource/chapter1_aligned.json web/data/chapter1.json
```

---

## 微信小程序（原生实现）

项目包含 `miniprogram/` 目录，采用 **原生小程序页面** 实现，不再使用 web-view 嵌入 H5。

- 书目列表、章节目录、播放页均为原生 WXML/WXSS/JS；
- Harry Potter 对齐 JSON 数据放在 `miniprogram/data/` 内，随小程序包发布；
- 新概念英语第二册 JSON 数据与音频均从云存储 CDN 下载，不占用小程序包体积；
- 书目与章节配置集中在 `miniprogram/data/books.js`。

详见 [`miniprogram/README.md`](miniprogram/README.md)。

---

## 上传 CDN

### 新概念英语第二册

把生成好的 JSON 和原始 MP3 上传到腾讯云存储对应目录：

```
数据：https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/data/nce2/
音频：https://7072-prod-d5g5fun3a019d78b1-1447117358.tcb.qcloud.la/audio/nce2/
```

上传清单：`cdn/nce2/manifest.json`。

---

## H5 本地部署

`web/` 目录保留为本地 H5 站点，用于浏览器访问或本地调试：

```bash
python3 start_server.py
# 打开 http://localhost:8000/web/index.html
```

本地开发时，`web/config.js` 中的 `CDN_BASE` 保持为空，自动使用相对路径。

---

## 飞书文档

技术方案文档源文件为 `docs_for_feishu.md`。

- 首次上传到知识库：
  ```bash
  python3 publish_to_feishu.py
  ```
- 更新已有文档内容：
  ```bash
  python3 upload_content_only.py
  ```

飞书应用配置位于 `~/.feishu-docx/config.json`。

---

## 依赖

- Python 3.8+
- `PyMuPDF`
- `openai-whisper`
- `feishu-docx`
- `lark-oapi`

---

## 已实现 vs 待完善

- [x] PDF 文本提取与清洗
- [x] 英文分句
- [x] Whisper 转录
- [x] 单词级强制对齐（Needleman-Wunsch）
- [x] 对齐质量检查
- [x] 网页逐句/选词播放
- [x] 书目列表页 / 章节目录页 / 章节播放页导航
- [x] 播放速度控制（0.5 / 0.75 / 1 / 1.25 / 1.5 / 2x）
- [x] 连续播放功能
- [x] 飞书文档上传
- [x] 微信小程序基础骨架（web-view 嵌入 H5）
- [x] H5 环境配置（支持本地开发与线上 CDN）
- [x] 微信小程序原生实现（书目/章节/播放器）
- [x] 新概念英语第二册 96 课数据生成
- [x] 小程序多书籍支持（Harry Potter + 新概念英语第二册）
- [ ] 微信小程序正式部署与审核
- [ ] 播放器增强（进度条、上一句/下一句、音量控制）
- [ ] H5 端接入新概念英语第二册
