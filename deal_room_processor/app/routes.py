"""
Flask route handlers for the Deal Room Processor.

Flow:
  GET  /           → upload page
  POST /process    → extract text → Claude summary → send email → results page
  GET  /health     → JSON health check
"""
import os
import uuid
from pathlib import Path
from typing import List

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .claude_client import ClaudeAPIError, summarize_documents
from .document_processor import SUPPORTED_EXTENSIONS, extract_all
from .email_sender import EmailSendError, send_summary

main = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = set(SUPPORTED_EXTENSIONS.keys())
MAX_FILES = 20


def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _save_uploads(files) -> List[str]:
    """Save uploaded FileStorage objects and return their paths."""
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    # Use a per-request subdirectory to avoid filename collisions
    session_dir = os.path.join(upload_dir, str(uuid.uuid4()))
    os.makedirs(session_dir, exist_ok=True)

    saved_paths = []
    for file in files:
        if file and file.filename and _allowed_file(file.filename):
            # Sanitize the filename
            safe_name = Path(file.filename).name
            dest = os.path.join(session_dir, safe_name)
            file.save(dest)
            saved_paths.append(dest)
    return saved_paths


def _cleanup(paths: List[str]) -> None:
    """Remove temporary files and their parent session directory."""
    if not paths:
        return
    session_dir = os.path.dirname(paths[0])
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.rmdir(session_dir)
    except OSError:
        pass


@main.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        supported_extensions=sorted(ALLOWED_EXTENSIONS),
        max_files=MAX_FILES,
    )


@main.route("/process", methods=["POST"])
def process():
    # ── 1. Validate uploaded files ────────────────────────────────────────────
    uploaded_files = request.files.getlist("documents")
    if not uploaded_files or all(not f.filename for f in uploaded_files):
        return render_template(
            "index.html",
            error="No files were uploaded. Please select at least one document.",
            supported_extensions=sorted(ALLOWED_EXTENSIONS),
            max_files=MAX_FILES,
        )

    # Filter to allowed types only
    valid_files = [f for f in uploaded_files if f.filename and _allowed_file(f.filename)]
    invalid_files = [
        f.filename
        for f in uploaded_files
        if f.filename and not _allowed_file(f.filename)
    ]

    if len(valid_files) > MAX_FILES:
        return render_template(
            "index.html",
            error=f"Too many files. Maximum is {MAX_FILES} per submission.",
            supported_extensions=sorted(ALLOWED_EXTENSIONS),
            max_files=MAX_FILES,
        )

    if not valid_files:
        ext_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return render_template(
            "index.html",
            error=f"None of the uploaded files are supported. Allowed types: {ext_list}",
            supported_extensions=sorted(ALLOWED_EXTENSIONS),
            max_files=MAX_FILES,
        )

    # ── 2. Save files to disk ─────────────────────────────────────────────────
    saved_paths: List[str] = []
    try:
        saved_paths = _save_uploads(valid_files)
        if not saved_paths:
            return render_template(
                "index.html",
                error="Files could not be saved. Please try again.",
                supported_extensions=sorted(ALLOWED_EXTENSIONS),
                max_files=MAX_FILES,
            )

        # ── 3. Extract text ───────────────────────────────────────────────────
        extraction = extract_all(saved_paths)
        extraction_results = extraction["results"]
        combined_text = extraction["combined_text"]

        # Partition into successes and failures for display
        successes = [r for r in extraction_results if r["error"] is None]
        failures = [r for r in extraction_results if r["error"] is not None]

        if not combined_text.strip():
            error_details = "; ".join(
                f"{r['filename']}: {r['error']}" for r in failures
            )
            return render_template(
                "index.html",
                error=(
                    "No text could be extracted from any of the uploaded files. "
                    + (f"Details: {error_details}" if error_details else "")
                ),
                supported_extensions=sorted(ALLOWED_EXTENSIONS),
                max_files=MAX_FILES,
            )

        # ── 4. Generate summary with Claude ──────────────────────────────────
        try:
            summary_html = summarize_documents(combined_text)
        except (ClaudeAPIError, ValueError) as exc:
            return render_template(
                "index.html",
                error=f"Claude API error: {exc}",
                supported_extensions=sorted(ALLOWED_EXTENSIONS),
                max_files=MAX_FILES,
            )

        # ── 5. Send email ─────────────────────────────────────────────────────
        filenames = [os.path.basename(p) for p in saved_paths]
        email_error: str = ""
        email_sent: bool = False
        recipient = os.environ.get("EMAIL_RECIPIENT", "will@athletic.vc")

        try:
            send_summary(
                summary_html=summary_html,
                filenames=filenames,
            )
            email_sent = True
        except EmailSendError as exc:
            email_error = str(exc)

        # ── 6. Render results page ────────────────────────────────────────────
        return render_template(
            "result.html",
            summary_html=summary_html,
            filenames=filenames,
            invalid_files=invalid_files,
            extraction_failures=failures,
            email_sent=email_sent,
            email_error=email_error,
            recipient=recipient,
        )

    finally:
        _cleanup(saved_paths)


@main.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "deal-room-processor"})
