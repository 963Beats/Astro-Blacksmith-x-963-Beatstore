import os
import random
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any

from flask import Flask, render_template, send_from_directory, abort

app = Flask(__name__)

# ---------------- CONFIG ----------------
class Config:
    BEATS_ROOT = Path("beats")
    AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    DEFAULT_IMAGE = "default.jpg"


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
        today_end = today_start.replace(hour=23, minute=59, second=59)

        for genre_dir in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre_dir.is_dir():
                continue

            img_dir = genre_dir / "images"
            images = []
            if img_dir.exists():
                images = [
                    i.name for i in img_dir.iterdir()
                    if i.suffix.lower() in Config.IMAGE_EXTS
                ]

            audio_files = sorted(
                [
                    f for f in genre_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in Config.AUDIO_EXTS
                ],
                key=lambda f: f.name.lower()
            )

            if not audio_files:
                continue

            if images:
                random.shuffle(images)

            beats = []
            for idx, audio in enumerate(audio_files):
                try:
                    ts = audio.stat().st_ctime or audio.stat().st_mtime
                    uploaded_at = datetime.fromtimestamp(ts)
                    is_new = today_start <= uploaded_at <= today_end
                except Exception:
                    is_new = False

                beats.append({
                    "title": audio.stem.replace("_", " ").title(),
                    "file": audio.name,
                    "image": images[idx % len(images)] if images else Config.DEFAULT_IMAGE,
                    "is_new": is_new,
                    "genre_folder": genre_dir.name,
                })

            beats.sort(key=lambda b: (not b["is_new"], b["title"]))

            genres.append({
                "name": genre_dir.name.replace("-", " ").title(),
                "folder": genre_dir.name,
                "beats": beats,
            })

        return genres


# ---------------- ROUTES ----------------
@app.route("/beat/<genre>/<slug>")
def beat_page(genre, slug):
    genres = BeatManager.get_all_genres()

    for g in genres:
        if g["folder"] == genre:
            for b in g["beats"]:
                if b["title"].lower().replace(" ", "-") == slug:
                    return render_template(
                        "index.html",
                        genres=genres,
                        og_beat=b,
                        og_genre=g
                    )

    abort(404)
    
@app.route("/")
def index():
    return render_template("index.html", genres=BeatManager.get_all_genres())


@app.route("/audio/<genre>/<filename>")
def serve_audio(genre, filename):
    safe = Path(genre).name
    path = Config.BEATS_ROOT / safe
    if not path.exists():
        abort(404)
    return send_from_directory(path, filename)


@app.route("/visuals/<genre>/<filename>")
def serve_visuals(genre, filename):
    if filename == Config.DEFAULT_IMAGE:
        return send_from_directory("static/visuals", filename)

    safe = Path(genre).name
    path = Config.BEATS_ROOT / safe / "images"
    if not path.exists():
        return send_from_directory("static/visuals", Config.DEFAULT_IMAGE)

    return send_from_directory(path, filename)


if __name__ == "__main__":
    Config.BEATS_ROOT.mkdir(exist_ok=True)
    Path("static/visuals").mkdir(parents=True, exist_ok=True)
    app.run(debug=True, port=5000)
