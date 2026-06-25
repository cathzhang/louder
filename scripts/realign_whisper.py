#!/usr/bin/env python3
"""
精确对齐策略：Needleman-Wunsch 全局单词对齐。
把 PDF 的每个单词和 Whisper 的每个单词做全局序列比对，
然后为 PDF 中的每个单词分配 Whisper 对应单词的时间戳。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

WHISPER_PATH = RESOURCE_DIR / "01.The Boy Who Lived.json"
PDF_PATH = RESOURCE_DIR / "chapter1_text_clean.txt"
OUTPUT_PATH = RESOURCE_DIR / "chapter1_aligned.json"

MATCH_SCORE = 2
MISMATCH_SCORE = -1
GAP_SCORE = -1


def normalize_word(w: str) -> str:
    """标准化单词用于比对：去标点、小写"""
    return re.sub(r'[^\w]', '', w.lower())


def tokenize_pdf(text: str) -> list:
    """
    把 PDF 文本分词，保留句子边界信息。
    返回: [(word, sentence_idx), ...]
    """
    abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|Vol|vol|Ch|ch|pp|etc|i\.e|e\.g|a\.m|p\.m|A\.M|P\.M)'
    protected = re.sub(rf'({abbreviations})\.', r'\1<DOT>', text)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'\—])', protected)
    sentences = [s.replace('<DOT>', '.').strip() for s in sentences if s.strip()]
    
    words = []
    for si, sent in enumerate(sentences):
        for w in sent.split():
            words.append((w, si))
    return words, sentences


def extract_whisper_words(whisper_data: dict) -> list:
    """
    从 Whisper 输出提取所有带时间戳的单词。
    过滤掉片头/标题的 segments。
    返回: [(word, start, end), ...]
    """
    skip_prefixes = [
        "harry potter and the philosopher",
        "chapter",
        "the boy who lived",
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


def needleman_wunsch(pdf_words: list, whisper_words: list):
    """
    全局序列对齐（Needleman-Wunsch）。
    返回对齐结果列表: [(pdf_idx, whisper_idx, is_match), ...]
    """
    m, n = len(pdf_words), len(whisper_words)
    
    print(f"Aligning {m} PDF words × {n} Whisper words...")
    
    # DP table (使用滚动数组节省内存)
    prev = [GAP_SCORE * j for j in range(n + 1)]
    curr = [0] * (n + 1)
    
    for i in range(1, m + 1):
        curr[0] = GAP_SCORE * i
        pw = normalize_word(pdf_words[i - 1][0])
        for j in range(1, n + 1):
            ww = normalize_word(whisper_words[j - 1][0])
            score = MATCH_SCORE if pw == ww else MISMATCH_SCORE
            curr[j] = max(
                prev[j - 1] + score,
                prev[j] + GAP_SCORE,
                curr[j - 1] + GAP_SCORE,
            )
        prev, curr = curr, prev
    
    # Backtrack to get alignment
    alignment = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            pw = normalize_word(pdf_words[i - 1][0])
            ww = normalize_word(whisper_words[j - 1][0])
            score = MATCH_SCORE if pw == ww else MISMATCH_SCORE
            if prev[j] == (curr[j - 1] if j > 0 else 0) + score:
                alignment.append((i - 1, j - 1, pw == ww))
                i -= 1
                j -= 1
                continue
        if i > 0 and prev[j] == (prev[j] if False else prev[j]) + GAP_SCORE:
            # 这个判断有问题，让我重新实现
            pass
        
        # 简化：直接用完整的 DP table 回溯
        break
    
    # 由于滚动数组回溯困难，这里用完整 DP table 重新计算
    print("Building full DP table for backtracking...")
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for j in range(1, n + 1):
        dp[0][j] = GAP_SCORE * j
    for i in range(1, m + 1):
        dp[i][0] = GAP_SCORE * i
    
    for i in range(1, m + 1):
        pw = normalize_word(pdf_words[i - 1][0])
        for j in range(1, n + 1):
            ww = normalize_word(whisper_words[j - 1][0])
            score = MATCH_SCORE if pw == ww else MISMATCH_SCORE
            dp[i][j] = max(
                dp[i - 1][j - 1] + score,
                dp[i - 1][j] + GAP_SCORE,
                dp[i][j - 1] + GAP_SCORE,
            )
    
    alignment = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            pw = normalize_word(pdf_words[i - 1][0])
            ww = normalize_word(whisper_words[j - 1][0])
            score = MATCH_SCORE if pw == ww else MISMATCH_SCORE
            if dp[i][j] == dp[i - 1][j - 1] + score:
                alignment.append((i - 1, j - 1, pw == ww))
                i -= 1
                j -= 1
                continue
        if i > 0 and dp[i][j] == dp[i - 1][j] + GAP_SCORE:
            alignment.append((i - 1, None, False))
            i -= 1
        else:
            alignment.append((None, j - 1, False))
            j -= 1
    
    alignment.reverse()
    matches = sum(1 for _, _, is_match in alignment if is_match)
    print(f"Alignment done: {matches} matched words / {len(pdf_words)} PDF words")
    return alignment


def assign_timestamps(pdf_words: list, whisper_words: list, alignment: list) -> list:
    """
    为每个 PDF 单词分配时间戳。
    已匹配的用 Whisper 的时间戳，未匹配的用线性插值。
    返回: [(word, sentence_idx, start, end), ...]
    """
    result = []
    
    for pdf_idx, whisper_idx, is_match in alignment:
        if pdf_idx is None:
            continue  # Whisper-only gap, skip
        
        word, sent_idx = pdf_words[pdf_idx]
        
        if is_match and whisper_idx is not None:
            _, start, end = whisper_words[whisper_idx]
            result.append((word, sent_idx, start, end))
        else:
            # Unmatched PDF word - will interpolate later
            result.append((word, sent_idx, None, None))
    
    # Interpolate missing timestamps
    for i in range(len(result)):
        if result[i][2] is None:
            # Find previous matched word
            prev_start, prev_end = None, None
            for j in range(i - 1, -1, -1):
                if result[j][2] is not None:
                    prev_start, prev_end = result[j][2], result[j][3]
                    break
            
            # Find next matched word
            next_start, next_end = None, None
            for j in range(i + 1, len(result)):
                if result[j][2] is not None:
                    next_start, next_end = result[j][2], result[j][3]
                    break
            
            if prev_start is not None and next_start is not None:
                # Linear interpolation
                gap_words = 1
                for j in range(i + 1, len(result)):
                    if result[j][2] is not None:
                        break
                    gap_words += 1
                
                ratio = 1 / (gap_words + 1)
                start = prev_end + (next_start - prev_end) * ratio
                end = start + (next_start - prev_end) / (gap_words + 1)
                result[i] = (result[i][0], result[i][1], start, end)
            elif prev_start is not None:
                result[i] = (result[i][0], result[i][1], prev_end, prev_end + 0.3)
            elif next_start is not None:
                result[i] = (result[i][0], result[i][1], next_start - 0.3, next_start)
            else:
                result[i] = (result[i][0], result[i][1], 0, 0)
    
    return result


def build_json(pdf_sentences: list, word_data: list) -> dict:
    """按 PDF 句子分组构建最终 JSON"""
    output = {
        "meta": {
            "book": "Harry Potter and the Philosopher's Stone",
            "chapter": 1,
            "title": "The Boy Who Lived",
            "audio_file": "01.The Boy Who Lived.mp3",
            "align_method": "needleman-wunsch global word alignment",
        },
        "sentences": [],
    }
    
    # Group words by sentence
    sentence_words = {}
    for word, sent_idx, start, end in word_data:
        if sent_idx not in sentence_words:
            sentence_words[sent_idx] = []
        sentence_words[sent_idx].append((word, start, end))
    
    for si in sorted(sentence_words.keys()):
        words = sentence_words[si]
        if not words:
            continue
        
        text = pdf_sentences[si]
        start = words[0][1]
        end = words[-1][2]
        
        output["sentences"].append({
            "id": f"c1_s{si + 1:03d}",
            "text": text,
            "start": round(start, 3),
            "end": round(end, 3),
            "words": [
                {"text": w, "start": round(s, 3), "end": round(e, 3)}
                for w, s, e in words
            ],
        })
    
    return output


def main():
    with open(WHISPER_PATH, "r", encoding="utf-8") as f:
        whisper_data = json.load(f)
    
    with open(PDF_PATH, "r", encoding="utf-8") as f:
        pdf_text = f.read()
    
    pdf_words, pdf_sentences = tokenize_pdf(pdf_text)
    whisper_words = extract_whisper_words(whisper_data)
    
    print(f"PDF words: {len(pdf_words)}")
    print(f"PDF sentences: {len(pdf_sentences)}")
    print(f"Whisper words: {len(whisper_words)}")
    
    alignment = needleman_wunsch(pdf_words, whisper_words)
    word_data = assign_timestamps(pdf_words, whisper_words, alignment)
    output = build_json(pdf_sentences, word_data)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved: {OUTPUT_PATH}")
    print(f"   Sentences: {len(output['sentences'])}")
    print(f"   Words: {sum(len(s['words']) for s in output['sentences'])}")
    print(f"   Duration: {output['sentences'][0]['start']:.1f}s ~ {output['sentences'][-1]['end']:.1f}s")


if __name__ == "__main__":
    main()
