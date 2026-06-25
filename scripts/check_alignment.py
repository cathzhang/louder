import json
import re
from pathlib import Path

# Load aligned data
ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

with open(RESOURCE_DIR / "chapter1_aligned.json", "r", encoding="utf-8") as f:
    aligned = json.load(f)

# Load PDF text and split sentences
with open(RESOURCE_DIR / "chapter1_text_clean.txt", "r", encoding="utf-8") as f:
    pdf_text = f.read()

abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|Vol|vol|Ch|ch|pp|etc|i\.e|e\.g|a\.m|p\.m|A\.M|P\.M)'
protected = re.sub(rf'({abbreviations})\.', r'\1<DOT>', pdf_text)
pdf_sentences = [s.replace('<DOT>', '.').strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z"\'\—])', protected) if s.strip()]

# Build aligned sentence map
aligned_ids = {s["id"]: s for s in aligned["sentences"]}
aligned_pdf_indices = set()
for s in aligned["sentences"]:
    # Extract index from id like "c1_s001"
    idx = int(s["id"].split("_s")[1]) - 1
    aligned_pdf_indices.add(idx)

print("=" * 70)
print(f"PDF 总句子数: {len(pdf_sentences)}")
print(f"对齐后句子数: {len(aligned['sentences'])}")
print(f"缺失的 PDF 句子: {len(pdf_sentences) - len(aligned['sentences'])}")
print("=" * 70)

# Check 1: Missing PDF sentences
print("\n【缺失的 PDF 句子】")
missing_count = 0
for i, sent in enumerate(pdf_sentences):
    if i not in aligned_pdf_indices:
        missing_count += 1
        print(f"  PDF #{i+1:3d}: {sent[:80]}...")
print(f"  共 {missing_count} 句缺失")

# Check 2: Time order anomalies
print("\n【时间顺序异常】")
prev_end = -1
for s in aligned["sentences"]:
    if s["start"] < prev_end - 0.5:  # 允许 0.5s 重叠
        print(f"  {s['id']}: start={s['start']:.2f} < prev_end={prev_end:.2f}")
    prev_end = s["end"]

# Check 3: First 20 sentences detail
print("\n【前 20 句对齐详情】")
for s in aligned["sentences"][:20]:
    idx = int(s["id"].split("_s")[1]) - 1
    pdf_text = pdf_sentences[idx] if idx < len(pdf_sentences) else "N/A"
    aligned_text = s["text"]
    # Simple similarity: common words ratio
    pw = set(re.sub(r'[^\w]', '', pdf_text.lower()).split())
    aw = set(re.sub(r'[^\w]', '', aligned_text.lower()).split())
    common = pw & aw
    sim = len(common) / max(len(pw), len(aw), 1) * 100
    status = "OK" if sim > 60 else "⚠️ LOW"
    print(f"  {s['id']} [{s['start']:6.2f}-{s['end']:6.2f}] sim={sim:.0f}% {status}")
    if sim < 60:
        print(f"    PDF:  {pdf_text[:100]}")
        print(f"    ALG:  {aligned_text[:100]}")

# Check 4: Check last few sentences
print("\n【最后 5 句对齐详情】")
for s in aligned["sentences"][-5:]:
    idx = int(s["id"].split("_s")[1]) - 1
    pdf_text = pdf_sentences[idx] if idx < len(pdf_sentences) else "N/A"
    aligned_text = s["text"]
    pw = set(re.sub(r'[^\w]', '', pdf_text.lower()).split())
    aw = set(re.sub(r'[^\w]', '', aligned_text.lower()).split())
    common = pw & aw
    sim = len(common) / max(len(pw), len(aw), 1) * 100
    status = "OK" if sim > 60 else "⚠️ LOW"
    print(f"  {s['id']} [{s['start']:6.2f}-{s['end']:6.2f}] sim={sim:.0f}% {status}")
    if sim < 60:
        print(f"    PDF:  {pdf_text[:100]}")
        print(f"    ALG:  {aligned_text[:100]}")

print("\n" + "=" * 70)
