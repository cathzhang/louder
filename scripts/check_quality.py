import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

with open(RESOURCE_DIR / "chapter1_aligned.json", "r", encoding="utf-8") as f:
    aligned = json.load(f)

with open(RESOURCE_DIR / "chapter1_text_clean.txt", "r", encoding="utf-8") as f:
    pdf_text = f.read()

# Build PDF sentence set for quick lookup
abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|Vol|vol|Ch|ch|pp|etc|i\.e|e\.g|a\.m|p\.m|A\.M|P\.M)'
protected = re.sub(rf'({abbreviations})\.', r'\1<DOT>', pdf_text)
pdf_sentences = [s.replace('<DOT>', '.').strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z"\'\—])', protected) if s.strip()]
pdf_set = set(s.lower() for s in pdf_sentences)

print("=" * 70)
print(f"对齐句子数: {len(aligned['sentences'])}")
print(f"PDF 原文句子数: {len(pdf_sentences)}")

# Check 1: How many aligned sentences exactly match PDF
exact_matches = 0
close_matches = 0
not_in_pdf = 0
for s in aligned["sentences"]:
    text_lower = s["text"].lower()
    if text_lower in pdf_set:
        exact_matches += 1
    elif any(text_lower in p or p in text_lower for p in pdf_set):
        close_matches += 1
    else:
        not_in_pdf += 1

print(f"完全匹配 PDF: {exact_matches}")
print(f"部分匹配: {close_matches}")
print(f"未匹配: {not_in_pdf}")

# Check 2: First 20 sentences detail
print("\n【前 20 句】")
for s in aligned["sentences"][:20]:
    text_lower = s["text"].lower()
    in_pdf = text_lower in pdf_set
    status = "✅" if in_pdf else "⚠️"
    print(f"  {status} [{s['start']:6.2f}-{s['end']:6.2f}] {s['text'][:90]}")

# Check 3: Last 10 sentences
print("\n【最后 10 句】")
for s in aligned["sentences"][-10:]:
    text_lower = s["text"].lower()
    in_pdf = text_lower in pdf_set
    status = "✅" if in_pdf else "⚠️"
    print(f"  {status} [{s['start']:6.2f}-{s['end']:6.2f}] {s['text'][:90]}")

# Check 4: Time order
print("\n【时间顺序检查】")
out_of_order = 0
for i in range(1, len(aligned["sentences"])):
    prev = aligned["sentences"][i-1]
    curr = aligned["sentences"][i]
    if curr["start"] < prev["start"]:
        out_of_order += 1
        print(f"  乱序: {curr['id']} start={curr['start']:.2f} < prev={prev['start']:.2f}")
print(f"  乱序数: {out_of_order}")

# Check 5: Missing PDF sentences (which PDF sentences are not in aligned)
print("\n【缺失的 PDF 句子】")
aligned_set = set(s["text"].lower() for s in aligned["sentences"])
missing = []
for i, p in enumerate(pdf_sentences):
    if p.lower() not in aligned_set:
        missing.append((i+1, p))

for idx, text in missing[:15]:
    print(f"  PDF #{idx}: {text[:80]}...")
if len(missing) > 15:
    print(f"  ... 还有 {len(missing)-15} 句缺失")
print(f"  共缺失: {len(missing)} 句")

print("=" * 70)
