import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent

# The rest of the project uses relative rag_db paths, so keep the app rooted here.
os.chdir(BASE_DIR)

app = Flask(__name__, template_folder="templates", static_folder="static")

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

_generator = None


def get_generator():
    global _generator

    if _generator is None:
        from backend.retrievals.hybrid_rag.MUTI_GENERATE.multi_generate import MULTI_GENERATE

        _generator = MULTI_GENERATE()

    return _generator


def save_and_index_files(files):
    uploaded_files = []

    for incoming_file in files:
        if not incoming_file or not incoming_file.filename:
            continue

        filename = secure_filename(incoming_file.filename)
        if not filename:
            continue
        if Path(filename).suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")

        destination = UPLOAD_DIR / filename
        incoming_file.save(destination)

        doc_id = Path(filename).stem

        from backend.retrievals.hybrid_rag.database.ingest_pdf import ingest_pdf

        ingest_pdf(str(destination), doc_id)

        uploaded_files.append(
            {
                "name": filename,
                "size": destination.stat().st_size,
            }
        )

    return uploaded_files


def generate_response(prompt):
    response_stream = get_generator().multi_generate(prompt)

    if isinstance(response_stream, str):
        return response_stream.strip()

    return "".join(str(chunk) for chunk in response_stream).strip()


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return render_template("index.html")

    try:
        prompt = (request.form.get("prompt") or "").strip()
        incoming_files = request.files.getlist("files")
        has_uploads = any(uploaded_file and uploaded_file.filename for uploaded_file in incoming_files)
        uploaded_files = save_and_index_files(incoming_files) if has_uploads else []

        if not prompt and not uploaded_files:
            return jsonify({"response": "Enter a prompt or upload at least one PDF."}), 400

        response_text = "Document uploaded successfully."
        if prompt:
            response_text = generate_response(prompt) or "No response generated."

        return jsonify(
            {
                "response": response_text,
                "uploaded_files": uploaded_files,
            }
        )
    except ValueError as exc:
        return jsonify({"response": str(exc)}), 400
    except Exception as exc:
        return jsonify({"response": f"Request failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("DEBUG", "false").lower() == "true",
    )
