#!/usr/bin/env python3
"""
用 Whisper 单词时间戳重新对齐新概念英语第二册的单词级时间。

思路：
1. LRC 文件已经给出正确的句子/短语级时间边界。
2. 对每个 lesson 的 MP3 跑 Whisper（base，word_timestamps=True），得到真实单词时间戳。
3. 在每个 LRC 句子的时间窗口内，把 Whisper 识别出的单词序列和 LRC 文本的单词序列做
   Needleman-Wunsch 全局比对，给 LRC 文本里的每个单词分配最可能的 Whisper 时间戳。
4. 未匹配或缺失的单词用线性插值补齐。
5. 输出覆盖 cdn/nce2/lessonXX.json。
"""
import json
import re
import os
from pathlib import Path

import whisper

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"
AUDIO_DIR = RESOURCE_DIR / "新概念英语（第2册）美音（MP3+LRC）"
OUTPUT_DIR = ROOT / "cdn" / "nce2"
WHISPER_CACHE_DIR = RESOURCE_DIR / "nce2_whisper"

os.environ["PATH"] = str(ROOT / "bin") + ":" + os.environ.get("PATH", "")

LRC_TIME_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")

MATCH_SCORE = 2
MISMATCH_SCORE = -1
GAP_SCORE = -1


def normalize_word(w: str) -> str:
    return re.sub(r"[^\w']", "", w.lower())


def parse_lrc(lrc_path: Path):
    """解析 lrc，返回 [{'start','end','text'}, ...]"""
    with open(lrc_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries = []
    for line in lines:
        line = line.strip()
        m = LRC_TIME_RE.match(line)
        if not m:
            continue
        minutes = int(m.group(1))
        seconds = int(m.group(2))
        millis = int(m.group(3).ljust(3, "0")[:3])
        text = m.group(4).strip()
        if not text:
            continue
        start = minutes * 60 + seconds + millis / 1000.0
        entries.append({"start": start, "text": text})

    for i in range(len(entries)):
        if i + 1 < len(entries):
            entries[i]["end"] = entries[i + 1]["start"]
        else:
            entries[i]["end"] = entries[i]["start"] + 3.0

    return entries


def tokenize_text(text: str) -> list:
    """把一句话拆成单词列表，保留原文。"""
    return [w for w in text.split() if w.strip()]


def extract_whisper_words(whisper_data: dict) -> list:
    """从 Whisper 结果中提取 [(word, start, end), ...]"""
    words = []
    for seg in whisper_data.get("segments", []):
        for w in seg.get("words", []):
            words.append((w["word"].strip(), float(w["start"]), float(w["end"])))
    return words


def needleman_wunsch(text_words: list, whisper_words: list) -> list:
    """
    对单句内的单词做全局比对。
    text_words: LRC 文本中的单词（原始文本）
    whisper_words: Whisper 识别出的单词，带时间戳
    返回: [(text_idx, whisper_idx, is_match), ...]
    """
    m, n = len(text_words), len(whisper_words)
    if m == 0 or n == 0:
        return []

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for j in range(1, n + 1):
        dp[0][j] = GAP_SCORE * j
    for i in range(1, m + 1):
        dp[i][0] = GAP_SCORE * i

    for i in range(1, m + 1):
        tw = normalize_word(text_words[i - 1])
        for j in range(1, n + 1):
            ww = normalize_word(whisper_words[j - 1][0])
            score = MATCH_SCORE if tw == ww else MISMATCH_SCORE
            dp[i][j] = max(
                dp[i - 1][j - 1] + score,
                dp[i - 1][j] + GAP_SCORE,
                dp[i][j - 1] + GAP_SCORE,
            )

    alignment = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            tw = normalize_word(text_words[i - 1])
            ww = normalize_word(whisper_words[j - 1][0])
            score = MATCH_SCORE if tw == ww else MISMATCH_SCORE
            if dp[i][j] == dp[i - 1][j - 1] + score:
                alignment.append((i - 1, j - 1, tw == ww))
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
    return alignment


def assign_word_timestamps(text_words: list, whisper_words: list, alignment: list,
                           sent_start: float, sent_end: float) -> list:
    """
    给 LRC 文本中的每个单词分配时间戳。
    已匹配的用 Whisper 时间戳；未匹配的插值；首尾缺失的用句边界。
    """
    n = len(text_words)
    result = [(w, None, None) for w in text_words]

    for ti, wi, is_match in alignment:
        if ti is None:
            continue
        if is_match and wi is not None:
            _, start, end = whisper_words[wi]
            result[ti] = (text_words[ti], start, end)
        # 否则保持 None，交给插值

    # 插值
    for i in range(n):
        if result[i][1] is not None:
            continue

        prev_end = None
        for j in range(i - 1, -1, -1):
            if result[j][2] is not None:
                prev_end = result[j][2]
                break
        if prev_end is None:
            prev_end = sent_start

        next_start = None
        for j in range(i + 1, n):
            if result[j][1] is not None:
                next_start = result[j][1]
                break
        if next_start is None:
            next_start = sent_end

        # 计算当前 gap 区间里有几个连续缺失单词
        gap_count = 1
        for j in range(i + 1, n):
            if result[j][1] is not None:
                break
            gap_count += 1

        total = next_start - prev_end
        step = total / (gap_count + 1)
        for k in range(gap_count):
            idx = i + k
            if idx >= n:
                break
            w = result[idx][0]
            start = prev_end + step * (k + 1)
            end = prev_end + step * (k + 2)
            result[idx] = (w, start, end)

    return [
        {"text": w, "start": round(s, 3), "end": round(e, 3)}
        for w, s, e in result
    ]


def align_lesson(lesson_num: int, lrc_path: Path, whisper_data: dict) -> dict:
    entries = parse_lrc(lrc_path)
    whisper_words = extract_whisper_words(whisper_data)

    sentences = []
    for idx, entry in enumerate(entries):
        sent_start = entry["start"]
        sent_end = entry["end"]
        text = entry["text"]
        text_words = tokenize_text(text)

        # 取出落在本句时间窗口内的 Whisper 单词，稍微外延避免边界漏词
        window_words = [
            w for w in whisper_words
            if w[1] >= sent_start - 0.3 and w[2] <= sent_end + 0.5
        ]

        alignment = needleman_wunsch(text_words, window_words)
        word_data = assign_word_timestamps(
            text_words, window_words, alignment, sent_start, sent_end
        )

        # 句子起止以实际单词为准，兜底用 LRC 边界
        if word_data:
            start = word_data[0]["start"]
            end = word_data[-1]["end"]
        else:
            start, end = sent_start, sent_end

        sentences.append({
            "id": f"s{idx + 1:03d}",
            "text": text,
            "start": round(start, 3),
            "end": round(end, 3),
            "words": word_data,
        })

    mp3_files = list(AUDIO_DIR.glob(f"{lesson_num:02d}－*.mp3"))
    mp3_files = [f for f in mp3_files if "_" not in f.stem]
    audio_file = mp3_files[0].name if mp3_files else f"{lesson_num:02d}.mp3"

    # 标题从现有 JSON 复用
    title = audio_file.replace(".mp3", "").split("－", 1)[-1]
    existing_json = OUTPUT_DIR / f"lesson{lesson_num:02d}.json"
    if existing_json.exists():
        with open(existing_json, "r", encoding="utf-8") as f:
            old = json.load(f)
        title = old.get("meta", {}).get("title", title)

    return {
        "meta": {
            "book": "新概念英语第二册",
            "lesson": lesson_num,
            "title": title,
            "audio_file": audio_file,
            "align_method": "whisper-base + needleman-wunsch per sentence",
        },
        "sentences": sentences,
    }


def load_or_run_whisper(mp3_path: Path, model) -> dict:
    """优先读缓存，否则跑 Whisper 并缓存结果。"""
    WHISPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = WHISPER_CACHE_DIR / f"{mp3_path.stem}.json"

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"  Running Whisper: {mp3_path.name}")
    result = model.transcribe(
        str(mp3_path),
        language="en",
        word_timestamps=True,
        verbose=False,
    )

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WHISPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Whisper base model...")
    model = whisper.load_model("base")

    lrc_files = sorted(AUDIO_DIR.glob("*.lrc"))
    success = 0
    failed = []

    for lrc_path in lrc_files:
        # 从文件名提取 lesson 编号：01－Title.lrc
        m = re.match(r"(\d+)－", lrc_path.name)
        if not m:
            continue
        lesson_num = int(m.group(1))

        mp3_files = list(AUDIO_DIR.glob(f"{lesson_num:02d}－*.mp3"))
        mp3_files = [f for f in mp3_files if "_" not in f.stem]
        if not mp3_files:
            print(f"Lesson {lesson_num:02d}: MP3 not found")
            failed.append(lesson_num)
            continue
        mp3_path = mp3_files[0]

        print(f"Lesson {lesson_num:02d}: {lrc_path.stem}")
        try:
            whisper_data = load_or_run_whisper(mp3_path, model)
            result = align_lesson(lesson_num, lrc_path, whisper_data)

            out_path = OUTPUT_DIR / f"lesson{lesson_num:02d}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"  -> saved ({len(result['sentences'])} sentences)")
            success += 1
        except Exception as e:
            print(f"  -> failed: {e}")
            failed.append(lesson_num)

    print(f"\n完成: {success}/{len(lrc_files)} 课成功")
    if failed:
        print(f"失败: {failed}")


if __name__ == "__main__":
    main()
