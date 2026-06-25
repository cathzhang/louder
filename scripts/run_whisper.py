#!/usr/bin/env python3
"""调用 whisper 转录音频"""
import json
import os
from pathlib import Path

import whisper

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resource"

# 确保 ffmpeg 在 PATH
os.environ["PATH"] = str(ROOT / "bin") + ":" + os.environ.get("PATH", "")

audio_path = RESOURCE_DIR / "01.The Boy Who Lived.mp3"
output_path = RESOURCE_DIR / "01.The Boy Who Lived.json"

print("Loading whisper base model...")
model = whisper.load_model("base")

print(f"Transcribing: {audio_path}")
result = model.transcribe(
    str(audio_path),
    language="en",
    word_timestamps=True,
    verbose=True,
)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\nDone! Output saved to: {output_path}")
print(f"Segments: {len(result['segments'])}")
