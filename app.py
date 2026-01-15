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
        """
        Scans the BEATS_ROOT directory for genres and their associated beats.
        Results are cached for performance.
        """
        genres = []
        root = Config.BEATS_ROOT

        if not root.exists():
            print(f"Warning: {root} directory not found.")
            return genres

        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)

        # Iterate through directories in BEATS_ROOT
        for genre_dir in sorted(root.iterdir(), key=lambda d: d.name.lower()):
            if not genre_dir.is_dir():
                continue

            # Look for images in a subfolder named 'images'
            img_dir = genre_dir / "images"
            images = []
            if img_dir.exists() and img_dir.is_dir():
                images = [
                    i.name for i in img_dir.iterdir()
                    if i.suffix.lower() in Config.IMAGE_EXTS
                ]

            # Find all audio files in the genre directory
            audio_files = sorted(
                [
                    f for f in genre_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in Config.AUDIO_EXTS
                ],
                key=lambda f: f.name.lower()
            )

            if not audio_files:
                continue

            # Shuffle images to assign them randomly to beats
            if images:
                random.shuffle(images)

            beats = []
            for idx, audio in enumerate(audio_files):
                try:
                    uploaded_at = datetime.fromtimestamp(audio.stat().st_mtime)
                    is_new = uploaded_at >= today_start
                except Exception:
                    is_new = False

                beats.append({
                    "title": audio.stem.replace("_", " ").title(),
                    "file": audio.name,
                    "image": images[idx % len(images)] if images else Config.DEFAULT_IMAGE,
                    "is_new": is_new,
                })

            # Sort beats: NEW ones first, then alphabetically by title
            beats.sort(key=lambda b: (not b["is_new"], b["title"]))

            genres.append({
                "name": genre_dir.name.replace("-", " ").title(),
                "folder": genre_dir.name,
                "beats": beats,
            })

        return genres


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    """Main page route."""
    genres = BeatManager.get_all_genres()
    return render_template("index.html", genres=genres)

@app.route("/audio/<genre>/<filename>")
def serve_audio(genre, filename):
    """Serves audio files from the genre directory."""
    safe_genre = Path(genre).name  # Basic path traversal protection
    genre_path = Config.BEATS_ROOT / safe_genre
    if not genre_path.exists():
        abort(404)
    return send_from_directory(genre_path, filename)

@app.route("/visuals/<genre>/<filename>")
def serve_visuals(genre, filename):
    """Serves images from the genre/images directory or a default image."""
    if filename == Config.DEFAULT_IMAGE:
        return send_from_directory("static/visuals", Config.DEFAULT_IMAGE)
    
    safe_genre = Path(genre).name
    genre_path = Config.BEATS_ROOT / safe_genre / "images"
    if not genre_path.exists():
        # Fallback to default if genre images dir doesn't exist
        return send_from_directory("static/visuals", Config.DEFAULT_IMAGE)
        
    return send_from_directory(genre_path, filename)


if __name__ == "__main__":
    # Ensure directories exist for local development
    Config.BEATS_ROOT.mkdir(exist_ok=True)
    Path("static/visuals").mkdir(parents=True, exist_ok=True)
    
    app.run(debug=True, port=5000)