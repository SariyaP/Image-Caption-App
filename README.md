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
