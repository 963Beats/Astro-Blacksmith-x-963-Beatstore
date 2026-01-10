import logging
from pathlib import Path
from typing import List, Dict, Any
from functools import lru_cache

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

        for genre in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre.is_dir():
                continue

            img_dir = genre / "images"
            image_map: Dict[str, str] = {}

            if img_dir.exists():
                for img in img_dir.iterdir():
                    if img.suffix.lower() in Config.IMAGE_EXTS:
                        image_map[img.stem.lower()] = img.name
            else:
                logger.warning(f"⚠️ Missing images folder: {img_dir}")

            audio_files = sorted(
                [
                    f for f in genre.iterdir()
                    if f.is_file() and f.suffix.lower() in Config.AUDIO_EXTS
                ],
                key=lambda f: f.name.lower(),
            )

            if not audio_files:
                continue

            beats = []
            for audio in audio_files:
                stem = audio.stem.lower()
                image_name = image_map.get(stem)

                # Strong fallback check
                if not image_name and (img_dir / "default.jpg").exists():
                    image_name = "default.jpg"

                beats.append(
                    {
                        "title": audio.stem.replace("_", " ").title(),
                        "file": audio.name,
                        "image": image_name,
                    }
                )

            genres.append(
                {
                    "name": genre.name.replace("-", " ").title(),
                    "folder": genre.name,
                    "beats": beats,
                }
            )

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
        logger.error(f"❌ Audio folder missing: {audio_dir}")
        abort(404)

    response = make_response(
        send_from_directory(
            directory=str(audio_dir),
            path=filename,
        )
    )
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.route("/visuals/<folder>/<filename>")
def visuals(folder: str, filename: str):
    img_dir = (Config.BEATS_ROOT / folder / "images").resolve()

    if not img_dir.exists():
        logger.error(f"❌ Image folder missing: {img_dir}")
        abort(404)

    response = make_response(
        send_from_directory(
            directory=str(img_dir),
            path=filename,
        )
    )
    response.headers["Cache-Control"] = "public, max-age=604800"
    return response


# ---------------- DEBUG (TEMPORARY – SAFE TO REMOVE) ----------------
@app.route("/debug-images/<folder>")
def debug_images(folder: str):
    img_dir = Config.BEATS_ROOT / folder / "images"
    return {
        "exists": img_dir.exists(),
        "resolved_path": str(img_dir.resolve()),
        "files": [f.name for f in img_dir.iterdir()] if img_dir.exists() else [],
    }


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
