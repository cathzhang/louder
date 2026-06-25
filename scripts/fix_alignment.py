import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

input_path = RESOURCE_DIR / "chapter1_aligned.json"
output_path = RESOURCE_DIR / "chapter1_aligned.json"

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Sort sentences by start time
data["sentences"].sort(key=lambda s: s["start"])

# 2. Renumber IDs
for i, s in enumerate(data["sentences"], 1):
    s["id"] = f"c1_s{i:03d}"

# 3. Strip leading spaces from words
for s in data["sentences"]:
    for w in s.get("words", []):
        w["text"] = w["text"].strip()

# 4. Deduplicate overlapping words within a sentence (keep first occurrence)
for s in data["sentences"]:
    seen = set()
    unique_words = []
    for w in s.get("words", []):
        key = (w["text"], round(w["start"], 2), round(w["end"], 2))
        if key not in seen:
            seen.add(key)
            unique_words.append(w)
    s["words"] = unique_words

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Fixed: {len(data['sentences'])} sentences")
# Show first and last
print(f"First: [{data['sentences'][0]['start']:.2f}] {data['sentences'][0]['text'][:60]}...")
print(f"Last:  [{data['sentences'][-1]['start']:.2f}] {data['sentences'][-1]['text'][:60]}...")
