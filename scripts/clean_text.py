import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

raw_path = RESOURCE_DIR / "chapter1_text_raw.txt"
clean_path = RESOURCE_DIR / "chapter1_text_clean.txt"

with open(raw_path, "r", encoding="utf-8") as f:
    text = f.read()

# Step 1: Remove page headers/footers
# Patterns: "8 HARRY POTTER", "THE BOY WHO LIVED 9", standalone numbers
text = re.sub(r'^\d+\s+HARRY POTTER\s*$', '', text, flags=re.MULTILINE)
text = re.sub(r'^THE BOY WHO LIVED\s+\d+\s*$', '', text, flags=re.MULTILINE)
text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)

# Step 2: Handle hyphenation at line breaks: word-\nrest -> wordrest
text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

# Step 3: Collapse all single newlines to spaces (these are just line wraps)
# But preserve paragraph breaks (double newlines) temporarily
text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

# Step 4: Now collapse paragraph breaks too - for audiobook alignment,
# paragraph breaks don't matter, we just need continuous text.
text = re.sub(r'\n+', ' ', text)

# Step 5: Clean up multiple spaces
text = re.sub(r' +', ' ', text).strip()

# Remove chapter header
text = re.sub(r'^—\s*CHAPTER\s+ONE\s*—\s*The Boy Who Lived\s*', '', text).strip()

with open(clean_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Cleaned: {len(text)} chars, {len(text.split())} words")
print("Start:", text[:200])
print("End:", text[-200:])
