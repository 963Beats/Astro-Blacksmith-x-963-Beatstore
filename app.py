import os
import random
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any

from flask import Flask, render_template

app = Flask(__name__)

# ---------------- CONFIG ----------------
class Config:
    BEATS_ROOT = Path("beats")
    AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------- BEAT MANAGER ----------------
class BeatManager:

    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_genres() -> List[Dict[str, Any]]:
        genres = []
        root = Config.BEATS_ROOT

        if not root.exists():
            return genres

        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)

        for genre in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre.is_dir():
                continue

            img_dir = genre / "images"
            images = []
            if img_dir.exists():
                images = [
                    i.name for i in img_dir.iterdir()
                    if i.suffix.lower() in Config.IMAGE_EXTS
                ]

            audio_files = sorted(
                [
                    f for f in genre.iterdir()
                    if f.is_file() and f.suffix.lower() in Config.AUDIO_EXTS
                ],
                key=lambda f: f.name.lower()
            )

            if not audio_files:
                continue

            random.shuffle(images)

            beats = []
            for idx, audio in enumerate(audio_files):
                uploaded_at = datetime.fromtimestamp(audio.stat().st_mtime)
                is_new = uploaded_at >= today_start

                beats.append({
                    "title": audio.stem.replace("_", " ").title(),
                    "file": audio.name,
                    "image": images[idx % len(images)] if images else "default.jpg",
                    "is_new": is_new,
                })

            # NEW beats first
            beats.sort(key=lambda b: b["is_new"], reverse=True)

            genres.append({
                "name": genre.name.replace("-", " ").title(),
                "folder": genre.name,
                "beats": beats,
            })

        return genres


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    genres = BeatManager.get_all_genres()
    return render_template("index.html", genres=genres)


if __name__ == "__main__":
    app.run(debug=True)
