from app import app, ensure_storage


if __name__ == "__main__":
    ensure_storage()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
