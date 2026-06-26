#!/usr/bin/env python3
"""
处理新概念英语第二册：
1. 从 PDF 提取每课正文（用于顺序校验）
2. 解析 lrc 文件获取句子/短语级时间戳
3. 把 lrc 行与 PDF 正文对齐，校验顺序
4. 生成单词级时间戳
5. 输出每个 lesson 的 JSON 文件

对齐策略：
- 以 lrc 行的文本作为句子/短语正文（lrc 文本与音频完全对应）
- PDF 正文仅用于校验 lrc 行的顺序是否一致
- 单词时间戳按 lrc 行内单词数等分
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"
PDF_PATH = RESOURCE_DIR / "新概念英语第二册 (亚历山大  何其莘) (Z-Library).pdf"
AUDIO_DIR = RESOURCE_DIR / "新概念英语（第2册）美音（MP3+LRC）"
OUTPUT_DIR = ROOT / "cdn" / "nce2"

LRC_TIME_RE = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)')


def extract_pdf_text():
    """提取 PDF 全部文本"""
    import fitz
    doc = fitz.open(str(PDF_PATH))
    full_text = "\n".join(page.get_text() for page in doc)
    return full_text


def find_body_start(full_text):
    """找到正文开始位置（跳过目录）"""
    first_listen_idx = full_text.find('First listen and then answer the question.')
    if first_listen_idx == -1:
        first_listen_idx = full_text.find('听录音，然后回答以下问题。')
    if first_listen_idx == -1:
        raise ValueError("无法找到课文开始位置")
    body_start = full_text.rfind('Lesson 1', 0, first_listen_idx)
    if body_start == -1:
        body_start = 0
    return body_start


def split_into_lessons(full_text):
    """按 Lesson N 分割成 96 课，跳过目录"""
    body_start = find_body_start(full_text)
    body_text = full_text[body_start:]

    pattern = re.compile(r'Lesson\s+(\d+)\s+([^\n]+)', re.IGNORECASE)
    matches = list(pattern.finditer(body_text))

    lessons = []
    seen = set()
    for i, m in enumerate(matches):
        lesson_num = int(m.group(1))
        title = m.group(2).strip()
        if lesson_num < 1 or lesson_num > 96:
            continue
        if lesson_num in seen:
            continue
        seen.add(lesson_num)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_text)
        lessons.append({
            'num': lesson_num,
            'title': title,
            'text': body_text[start:end]
        })

    return sorted(lessons, key=lambda x: x['num'])


def extract_body(lesson_text):
    """
    从一课文本中提取正文：
    从"听录音，然后回答以下问题。"之后开始，到"New words and expressions"之前结束
    """
    start_marker = "听录音，然后回答以下问题。"
    start_idx = lesson_text.find(start_marker)
    if start_idx == -1:
        return None
    start_idx += len(start_marker)

    q_end = lesson_text.find('?', start_idx)
    if q_end != -1:
        nl = lesson_text.find('\n', q_end)
        if nl != -1:
            start_idx = nl + 1
        else:
            start_idx = q_end + 1

    end_marker = "New words and expressions"
    end_idx = lesson_text.find(end_marker, start_idx)
    if end_idx == -1:
        end_idx = len(lesson_text)

    body = lesson_text[start_idx:end_idx].strip()
    return body


def clean_pdf_body(body):
    """
    清洗 PDF 正文，返回单词列表（仅用于对齐校验）
    """
    lines = body.split('\n')
    paragraphs = []
    current = []

    for line in lines:
        line = line.strip()
        if not line:
            if current:
                paragraphs.append(' '.join(current))
                current = []
            continue

        if re.match(r'^[\u4e00-\u9fff\s，。！？、：""''（）]+$', line):
            continue
        if re.match(r'^\[[^\]]+\]$', line):
            continue
        if '参考译文' in line:
            break

        if line.endswith('-') or line.endswith('—'):
            current.append(line[:-1])
        else:
            current.append(line)

    if current:
        paragraphs.append(' '.join(current))

    full_text = ' '.join(paragraphs)
    full_text = re.sub(r'[\u4e00-\u9fff]+', '', full_text)
    full_text = re.sub(r'\[[^\]]+\]', '', full_text)
    full_text = re.sub(r'\s+', ' ', full_text).strip()

    words = [normalize_word(m.group()) for m in re.finditer(r"\S+", full_text)]
    return words


def normalize_word(w):
    return re.sub(r"[^\w']", '', w.lower())


def parse_lrc(lrc_path):
    """解析 lrc 文件，返回 [{'start', 'end', 'text'}, ...]"""
    with open(lrc_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    for line in lines:
        line = line.strip()
        m = LRC_TIME_RE.match(line)
        if not m:
            continue
        minutes = int(m.group(1))
        seconds = int(m.group(2))
        millis = int(m.group(3).ljust(3, '0')[:3])
        text = m.group(4).strip()
        if not text:
            continue
        start = minutes * 60 + seconds + millis / 1000.0
        entries.append({'start': start, 'text': text})

    for i in range(len(entries)):
        if i + 1 < len(entries):
            entries[i]['end'] = entries[i + 1]['start']
        else:
            entries[i]['end'] = entries[i]['start'] + 3.0

    return entries


def align_lrc_to_pdf(lrc_entries, pdf_words):
    """
    把 lrc 行按顺序与 PDF 正文对齐校验。
    返回 [{'start', 'end', 'text', 'words'}, ...]，text 使用 lrc 原文。
    """
    aligned = []
    pdf_pos = 0

    for entry in lrc_entries:
        lrc_text = entry['text']
        lrc_norms = [normalize_word(w) for w in lrc_text.split() if normalize_word(w)]

        if not lrc_norms:
            continue

        best_start = -1
        best_score = 0
        best_len = 0

        # 扩大搜索范围，避免长句被截断
        search_end = min(len(pdf_words), pdf_pos + max(60, len(lrc_norms) * 3))

        for i in range(pdf_pos, search_end):
            match_count = 0
            j = 0
            k = i
            while j < len(lrc_norms) and k < len(pdf_words):
                if lrc_norms[j] == pdf_words[k]:
                    match_count += 1
                    j += 1
                k += 1

            score = match_count / len(lrc_norms)
            if score > best_score or (score == best_score and match_count > best_len):
                best_score = score
                best_start = i
                best_len = match_count
            if score == 1.0:
                break

        if best_start == -1 or best_score < 0.3:
            # 对齐失败，仍然使用 lrc 文本，但位置不前移
            pass
        else:
            # 跳到匹配位置之后
            matched_len = 0
            j = 0
            k = best_start
            while j < len(lrc_norms) and k < len(pdf_words):
                if lrc_norms[j] == pdf_words[k]:
                    matched_len += 1
                    j += 1
                k += 1
            pdf_pos = best_start + max(matched_len, 1)

        # 使用 lrc 原文作为句子文本
        words = split_into_words(lrc_text, entry['start'], entry['end'])
        aligned.append({
            'id': f's{len(aligned)+1:03d}',
            'text': lrc_text,
            'start': round(entry['start'], 3),
            'end': round(entry['end'], 3),
            'words': words,
            'align_score': round(best_score, 2)
        })

    return aligned


def split_into_words(sentence_text, start, end):
    """把句子拆分成单词，并按单词数等分时间"""
    words_raw = sentence_text.split()
    if not words_raw:
        return []

    duration = end - start
    word_duration = duration / len(words_raw)

    result = []
    for i, w in enumerate(words_raw):
        w_start = start + i * word_duration
        w_end = start + (i + 1) * word_duration
        result.append({
            'text': w,
            'start': round(w_start, 3),
            'end': round(w_end, 3)
        })

    return result


def process_lesson(lesson, lrc_path):
    """处理单个 lesson，生成对齐 JSON"""
    body = extract_body(lesson['text'])
    if not body:
        print(f"Lesson {lesson['num']}: 无法提取正文")
        return None

    pdf_words = clean_pdf_body(body)
    if not pdf_words:
        print(f"Lesson {lesson['num']}: 清洗后无正文")
        return None

    if not lrc_path.exists():
        print(f"Lesson {lesson['num']}: 缺少 lrc 文件 {lrc_path}")
        return None

    lrc_entries = parse_lrc(lrc_path)
    aligned = align_lrc_to_pdf(lrc_entries, pdf_words)

    if not aligned:
        print(f"Lesson {lesson['num']}: 对齐失败")
        return None

    # 移除对齐分数字段，不输出到 JSON
    for item in aligned:
        item.pop('align_score', None)

    mp3_files = list(AUDIO_DIR.glob(f'{lesson["num"]:02d}－*.mp3'))
    mp3_files = [f for f in mp3_files if '_' not in f.stem]
    audio_file = mp3_files[0].name if mp3_files else f'{lesson["num"]:02d}.mp3'

    result = {
        'meta': {
            'book': '新概念英语第二册',
            'lesson': lesson['num'],
            'title': lesson['title'],
            'audio_file': audio_file
        },
        'sentences': aligned
    }

    return result


def find_lrc_path(lesson_num):
    """根据 lesson 编号找 lrc 文件"""
    pattern = f'{lesson_num:02d}－*.lrc'
    files = list(AUDIO_DIR.glob(pattern))
    if not files:
        return None
    return files[0]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("提取 PDF 文本...")
    full_text = extract_pdf_text()

    print("分割课程...")
    lessons = split_into_lessons(full_text)
    print(f"找到 {len(lessons)} 课")

    success = 0
    failed = []

    for lesson in lessons:
        lrc_path = find_lrc_path(lesson['num'])
        if not lrc_path:
            print(f"Lesson {lesson['num']}: 找不到 lrc 文件")
            failed.append(lesson['num'])
            continue

        result = process_lesson(lesson, lrc_path)
        if not result:
            failed.append(lesson['num'])
            continue

        out_path = OUTPUT_DIR / f'lesson{lesson["num"]:02d}.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        success += 1
        print(f"Lesson {lesson['num']:02d}: 已保存 ({len(result['sentences'])} 句)")

    # 生成 manifest.json
    manifest = []
    for lesson in lessons:
        out_path = OUTPUT_DIR / f'lesson{lesson["num"]:02d}.json'
        if out_path.exists():
            with open(out_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            manifest.append({
                'lesson': data['meta']['lesson'],
                'title': data['meta']['title'],
                'json_file': out_path.name,
                'audio_file': data['meta']['audio_file']
            })

    with open(OUTPUT_DIR / 'manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n完成: {success}/{len(lessons)} 课成功")
    if failed:
        print(f"失败: {failed}")


if __name__ == '__main__':
    main()
