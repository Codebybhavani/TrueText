import os
import io
import uuid
import jwt
import bcrypt
import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import database as db
import ml_model
import file_extract

HERE = os.path.dirname(__file__)
app = Flask(
    __name__,
    template_folder=os.path.join(HERE, "..", "templates"),
    static_folder=os.path.join(HERE, "..", "static"),
)
CORS(app)

# CHANGE THIS in production, e.g. load from an environment variable
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

db.init_db()


# ---------- Auth helpers ----------
def make_token(user_id, username):
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        request.user_id = payload["user_id"]
        request.username = payload["username"]
        return f(*args, **kwargs)
    return decorated


# ---------- Page routes ----------
@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# ---------- Auth API ----------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or len(password) < 6:
        return jsonify({"error": "Username, email required. Password must be 6+ characters."}), 400

    if db.get_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 409

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        db.create_user(username, email, password_hash)
    except Exception as e:
        return jsonify({"error": f"Could not create user: {e}"}), 400

    user = db.get_user_by_username(username)
    token = make_token(user["id"], user["username"])
    return jsonify({"token": token, "username": username}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = db.get_user_by_username(username)
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid username or password"}), 401

    token = make_token(user["id"], user["username"])
    return jsonify({"token": token, "username": user["username"]})


# ---------- Detection API ----------
def _run_detection_and_save(text, filename=None):
    result = ml_model.predict(text)
    detection_id = db.save_detection(
        request.user_id, text, result["label"], result["ai_probability"], result["human_probability"],
        filename=filename,
    )
    result["id"] = detection_id
    result["text"] = text
    return result


@app.route("/api/detect", methods=["POST"])
@token_required
def detect():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if len(text.split()) < 5:
        return jsonify({"error": "Please enter at least 5 words of text."}), 400
    return jsonify(_run_detection_and_save(text))


@app.route("/api/detect-file", methods=["POST"])
@token_required
def detect_file():
    """Detector panel file upload: extracts text from a .txt/.pdf/.docx file
    and runs it through the same detector used for pasted text."""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file received."}), 400

    try:
        text = file_extract.extract_text(f)
    except file_extract.ExtractionError as e:
        return jsonify({"error": str(e)}), 400

    if len(text.split()) < 5:
        return jsonify({"error": "Extracted text is too short (need 5+ words)."}), 400

    return jsonify(_run_detection_and_save(text, filename=f.filename))


def compute_similarity_pairs(named_texts, sim_threshold):
    """Pairwise TF-IDF cosine similarity across a batch of submissions —
    flags likely-copied pairs (a lightweight plagiarism check), independent
    of the AI/Human detector."""
    if len(named_texts) < 2:
        return []
    names = [n for n, _ in named_texts]
    texts = [t for _, t in named_texts]
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        matrix = vec.fit_transform(texts)
        sims = cosine_similarity(matrix)
    except Exception:
        return []

    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            score = round(float(sims[i][j]) * 100, 1)
            if score >= sim_threshold:
                pairs.append({"file_a": names[i], "file_b": names[j], "similarity": score})
    pairs.sort(key=lambda p: -p["similarity"])
    return pairs


@app.route("/api/batch-detect", methods=["POST"])
@token_required
def batch_detect():
    """Instructor batch mode: upload several .txt files at once, get one
    sortable set of results back instead of checking students one by one.
    Also cross-compares every pair of submissions for text similarity
    (a lightweight plagiarism check) using TF-IDF cosine similarity."""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files received. Attach one or more .txt files."}), 400

    try:
        threshold = float(request.form.get("threshold", 70))
    except ValueError:
        threshold = 70.0
    try:
        sim_threshold = float(request.form.get("similarity_threshold", 60))
    except ValueError:
        sim_threshold = 60.0

    batch_id = uuid.uuid4().hex[:12]
    results = []
    valid_texts = []   # (filename, text) for similarity comparison
    for f in files:
        if not f.filename:
            continue
        try:
            raw = f.read()
            text = raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            continue
        if len(text.split()) < 5:
            results.append({
                "filename": f.filename, "error": "Too short (need 5+ words)",
                "ai_probability": None, "human_probability": None,
                "label": None, "word_count": len(text.split()), "flagged": False,
            })
            continue

        r = ml_model.predict_fast(text)
        db.save_detection(
            request.user_id, text, r["label"], r["ai_probability"], r["human_probability"],
            batch_id=batch_id, filename=f.filename,
        )
        results.append({
            "filename": f.filename,
            "word_count": r["word_count"],
            "ai_probability": r["ai_probability"],
            "human_probability": r["human_probability"],
            "label": r["label"],
            "flagged": r["ai_probability"] >= threshold,
        })
        valid_texts.append((f.filename, text))

    valid = [r for r in results if r.get("ai_probability") is not None]
    class_avg = round(sum(r["ai_probability"] for r in valid) / len(valid), 2) if valid else 0
    flagged_count = sum(1 for r in valid if r["flagged"])

    results.sort(key=lambda r: (r.get("ai_probability") is None, -(r.get("ai_probability") or 0)))

    similarity_pairs = compute_similarity_pairs(valid_texts, sim_threshold)

    return jsonify({
        "batch_id": batch_id,
        "threshold": threshold,
        "similarity_threshold": sim_threshold,
        "class_average_ai": class_avg,
        "flagged_count": flagged_count,
        "similarity_pairs": similarity_pairs,
        "total": len(results),
        "results": results,
    })


@app.route("/api/history", methods=["GET"])
@token_required
def history():
    rows = db.get_history(request.user_id)
    items = [
        {
            "id": r["id"],
            "text": r["text"][:150] + ("..." if len(r["text"]) > 150 else ""),
            "label": r["label"],
            "ai_probability": r["ai_probability"],
            "human_probability": r["human_probability"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    total = len(items)
    avg_ai = round(sum(i["ai_probability"] for i in items) / total, 2) if total else 0
    return jsonify({"items": items, "total_scans": total, "average_ai_score": avg_ai})


@app.route("/api/report/<int:detection_id>", methods=["GET"])
@token_required
def report(detection_id):
    row = db.get_detection(detection_id, request.user_id)
    if not row:
        return jsonify({"error": "Report not found"}), 404

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("TrueText — Detection Report", styles["Title"]),
        Spacer(1, 0.2 * inch),
        Paragraph(f"<b>Date:</b> {row['created_at']}", styles["Normal"]),
        Paragraph(f"<b>Prediction:</b> {row['label']}", styles["Normal"]),
        Paragraph(f"<b>AI Probability:</b> {row['ai_probability']}%", styles["Normal"]),
        Paragraph(f"<b>Human Probability:</b> {row['human_probability']}%", styles["Normal"]),
        Spacer(1, 0.3 * inch),
        Paragraph("<b>Analyzed Text:</b>", styles["Heading3"]),
        Paragraph(row["text"].replace("\n", "<br/>"), styles["Normal"]),
    ]
    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"report_{detection_id}.pdf"
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
