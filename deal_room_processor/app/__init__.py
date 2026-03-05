"""Flask application factory for the Deal Room Processor."""
import os
from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB total upload limit
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "uploads"
    )
    app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from .routes import main
    app.register_blueprint(main)

    return app
