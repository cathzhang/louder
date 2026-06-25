# 大声朗读

将英文有声书（PDF 文本 + 音频）进行逐句、逐词对齐，在网页上实现“点句播放、选词播放”。

首个内容载体：《Harry Potter and the Philosopher's Stone》Chapter 1 · The Boy Who Lived。

---

## 目录结构

```
louder/
├── archive/                  # 废弃/备份脚本
├── bin/                      # ffmpeg / ffprobe 二进制
├── resource/                 # 原始素材与对齐结果
│   ├── 1.英文电子书-Harry Potter and the Philosopher's Stone.pdf
│   ├── 01.The Boy Who Lived.mp3      # 原始音频（Whisper 输入）
│   ├── 01.The Boy Who Lived.m4a      # 前端播放音频
│   ├── 01.The Boy Who Lived.json     # Whisper 转录结果
│   ├── chapter1_text_raw.txt         # PDF 原始文本
│   ├── chapter1_text_clean.txt       # 清洗后文本
│   ├── chapter1_sentences.txt        # 分句结果
│   └── chapter1_aligned.json         # 最终对齐结果
├── scripts/                  # 数据处理脚本
│   ├── extract_text.py       # 从 PDF 提取文本
│   ├── clean_text.py         # 清洗文本
│   ├── split_sentences.py    # 英文分句
│   ├── run_whisper.py        # Whisper 转录音频
│   ├── realign_whisper.py    # Whisper + PDF 强制对齐
│   ├── fix_alignment.py      # 对齐后处理
│   ├── check_alignment.py    # 对齐质量检查
│   └── check_quality.py      # 对齐质量检查（另一维度）
├── web/                      # 前端页面
│   ├── index.html            # 书目列表页
│   ├── chapters.html         # 章节目录页
│   ├── chapter.html          # 章节播放页
│   ├── app.js
│   ├── style.css
│   └── data/                 # 前端使用的对齐数据
│       └── chapter1.json     # 由 chapter1_aligned.json 同步
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

如果要重新生成对齐数据，按以下顺序执行：

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

---

## 同步前端数据

`web/data.json` 是前端读取的对齐数据，当前与 `resource/chapter1_aligned.json` 一致。更新对齐结果后，手动同步：

```bash
cp resource/chapter1_aligned.json web/data/chapter1.json
```

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
- `pdfplumber`
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
- [ ] 多章节数据扩展（目前只有 Chapter 1）
- [ ] 播放器增强（进度条、上一句/下一句、音量控制）
