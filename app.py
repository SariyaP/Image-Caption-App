import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, url_for
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

try:
    from transformers import BlipForConditionalGeneration, BlipProcessor
except ImportError:  # pragma: no cover - optional until installed
    BlipForConditionalGeneration = None
    BlipProcessor = None


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DATA_FILE = DATA_DIR / "albums.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


load_dotenv(BASE_DIR / ".env")


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

_blip_processor = None
_blip_model = None


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"albums": []}, indent=2), encoding="utf-8")


def load_data() -> dict:
    ensure_storage()
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_slug(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    slug = "-".join(filter(None, cleaned.split("-")))
    return slug or f"album-{uuid4().hex[:8]}"


def get_album(data: dict, album_id: str) -> dict | None:
    return next((album for album in data["albums"] if album["id"] == album_id), None)


def get_image(album: dict, image_id: str) -> dict | None:
    return next((image for image in album["images"] if image["id"] == image_id), None)


def generate_caption(file_path: Path) -> str:
    return generate_caption_locally(file_path)


def load_local_blip():
    global _blip_model, _blip_processor

    if _blip_model is not None and _blip_processor is not None:
        return _blip_processor, _blip_model

    if BlipProcessor is None or BlipForConditionalGeneration is None:
        raise RuntimeError(
            "BLIP captioning requires Pillow, transformers, and torch to be installed."
        )

    _blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    _blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )
    return _blip_processor, _blip_model


def generate_caption_locally(file_path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Local BLIP fallback requires Pillow, transformers, and torch to be installed."
        ) from exc

    processor, model = load_local_blip()
    image = Image.open(file_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    output = model.generate(**inputs, max_new_tokens=40)
    return processor.decode(output[0], skip_special_tokens=True).strip()


@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", albums=data["albums"])


@app.route("/albums", methods=["POST"])
def create_album():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Album name is required.", "error")
        return redirect(url_for("index"))

    data = load_data()
    album_id = create_slug(name)
    existing_ids = {album["id"] for album in data["albums"]}
    if album_id in existing_ids:
        album_id = f"{album_id}-{uuid4().hex[:6]}"

    album = {
        "id": album_id,
        "name": name,
        "description": description,
        "created_at": datetime.utcnow().isoformat(),
        "images": [],
    }
    data["albums"].append(album)
    save_data(data)
    flash("Album created.", "success")
    return redirect(url_for("view_album", album_id=album_id))


@app.route("/albums/<album_id>")
def view_album(album_id: str):
    data = load_data()
    album = get_album(data, album_id)
    if album is None:
        flash("Album not found.", "error")
        return redirect(url_for("index"))
    return render_template("album.html", album=album)


@app.route("/albums/<album_id>/upload", methods=["POST"])
def upload_images(album_id: str):
    data = load_data()
    album = get_album(data, album_id)
    if album is None:
        flash("Album not found.", "error")
        return redirect(url_for("index"))

    files = request.files.getlist("images")
    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        flash("Select at least one image.", "error")
        return redirect(url_for("view_album", album_id=album_id))

    saved_count = 0
    album_upload_dir = UPLOAD_DIR / album_id
    album_upload_dir.mkdir(parents=True, exist_ok=True)

    for file in valid_files:
        if not allowed_file(file.filename):
            continue

        original_name = secure_filename(file.filename)
        extension = original_name.rsplit(".", 1)[1].lower()
        image_id = uuid4().hex
        file_name = f"{image_id}.{extension}"
        destination = album_upload_dir / file_name
        file.save(destination)

        album["images"].append(
            {
                "id": image_id,
                "filename": original_name,
                "file_path": f"uploads/{album_id}/{file_name}",
                "caption": None,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        )
        saved_count += 1

    save_data(data)

    if saved_count == 0:
        flash("No supported image files were uploaded.", "error")
    else:
        flash(f"Uploaded {saved_count} image(s).", "success")
    return redirect(url_for("view_album", album_id=album_id))


@app.route("/albums/<album_id>/images/<image_id>/caption", methods=["POST"])
def caption_image(album_id: str, image_id: str):
    data = load_data()
    album = get_album(data, album_id)
    if album is None:
        flash("Album not found.", "error")
        return redirect(url_for("index"))

    image = get_image(album, image_id)
    if image is None:
        flash("Image not found.", "error")
        return redirect(url_for("view_album", album_id=album_id))

    file_path = BASE_DIR / "static" / image["file_path"]
    try:
        image["caption"] = generate_caption(file_path)
        save_data(data)
        flash("Caption generated.", "success")
    except Exception as exc:
        flash(f"Caption generation failed: {exc}", "error")

    return redirect(url_for("view_album", album_id=album_id))


@app.route("/albums/<album_id>/captions", methods=["POST"])
def caption_album(album_id: str):
    data = load_data()
    album = get_album(data, album_id)
    if album is None:
        flash("Album not found.", "error")
        return redirect(url_for("index"))

    captioned = 0
    failures = 0
    for image in album["images"]:
        if image.get("caption"):
            continue
        file_path = BASE_DIR / "static" / image["file_path"]
        try:
            image["caption"] = generate_caption(file_path)
            captioned += 1
        except Exception:
            failures += 1

    save_data(data)
    if captioned:
        flash(f"Generated {captioned} caption(s).", "success")
    if failures:
        flash(f"{failures} image(s) could not be captioned.", "error")
    return redirect(url_for("view_album", album_id=album_id))


if __name__ == "__main__":
    ensure_storage()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
