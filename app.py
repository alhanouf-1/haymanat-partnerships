"""Vercel entrypoint: exposes a top-level Flask ``app`` (built by the app factory)."""
from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
