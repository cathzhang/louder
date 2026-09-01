import re
from pathlib import Path
from sentence_utils import split_sentences

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

text_path = RESOURCE_DIR / "chapter1_text_clean.txt"
output_path = RESOURCE_DIR / "chapter1_sentences.txt"

with open(text_path, "r", encoding="utf-8") as f:
    text = f.read()

# Remove chapter title line
text = re.sub(r'^—\s*CHAPTER\s+ONE\s*—\s*', '', text, flags=re.MULTILINE)
text = re.sub(r'^The Boy Who Lived\s*', '', text, flags=re.MULTILINE)
text = text.strip()

sentences = split_sentences(text)

print(f"Total sentences: {len(sentences)}")
for i, s in enumerate(sentences[:5], 1):
    print(f"\n--- Sentence {i} ---")
    print(s[:200])

print(f"\n... ({len(sentences)-10} sentences omitted) ...\n")

for i, s in enumerate(sentences[-5:], len(sentences)-4):
    print(f"\n--- Sentence {i} ---")
    print(s[:200])

# Save
with open(output_path, "w", encoding="utf-8") as f:
    for i, s in enumerate(sentences, 1):
        f.write(f"{i}\t{s}\n")

print(f"\nSaved to {output_path}")
