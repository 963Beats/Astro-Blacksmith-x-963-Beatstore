import logging
import random
from pathlib import Path
from typing import List, Dict, Any
from functools import lru_cache
from datetime import datetime, timezone, timedelta

from flask import (
    Flask,
    send_from_directory,
    render_template,
    abort,
    make_response,
)

# ---------------- BASE DIR ----------------
BASE_DIR = Path(__file__).resolve().parent

# ---------------- CONFIG ----------------
class Config:
    BEATS_ROOT = BASE_DIR / "beats"
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
    DEBUG = False

    # 🔥 Beats uploaded within last X days are marked NEW
    NEW_UPLOAD_DAYS = 7


# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------- APP ----------------
app = Flask(__name__)
app.config.from_object(Config)

logger.info(f"BEATS_ROOT resolved to: {Config.BEATS_ROOT.resolve()}")


# ---------------- BEAT MANAGER ----------------
class BeatManager:

    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_genres() -> List[Dict[str, Any]]:
        genres: List[Dict[str, Any]] = []
        root = Config.BEATS_ROOT

        if not root.exists():
            logger.error("❌ beats/ directory does not exist")
            return genres

        now = datetime.now(timezone.utc)
        new_cutoff = now - timedelta(days=Config.NEW_UPLOAD_DAYS)

        for genre in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre.is_dir():
                continue

            img_dir = genre / "images"
            images: List[str] = []

            if img_dir.exists():
                images = [
                    i.name for i in img_dir.iterdir()
                    if i.suffix.lower() in Config.IMAGE_EXTS
                ]

            audio_files = sorted(
                [f for f in genre.iterdir() if f.is_file() and f.suffix.lower() in Config.AUDIO_EXTS],
                key=lambda f: f.name.lower(),
            )

            if not audio_files:
                continue

            random.shuffle(images)

            beats = []
            for idx, audio in enumerate(audio_files):
                uploaded_at = datetime.fromtimestamp(
                    audio.stat().st_mtime, tz=timezone.utc
                )

                is_new = uploaded_at >= new_cutoff

                image_name = images[idx % len(images)] if images else "default.jpg"

                beats.append({
                    "title": audio.stem.replace("_", " ").title(),
                    "file": audio.name,
                    "image": image_name,
                    "is_new": is_new,
                    "uploaded_at": uploaded_at.isoformat(),
                })

            # 🔥 Sort new beats to the top
            beats.sort(key=lambda b: b["is_new"], reverse=True)

            genres.append({
                "name": genre.name.replace("-", " ").title(),
                "folder": genre.name,
                "beats": beats,
            })

        logger.info(f"✅ Loaded {len(genres)} genres")
        return genres


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        genres=BeatManager.get_all_genres(),
    )


@app.route("/audio/<folder>/<filename>")
def audio(folder: str, filename: str):
    audio_dir = (Config.BEATS_ROOT / folder).resolve()
    if not audio_dir.exists():
        abort(404)

    response = make_response(
        send_from_directory(str(audio_dir), filename)
    )
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.route("/visuals/<folder>/<filename>")
def visuals(folder: str, filename: str):
    img_dir = (Config.BEATS_ROOT / folder / "images").resolve()
    if not img_dir.exists():
        abort(404)

    response = make_response(
        send_from_directory(str(img_dir), filename)
    )
    response.headers["Cache-Control"] = "public, max-age=604800"
    return response


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
