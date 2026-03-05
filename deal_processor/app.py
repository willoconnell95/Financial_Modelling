import os
import uuid
import logging
from pathlib import Path
from flask import Flask, request, jsonify, render_template, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from utils.document_parser import extract_text, ALLOWED_EXTENSIONS
from utils.claude_api import generate_deal_summary
from utils.email_sender import send_summary_email

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB total


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_documents():
    """
    Accepts one or more uploaded files, extracts text from each,
    sends the combined content to Claude for summarization, emails
    the result, and returns the HTML summary to the client.
    """
    if "files" not in request.files:
        return jsonify({"error": "No files were uploaded."}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected."}), 400

    # ------------------------------------------------------------------ #
    # 1. Save uploads to a temporary session directory                     #
    # ------------------------------------------------------------------ #
    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_FOLDER / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    rejected_files = []

    for file in files:
        if file.filename == "":
            continue
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            rejected_files.append(file.filename)
            continue
        dest = session_dir / filename
        file.save(str(dest))
        saved_paths.append((filename, dest))

    if not saved_paths:
        _cleanup_dir(session_dir)
        msg = "None of the uploaded files have a supported format."
        if rejected_files:
            msg += f" Unsupported files: {', '.join(rejected_files)}"
        return jsonify({"error": msg}), 400

    # ------------------------------------------------------------------ #
    # 2. Extract text from every saved file                                #
    # ------------------------------------------------------------------ #
    combined_text = ""
    extraction_errors = []

    for filename, path in saved_paths:
        try:
            text = extract_text(str(path), filename)
            if text.strip():
                combined_text += f"\n\n--- Document: {filename} ---\n\n{text}"
            else:
                extraction_errors.append(
                    f"{filename}: extracted successfully but contained no readable text."
                )
        except Exception as exc:
            logger.exception("Extraction failed for %s", filename)
            extraction_errors.append(f"{filename}: {exc}")

    _cleanup_dir(session_dir)

    if not combined_text.strip():
        error_detail = (
            " Details: " + "; ".join(extraction_errors)
            if extraction_errors
            else ""
        )
        return jsonify(
            {"error": f"Could not extract any readable text from the uploaded files.{error_detail}"}
        ), 422

    # ------------------------------------------------------------------ #
    # 3. Send combined text to Claude for structured summarization         #
    # ------------------------------------------------------------------ #
    try:
        html_summary = generate_deal_summary(combined_text)
    except Exception as exc:
        logger.exception("Claude API call failed")
        return jsonify({"error": f"Claude API error: {exc}"}), 502

    # ------------------------------------------------------------------ #
    # 4. Email the summary                                                 #
    # ------------------------------------------------------------------ #
    email_error = None
    try:
        send_summary_email(html_summary)
    except Exception as exc:
        logger.exception("Email delivery failed")
        email_error = str(exc)

    response: dict = {"html_summary": html_summary}

    if extraction_errors:
        response["warnings"] = extraction_errors
    if email_error:
        response["email_error"] = (
            f"Summary generated successfully but email delivery failed: {email_error}"
        )
    else:
        response["email_sent"] = True

    return jsonify(response), 200


def _cleanup_dir(path: Path) -> None:
    """Remove all files in *path* then remove *path* itself."""
    try:
        for child in path.iterdir():
            child.unlink(missing_ok=True)
        path.rmdir()
    except Exception:
        pass  # best-effort cleanup


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
