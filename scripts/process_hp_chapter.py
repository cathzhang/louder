#!/usr/bin/env python3
"""
处理 Harry Potter 单章：提取 PDF 文本、清洗、分句、转 m4a、Whisper 转录、
单词级强制对齐，并生成 web/小程序数据。

示例：
    python3 scripts/process_hp_chapter.py --chapter 2 --title "The Vanishing Glass" --pdf-pages 23 31
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pdfplumber
import whisper

# 把项目根目录加入路径，方便导入自定义模块
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from realign_whisper import (
    assign_timestamps,
    extract_whisper_words,
    needleman_wunsch,
)
from sentence_utils import split_sentences

RESOURCE_DIR = ROOT / "resource"
WEB_DATA_DIR = ROOT / "web" / "data"
MP_DATA_DIR = ROOT / "miniprogram" / "data"

# ffmpeg / ffprobe
os.environ["PATH"] = str(ROOT / "bin") + ":" + os.environ.get("PATH", "")


def int_to_roman(num: int) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    for v, s in zip(val, syb):
        while num >= v:
            roman_num += s
            num -= v
    return roman_num


def extract_pdf(chapter: int, start_page: int, end_page: int, title: str) -> str:
    """从 PDF 提取指定页，保留换行，写入 chapter{N}_text_raw.txt"""
    pdf_path = RESOURCE_DIR / "1.英文电子书-Harry Potter and the Philosopher's Stone.pdf"
    output_path = RESOURCE_DIR / f"chapter{chapter}_text_raw.txt"

    with pdfplumber.open(str(pdf_path)) as pdf:
        # 参数是 1-indexed 闭区间，转成 0-indexed 切片
        pages = pdf.pages[start_page - 1 : end_page]
        full_text = "\n".join(p.extract_text() or "" for p in pages)

    output_path.write_text(full_text, encoding="utf-8")
    print(f"[extract] {output_path} ({len(full_text)} chars)")
    return full_text


def clean_text(chapter: int, title: str, raw_text: str) -> str:
    """清洗 PDF 文本：去页眉页脚、去连字符、去章节标题"""
    output_path = RESOURCE_DIR / f"chapter{chapter}_text_clean.txt"

    text = raw_text

    # 1. 去页眉/页脚
    text = re.sub(r'^\d+\s+HARRY POTTER\s*$', '', text, flags=re.MULTILINE)
    # 章节标题页脚，例如 "THE VANISHING GLASS 27"
    upper_title = title.upper()
    text = re.sub(rf'^{re.escape(upper_title)}\s+\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)

    # 2. 处理行尾连字符
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # 3. 单换行变空格，段落合并
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r'\n+', ' ', text)

    # 4. 合并多空格
    text = re.sub(r' +', ' ', text).strip()

    # 5. 去掉章节标题
    roman = int_to_roman(chapter)
    text = re.sub(rf'^—\s*CHAPTER\s+{roman}\s*—\s*{re.escape(title)}\s*', '', text, flags=re.IGNORECASE).strip()

    output_path.write_text(text, encoding="utf-8")
    print(f"[clean]   {output_path} ({len(text)} chars, {len(text.split())} words)")
    return text


def split_and_save(chapter: int, text: str):
    """分句并保存"""
    output_path = RESOURCE_DIR / f"chapter{chapter}_sentences.txt"
    sentences = split_sentences(text)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, s in enumerate(sentences, 1):
            f.write(f"{i}\t{s}\n")
    print(f"[split]   {output_path} ({len(sentences)} sentences)")
    return sentences


def convert_to_m4a(mp3_path: Path, m4a_path: Path):
    """mp3 -> m4a (AAC)"""
    if m4a_path.exists() and m4a_path.stat().st_size > 0:
        print(f"[audio]   {m4a_path} already exists, skip conversion")
        return
    if m4a_path.exists():
        print(f"[audio]   {m4a_path} is empty, re-converting")

    print(f"[audio]   converting {mp3_path.name} -> {m4a_path.name}")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path), "-vn", "-c:a", "aac", "-b:a", "128k", str(m4a_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[audio]   done: {m4a_path}")


def run_whisper(mp3_path: Path, json_path: Path, model_name: str = "base"):
    """Whisper 转录"""
    if json_path.exists():
        print(f"[whisper] {json_path} already exists, skip")
        return

    print(f"[whisper] loading model '{model_name}' ...")
    model = whisper.load_model(model_name)

    print(f"[whisper] transcribing {mp3_path.name} ...")
    result = model.transcribe(
        str(mp3_path),
        language="en",
        word_timestamps=True,
        verbose=True,
    )

    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[whisper] saved {json_path} ({len(result['segments'])} segments)")


def tokenize_sentences(text: str):
    """把清洗后的文本分词，返回 [(word, sentence_idx), ...] 和句子列表"""
    sentences = split_sentences(text)
    words = []
    for si, sent in enumerate(sentences):
        for w in sent.split():
            words.append((w, si))
    return words, sentences


def extract_whisper_words_chapter(whisper_data: dict, title: str):
    """提取 Whisper 单词时间戳，过滤片头/标题段"""
    skip_prefixes = [
        "harry potter and the philosopher",
        "chapter",
        title.lower(),
    ]
    words = []
    for seg in whisper_data["segments"]:
        text = seg["text"].strip()
        lower = text.lower()
        if any(lower.startswith(p) for p in skip_prefixes):
            continue
        for w in seg.get("words", []):
            words.append((w["word"].strip(), w["start"], w["end"]))
    return words


def build_json(chapter: int, title: str, audio_file: str, pdf_sentences: list, word_data: list) -> dict:
    """按句子分组构建最终 JSON"""
    output = {
        "meta": {
            "book": "Harry Potter and the Philosopher's Stone",
            "chapter": chapter,
            "title": title,
            "audio_file": audio_file,
            "align_method": "needleman-wunsch global word alignment",
        },
        "sentences": [],
    }

    sentence_words = {}
    for word, sent_idx, start, end in word_data:
        sentence_words.setdefault(sent_idx, []).append((word, start, end))

    for si in sorted(sentence_words.keys()):
        words = sentence_words[si]
        if not words:
            continue
        text = pdf_sentences[si]
        output["sentences"].append({
            "id": f"c{chapter}_s{si + 1:03d}",
            "text": text,
            "start": round(words[0][1], 3),
            "end": round(words[-1][2], 3),
            "words": [
                {"text": w, "start": round(s, 3), "end": round(e, 3)}
                for w, s, e in words
            ],
        })

    return output


def fix_alignment(data: dict) -> dict:
    """排序、重编号、去重、去空格"""
    data["sentences"].sort(key=lambda s: s["start"])
    for i, s in enumerate(data["sentences"], 1):
        chapter = s["id"].split("_")[0][1:]  # c2_s001 -> 2
        s["id"] = f"c{chapter}_s{i:03d}"
    for s in data["sentences"]:
        for w in s.get("words", []):
            w["text"] = w["text"].strip()
        seen = set()
        unique = []
        for w in s.get("words", []):
            key = (w["text"], round(w["start"], 2), round(w["end"], 2))
            if key not in seen:
                seen.add(key)
                unique.append(w)
        s["words"] = unique
    return data


def align_chapter(chapter: int, title: str, clean_text: str, whisper_json: Path):
    """强制对齐 PDF 文本与 Whisper 转录"""
    aligned_path = RESOURCE_DIR / f"chapter{chapter}_aligned.json"
    if aligned_path.exists():
        print(f"[align]   {aligned_path} already exists, skip")
        return json.loads(aligned_path.read_text(encoding="utf-8"))

    print("[align]   tokenizing PDF ...")
    pdf_words, pdf_sentences = tokenize_sentences(clean_text)

    print("[align]   loading whisper words ...")
    whisper_data = json.loads(whisper_json.read_text(encoding="utf-8"))
    whisper_words = extract_whisper_words_chapter(whisper_data, title)

    print(f"[align]   PDF words: {len(pdf_words)}, Whisper words: {len(whisper_words)}")
    alignment = needleman_wunsch(pdf_words, whisper_words)
    word_data = assign_timestamps(pdf_words, whisper_words, alignment)

    output = build_json(chapter, title, f"{chapter:02d}.{title}.m4a", pdf_sentences, word_data)
    output = fix_alignment(output)

    aligned_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[align]   saved {aligned_path} ({len(output['sentences'])} sentences)")
    return output


def export_data(chapter: int, data: dict):
    """导出到 web/data 和 miniprogram/data"""
    web_path = WEB_DATA_DIR / f"chapter{chapter}.json"
    js_path = MP_DATA_DIR / f"chapter{chapter}-data.js"

    json_text = json.dumps(data, indent=2, ensure_ascii=False)
    web_path.write_text(json_text, encoding="utf-8")
    js_path.write_text("module.exports = " + json_text + ";\n", encoding="utf-8")
    print(f"[export]  {web_path}")
    print(f"[export]  {js_path}")


def main():
    parser = argparse.ArgumentParser(description="处理 Harry Potter 单章")
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--pdf-pages", type=int, nargs=2, required=True, metavar=("START", "END"))
    parser.add_argument("--skip-whisper", action="store_true", help="跳过 Whisper 转录（如果已有 JSON）")
    parser.add_argument("--skip-align", action="store_true", help="跳过对齐（如果已有对齐 JSON）")
    args = parser.parse_args()

    chapter = args.chapter
    title = args.title
    start_page, end_page = args.pdf_pages

    print(f"=== Processing Chapter {chapter}: {title} ===\n")

    # 1. PDF
    raw_text = extract_pdf(chapter, start_page, end_page, title)
    clean = clean_text(chapter, title, raw_text)
    split_and_save(chapter, clean)

    # 2. 音频
    mp3_path = RESOURCE_DIR / f"{chapter:02d}.{title}.mp3"
    m4a_path = RESOURCE_DIR / f"{chapter:02d}.{title}.m4a"
    whisper_json = RESOURCE_DIR / f"{chapter:02d}.{title}.json"

    convert_to_m4a(mp3_path, m4a_path)

    if not args.skip_whisper:
        run_whisper(mp3_path, whisper_json)

    # 3. 对齐与导出
    if not args.skip_align:
        data = align_chapter(chapter, title, clean, whisper_json)
        export_data(chapter, data)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
