import re

with open("/Users/cathy/Documents/workspace/louder/resource/chapter1_text_raw.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Step 1: Remove page headers/footers
# Patterns like "8 HARRY POTTER", "THE BOY WHO LIVED 9"
# These are lines that contain only page number + book/chapter title
text = re.sub(r'^\d+\s+HARRY POTTER\s*$', '', text, flags=re.MULTILINE)
text = re.sub(r'^THE BOY WHO LIVED\s+\d+\s*$', '', text, flags=re.MULTILINE)

# Step 2: Remove standalone page numbers that might appear
text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)

# Step 3: Handle hyphenation at line breaks (word split across pages)
# Pattern: word-part\nrest-of-word -> word-partrest-of-word
# But we need to be careful: only remove hyphen when it's a real word break
# Examples: "hap-\npening" -> "happening", "night-\ntime" -> "nighttime"
text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

# Step 4: Replace remaining line breaks with spaces (since PDF text has hard wraps)
# But preserve paragraph breaks (double newlines)
text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

# Step 5: Clean up multiple spaces and blank lines
text = re.sub(r' +', ' ', text)
text = re.sub(r'\n\n+', '\n\n', text)
text = text.strip()

# Step 6: Normalize some common PDF artifacts
text = text.replace(' ' * 2, ' ')

with open("/Users/cathy/Documents/workspace/louder/resource/chapter1_text_clean.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(f"Cleaned text: {len(text)} chars")
print("="*60)
print(text[:1500])
print("="*60)
print(f"\n... ({len(text) - 3000} chars omitted) ...\n")
print(text[-1500:])
