import re
from pathlib import Path

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

# Simple sentence splitting for English
# Split on . ! ? followed by space and uppercase (or end of string)
# But protect abbreviations: Mr. Mrs. Ms. Dr. St. Prof. etc.

abbreviations = r'(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|Vol|vol|Ch|ch|pp|etc|i\.e|e\.g|a\.m|p\.m|A\.M|P\.M)'

# Protect abbreviations by temporarily replacing the period
protected = re.sub(rf'({abbreviations})\.', r'\1<DOT>', text)

# Now split on sentence-ending punctuation followed by space+uppercase or end
sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'\—])', protected)

# Restore dots and clean up
sentences = [s.replace('<DOT>', '.').strip() for s in sentences if s.strip()]

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
