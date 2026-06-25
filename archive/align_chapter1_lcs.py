#!/usr/bin/env python3
"""
对齐 Whisper 转录结果与 PDF 文本，生成带时间戳的 JSON。

策略：
1. 读取 Whisper 输出的 segments（带 word timestamps）
2. 读取 PDF 清洗后的文本，按句子分割
3. 用模糊匹配（LCS / 编辑距离）将 Whisper segments 映射到 PDF 句子
4. 输出统一格式的 JSON：句子级 + 单词级时间戳
"""

import json
import re
from pathlib import Path


def split_pdf_sentences(text: str) -> list:
    """把 PDF 文本分成句子列表"""
    abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|Vol|vol|Ch|ch|pp|etc|i\.e|e\.g|a\.m|p\.m|A\.M|P\.M)'
    protected = re.sub(rf'({abbreviations})\.', r'\1<DOT>', text)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'\—])', protected)
    return [s.replace('<DOT>', '.').strip() for s in sentences if s.strip()]


def normalise(text: str) -> str:
    """标准化文本用于比对：小写、去标点、去多余空格"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def lcs_length(a: str, b: str) -> int:
    """计算两个字符串的最长公共子序列长度（基于词）"""
    aw = a.split()
    bw = b.split()
    m, n = len(aw), len(bw)
    # 使用滚动数组节省内存
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if aw[i - 1] == bw[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, prev
    return prev[n]


def align_segments(pdf_sentences: list, whisper_segments: list) -> dict:
    """
    将 Whisper segments 与 PDF 句子对齐。
    对每个 Whisper segment，在 PDF 句子中找到最长公共子序列最大的匹配。
    """
    aligned = []
    pdf_idx = 0
    
    for seg in whisper_segments:
        w_text = normalise(seg["text"])
        if not w_text:
            continue
        
        best_score = -1
        best_idx = pdf_idx
        
        # 在当前 PDF 位置附近搜索（窗口 5 句）
        search_start = max(0, pdf_idx - 2)
        search_end = min(len(pdf_sentences), pdf_idx + 5)
        
        for i in range(search_start, search_end):
            p_text = normalise(pdf_sentences[i])
            score = lcs_length(w_text, p_text)
            if score > best_score:
                best_score = score
                best_idx = i
        
        # 接受最佳匹配，不再设硬阈值（短 segment 对长 PDF 句子的 LCS 天然低）
        aligned.append({
            "pdf_index": best_idx,
            "pdf_text": pdf_sentences[best_idx],
            "whisper_text": seg["text"],
            "start": seg["start"],
            "end": seg["end"],
            "words": seg.get("words", []),
            "match_score": best_score,
        })
        pdf_idx = best_idx + 1  # 下次从后面开始搜
    
    return aligned


def build_output(pdf_sentences: list, aligned_segments: list) -> dict:
    """构建最终的 JSON 输出格式"""
    output = {
        "meta": {
            "book": "Harry Potter and the Philosopher's Stone",
            "chapter": 1,
            "title": "The Boy Who Lived",
            "audio_file": "01.The Boy Who Lived.mp3",
            "align_method": "whisper-base + lcs-mapping",
        },
        "sentences": [],
    }
    
    # 按 PDF 句子索引分组
    sentence_map = {}
    for seg in aligned_segments:
        idx = seg.get("pdf_index")
        if idx is None:
            continue
        if idx not in sentence_map:
            sentence_map[idx] = {
                "text": pdf_sentences[idx],
                "start": seg["start"],
                "end": seg["end"],
                "words": [],
            }
        else:
            sentence_map[idx]["end"] = seg["end"]
        
        # 合并单词时间戳
        for w in seg.get("words", []):
            sentence_map[idx]["words"].append({
                "text": w["word"],
                "start": w["start"],
                "end": w["end"],
            })
    
    # 按索引排序输出
    for idx in sorted(sentence_map.keys()):
        s = sentence_map[idx]
        output["sentences"].append({
            "id": f"c1_s{idx+1:03d}",
            "text": s["text"],
            "start": round(s["start"], 3),
            "end": round(s["end"], 3),
            "words": [
                {"text": w["text"], "start": round(w["start"], 3), "end": round(w["end"], 3)}
                for w in s["words"]
            ],
        })
    
    return output


def main():
    whisper_path = Path("/Users/cathy/Documents/workspace/louder/resource/01.The Boy Who Lived.json")
    pdf_path = Path("/Users/cathy/Documents/workspace/louder/resource/chapter1_text_clean.txt")
    output_path = Path("/Users/cathy/Documents/workspace/louder/resource/chapter1_aligned.json")
    
    if not whisper_path.exists():
        print(f"Whisper output not found: {whisper_path}")
        print("Please run whisper transcription first.")
        return
    
    print("Loading Whisper output...")
    with open(whisper_path, "r", encoding="utf-8") as f:
        whisper_data = json.load(f)
    
    print("Loading PDF text...")
    with open(pdf_path, "r", encoding="utf-8") as f:
        pdf_text = f.read()
    
    pdf_sentences = split_pdf_sentences(pdf_text)
    print(f"PDF sentences: {len(pdf_sentences)}")
    
    whisper_segments = whisper_data.get("segments", [])
    print(f"Whisper segments: {len(whisper_segments)}")
    
    print("Aligning...")
    aligned = align_segments(pdf_sentences, whisper_segments)
    
    matched = sum(1 for a in aligned if a.get("pdf_index") is not None)
    print(f"Matched: {matched}/{len(aligned)} segments")
    
    output = build_output(pdf_sentences, aligned)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Output saved to: {output_path}")
    print(f"   Total aligned sentences: {len(output['sentences'])}")


if __name__ == "__main__":
    main()
