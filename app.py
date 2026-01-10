import os
import logging
from typing import List, Dict, Any
from flask import Flask, send_from_directory, render_template, abort
from pathlib import Path

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

# ---------------- BEATS SCAN ----------------
class BeatManager:
    @staticmethod
    def get_all_genres() -> List[Dict[str, Any]]:
        genres = []

        if not Config.BEATS_ROOT.exists():
            logger.error("Beats folder missing")
            return genres

        for genre in sorted(d for d in Config.BEATS_ROOT.iterdir() if d.is_dir()):
            img_dir = genre / "images"

            images = (
                [i.name for i in img_dir.iterdir() if i.suffix.lower() in Config.IMAGE_EXTS]
                if img_dir.exists() else []
            )

            audio = [
                f.name for f in genre.iterdir()
                if f.suffix.lower() in Config.AUDIO_EXTS
            ]

            if not audio:
                continue

            beats = []
            for i, file in enumerate(sorted(audio)):
                beats.append({
                    "title": file.rsplit(".", 1)[0].replace("_", " ").title(),
                    "file": file,
                    "image": images[i % len(images)] if images else "default.jpg"
                })

            genres.append({
                "name": genre.name.replace("-", " ").title(),
                "folder": genre.name,
                "beats": beats
            })

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
    return send_from_directory(path, filename)

@app.route("/visuals/<folder>/<filename>")
def visuals(folder, filename):
    path = Config.BEATS_ROOT / folder / "images"
    if not path.exists():
        abort(404)
    return send_from_directory(path, filename)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
