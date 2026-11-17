"""Start the Flask app locally:  python run.py   (or: py -3.13 run.py)"""
import os

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print("=" * 60)
    print(" Haymanat Alnajah - Partnerships Showcase (Flask)")
    print(f" Open in your browser:  http://{host}:{port}")
    print(" (This is the Flask app, not a static server on port 5500)")
    print("=" * 60)
    app.run(host=host, port=port, debug=False)
