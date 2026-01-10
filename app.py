import os
import logging
from typing import List, Dict, Any
from flask import Flask, send_from_directory, render_template, abort, make_response
from pathlib import Path
from functools import lru_cache

# ---------------- BASE DIR ----------------
BASE_DIR = Path(__file__).resolve().parent

# ---------------- CONFIG ----------------
class Config:
    BEATS_ROOT = BASE_DIR / "beats"
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
    DEBUG = True

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- APP ----------------
app = Flask(__name__)
app.config.from_object(Config)

logger.info(f"Beats path: {Config.BEATS_ROOT.resolve()}")

# ---------------- BEATS SCAN (CACHED) ----------------
class BeatManager:

    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_genres() -> List[Dict[str, Any]]:
        genres = []

        root = Config.BEATS_ROOT
        if not root.exists():
            logger.error("Beats folder missing")
            return genres

        for genre in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre.is_dir():
                continue

            img_dir = genre / "images"

            images = {
                i.stem.lower(): i.name
                for i in img_dir.iterdir()
                if i.suffix.lower() in Config.IMAGE_EXTS
            } if img_dir.exists() else {}

            audio_files = sorted(
                [f for f in genre.iterdir() if f.suffix.lower() in Config.AUDIO_EXTS],
                key=lambda f: f.name.lower()
            )

            if not audio_files:
                continue

            beats = []
            for f in audio_files:
                stem = f.stem.lower()
                beats.append({
                    "title": f.stem.replace("_", " ").title(),
                    "file": f.name,
                    "image": images.get(stem, "default.jpg")
                })

            genres.append({
                "name": genre.name.replace("-", " ").title(),
                "folder": genre.name,
                "beats": beats
            })

        logger.info(f"Loaded {len(genres)} genres")
        return genres

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", genres=BeatManager.get_all_genres())

@app.route("/audio/<folder>/<filename>")
def audio(folder, filename):
    path = Config.BEATS_ROOT / folder
    if not path.exists():
        abort(404)

    response = make_response(send_from_directory(path, filename))
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

@app.route("/visuals/<folder>/<filename>")
def visuals(folder, filename):
    path = Config.BEATS_ROOT / folder / "images"
    if not path.exists():
        abort(404)

    response = make_response(send_from_directory(path, filename))
    response.headers["Cache-Control"] = "public, max-age=604800"
    return response

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
