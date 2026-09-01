import re
from typing import List

# 常见缩写（句点需要保留，不触发分句）
ABBREVIATIONS = (
    r'(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|Vol|vol|Ch|ch|pp|'
    r'etc|i\.e|e\.g|a\.m|p\.m|A\.M|P\.M)'
)

# 句尾标点 + 可选的右引号 + 空白，
# 后面紧跟可选的左引号/破折号 + 大写字母或数字，才视为新一句开始。
# 左引号包括：' " ‘ “ — – - ；右引号包括：' " ’ ”
SENTENCE_BOUNDARY_RE = re.compile(
    r"(?:\.{3,}|…|[.!?])['\"’”]?\s+"
    r"(?=(?:['\"‘“—–-])?[A-Z0-9])"
)


def _protect_abbreviations(text: str) -> str:
    return re.sub(rf'\b({ABBREVIATIONS})\.', r'\1<DOT>', text)


def _restore_abbreviations(text: str) -> str:
    return text.replace('<DOT>', '.')


def split_sentences(text: str) -> List[str]:
    """
    对清洗后的英文文本按句子拆分。

    支持：
    - 普通句尾 . ! ?
    - 省略号 ... / …
    - 弯引号前后导致分句失效的情况
    - 保护常见缩写（Mr. / Mrs. / Dr. / i.e. / a.m. 等）
    """
    protected = _protect_abbreviations(text)

    sentences = []
    start = 0
    for m in SENTENCE_BOUNDARY_RE.finditer(protected):
        sentences.append(protected[start:m.end()].strip())
        start = m.end()

    if start < len(protected):
        sentences.append(protected[start:].strip())

    return [s for s in (_restore_abbreviations(s) for s in sentences) if s]
