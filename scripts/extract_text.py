import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

pdf_path = RESOURCE_DIR / "1.英文电子书-Harry Potter and the Philosopher's Stone.pdf"
output_path = RESOURCE_DIR / "chapter1_text_raw.txt"

with pdfplumber.open(str(pdf_path)) as pdf:
    # Extract pages 11-22 (0-indexed: 10-21)
    pages = pdf.pages[10:22]
    full_text = "\n".join(p.extract_text() or "" for p in pages)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"Extracted {len(full_text)} chars to {output_path}")
print("--- Preview (first 1000 chars) ---")
print(full_text[:1000])
