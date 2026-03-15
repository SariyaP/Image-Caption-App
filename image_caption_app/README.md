# Personal Gallery with BLIP Image Captioning

This project is a Flask web application for:

- creating image albums
- uploading multiple images into each album
- generating captions locally with Hugging Face's pretrained `Salesforce/blip-image-captioning-base` model

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: create a `.env` file in the project root if you want to set `FLASK_SECRET_KEY`:

```env
FLASK_SECRET_KEY=your_secret_here
```

4. Run the Flask app:

```bash
python run_server.py
```

5. Open `http://127.0.0.1:5000`.

## Notes

- Uploaded images are stored under `static/uploads/`.
- Album metadata is stored in `data/albums.json`.
- Captions are generated locally with the BLIP model.
- The first caption request will download the BLIP model weights, so it can take longer than later requests.

## Example Output

Example album page output after you create an album and upload a few images:

- Album title: `Pictures`
- Album description: `Collection of random picture I download from internet`
- Multiple uploaded images are shown as gallery cards
- Each card displays the image filename, generated caption, and a `Refresh caption` button
- The album page also includes `Add to album` and `Generate missing captions` actions

This is the kind of interface produced by the application when an album already contains several uploaded images and generated captions.

## Clean Project State

The repository is intended to start clean:

- `data/albums.json` should begin with an empty `albums` list
- `static/uploads/` should only keep `.gitkeep`
- local files such as `.env` and `*.log` are ignored and should not be committed
