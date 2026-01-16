import random
import re
from datetime import datetime, timedelta, timezone
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
    NEW_WINDOW_HOURS = 24


# ---------------- BEAT MANAGER ----------------
class BeatManager:

    @staticmethod
    def get_all_genres() -> List[Dict[str, Any]]:
        genres = []
        root = Config.BEATS_ROOT

        if not root.exists():
            return genres

        now = datetime.now(timezone.utc)
        new_cutoff = now - timedelta(hours=Config.NEW_WINDOW_HOURS)

        for genre_dir in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre_dir.is_dir():
                continue

            # Images
            img_dir = genre_dir / "images"
            images = []
            if img_dir.exists():
                images = [
                    i.name for i in img_dir.iterdir()
                    if i.suffix.lower() in Config.IMAGE_EXTS
                ]
                random.shuffle(images)

            # Audio files (newest first)
            audio_files = sorted(
                [
                    f for f in genre_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in Config.AUDIO_EXTS
                ],
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            if not audio_files:
                continue

            beats = []
            for idx, audio in enumerate(audio_files):
                try:
                    uploaded_at = datetime.fromtimestamp(
                        audio.stat().st_mtime, tz=timezone.utc
                    )
                    is_new = uploaded_at >= new_cutoff
                except Exception:
                    uploaded_at = None
                    is_new = False

                beats.append({
                    "title": audio.stem.replace("_", " ").title(),
                    "file": audio.name,
                    "image": images[idx % len(images)] if images else Config.DEFAULT_IMAGE,
                    "is_new": is_new,
                    "uploaded_at": uploaded_at.timestamp() if uploaded_at else 0,
                    "genre_folder": genre_dir.name,
                })

            # Sort: NEW first → newest → oldest
            beats.sort(key=lambda b: (not b["is_new"], -b["uploaded_at"]))

            genres.append({
                "name": genre_dir.name.replace("-", " ").title(),
                "folder": genre_dir.name,
                "beats": beats,
            })

        return genres


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", genres=BeatManager.get_all_genres())


@app.route("/beat/<genre>/<slug>")
def beat_page(genre, slug):
    genres = BeatManager.get_all_genres()

    for g in genres:
        if g["folder"] == genre:
            for b in g["beats"]:
                beat_slug = re.sub(r"\s+", "-", b["title"].lower())
                if beat_slug == slug:
                    return render_template(
                        "index.html",
                        genres=genres,
                        og_beat=b,
                        og_genre=g
                    )
    abort(404)


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
