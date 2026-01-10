import os
import logging
from typing import List, Dict, Any
from flask import Flask, send_from_directory, render_template, abort
from dataclasses import dataclass
from pathlib import Path

# ---------------- CONFIG ----------------
BASE_DIR = Path(__file__).resolve().parent

class Config:
    BEATS_ROOT = Path(os.environ.get("BEATS_ROOT", BASE_DIR / "beats"))
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-123")
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------- APP ----------------
app = Flask(__name__)
app.config.from_object(Config)

logger.info(f"Beats directory: {Config.BEATS_ROOT.resolve()}")

# ---------------- DATA MODELS ----------------
@dataclass
class Beat:
    title: str
    file: str
    image: str

@dataclass
class Genre:
    name: str
    folder: str
    beats: List[Dict[str, Any]]

# ---------------- MANAGER ----------------
class BeatManager:
    @staticmethod
    def get_all_genres() -> List[Dict[str, Any]]:
        root = Config.BEATS_ROOT
        genres = []

        if not root.exists():
            logger.error("Beats folder not found")
            return []

        for genre_dir in sorted(d for d in root.iterdir() if d.is_dir()):
            img_dir = genre_dir / "images"

            images = (
                [i.name for i in img_dir.iterdir() if i.suffix.lower() in Config.IMAGE_EXTS]
                if img_dir.exists() else []
            )

            audio_files = [
                f.name for f in genre_dir.iterdir()
                if f.suffix.lower() in Config.AUDIO_EXTS
            ]

            if not audio_files:
                continue

            beats = []
            for i, file in enumerate(sorted(audio_files)):
                beats.append({
                    "title": file.rsplit(".", 1)[0].replace("_", " ").title(),
                    "file": file,
                    "image": images[i % len(images)] if images else "default.jpg"
                })

            genres.append({
                "name": genre_dir.name.replace("-", " ").title(),
                "folder": genre_dir.name,
                "beats": beats
            })

        return genres

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", genres=BeatManager.get_all_genres())

@app.route("/audio/<folder>/<filename>")
def stream_audio(folder, filename):
    path = Config.BEATS_ROOT / folder
    if not path.exists():
        abort(404)
    return send_from_directory(path, filename)

@app.route("/visuals/<folder>/<filename>")
def stream_image(folder, filename):
    path = Config.BEATS_ROOT / folder / "images"
    if not path.exists():
        abort(404)
    return send_from_directory(path, filename)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
