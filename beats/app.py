from flask import Flask, send_from_directory, abort, Response
from pathlib import Path
import mimetypes

app = Flask(__name__, static_folder=None)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules"}

# Ensure common audio & image MIME types
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/wav", ".wav")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/png", ".png")


# ─────────────────────────────────────────────
# DIRECTORY LISTING (CRITICAL FOR FRONTEND)
# ─────────────────────────────────────────────
def directory_listing(path: Path, url_path: str) -> Response:
    items = []

    # Parent directory link (REQUIRED)
    if url_path.strip("/") != "":
        items.append('<a href="../">../</a>')

    for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if item.name in SKIP_DIRS:
            continue

        name = item.name + ("/" if item.is_dir() else "")
        items.append(f'<a href="{name}">{name}</a>')

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body>\n" + "<br>\n".join(items) + "\n</body></html>"
    )

    return Response(html, mimetype="text/html")


# ─────────────────────────────────────────────
# ROOT & SUBPATH HANDLER
# ─────────────────────────────────────────────
@app.route("/", defaults={"req_path": ""})
@app.route("/<path:req_path>")
def serve(req_path: str):
    abs_path = (BASE_DIR / req_path).resolve()

    # ── SECURITY: prevent directory traversal
    try:
        abs_path.relative_to(BASE_DIR)
    except ValueError:
        abort(404)

    if not abs_path.exists():
        abort(404)

    # ── FILE
    if abs_path.is_file():
        mime, _ = mimetypes.guess_type(abs_path.name)
        return send_from_directory(
            abs_path.parent,
            abs_path.name,
            mimetype=mime or "application/octet-stream",
            conditional=True
        )

    # ── DIRECTORY (LISTING)
    if abs_path.is_dir():
        return directory_listing(abs_path, "/" + req_path)

    abort(404)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
