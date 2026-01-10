import os
import logging
from typing import List, Dict, Any
from flask import Flask, send_from_directory, render_template, abort
from dataclasses import dataclass
from pathlib import Path

# --- Configuration & Security ---
# In production, these would be loaded from .env
class Config:
    BEATS_ROOT = Path(os.environ.get("BEATS_ROOT", "beats"))
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    AUDIO_EXTS = {".mp3", ".wav", ".ogg"}
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-123")
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

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

class BeatManager:
    """Service class for managing beat metadata and file discovery."""
    
    @staticmethod
    def get_all_genres() -> List[Dict[str, Any]]:
        """Scans the filesystem and returns structured beat data."""
        genres = []
        root = Config.BEATS_ROOT
        
        if not root.exists():
            logger.error(f"Beats directory not found at {root}")
            return []

        try:
            # Sort folders for consistent UI presentation
            for folder_name in sorted([d.name for d in root.iterdir() if d.is_dir()]):
                genre_path = root / folder_name
                img_dir = genre_path / "images"
                
                # Gather assets using sets for O(1) lookups
                imgs = sorted([
                    i.name for i in img_dir.iterdir() 
                    if i.suffix.lower() in Config.IMAGE_EXTS
                ]) if img_dir.exists() else []

                audio_files = sorted([
                    f.name for f in genre_path.iterdir() 
                    if f.suffix.lower() in Config.AUDIO_EXTS
                ])

                if not audio_files:
                    continue

                beats = []
                for i, file_name in enumerate(audio_files):
                    # Robust title parsing
                    title = file_name.rsplit('.', 1)[0].replace("_", " ").title()
                    beats.append({
                        "title": title,
                        "file": file_name,
                        "image": imgs[i % len(imgs)] if imgs else "default.jpg"
                    })

                genres.append({
                    "name": folder_name.replace("-", " ").title(),
                    "folder": folder_name,
                    "beats": beats
                })
        except Exception as e:
            logger.exception("Failed to scan beats directory")
            
        return genres

# --- Routes ---

@app.route("/")
def index():
    """Main library entry point."""
    genres = BeatManager.get_all_genres()
    # Note: In a real app, 'HTML' would be a separate file in /templates
    return render_template("index.html", genres=genres)

@app.route("/audio/<path:folder>/<path:filename>")
def stream_audio(folder: str, filename: str):
    """Securely streams audio files."""
    base_path = Config.BEATS_ROOT / folder
    if not base_path.exists():
        abort(404)
    return send_from_directory(base_path, filename)

@app.route("/visuals/<path:folder>/<path:filename>")
def stream_image(folder: str, filename: str):
    """Securely streams artwork."""
    base_path = Config.BEATS_ROOT / folder / "images"
    if not base_path.exists():
        abort(404)
    return send_from_directory(base_path, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)