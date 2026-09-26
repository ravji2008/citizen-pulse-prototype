"""
CitizenPulse — AI for Digital Public Infrastructure & Governance
Track 1 prototype: Google "Build with AI: Code for Communities" hackathon

A scalable, multilingual citizen-feedback aggregation platform that surfaces
infrastructure "demand hotspots" and ranks development priorities for
policymakers, combining citizen complaints (text/voice) with state-level
demographic and infrastructure-index data.

Run:
    pip install -r requirements.txt
    export GEMINI_API_KEY=your_key_here   # optional — falls back to a rule-based
                                           # classifier if not set, so the demo
                                           # always works end-to-end.
    python app.py
    python seed_demo.py                   # optional: populate sample feedback
"""

import os
import json
import sqlite3
from datetime import datetime

from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "citizenpulse.db")

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = None
if GEMINI_SDK_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    MODEL = genai.GenerativeModel("gemini-1.5-flash")

CATEGORIES = [
    "Roads & Transport", "Water Supply", "Electricity", "Sanitation & Waste",
    "Healthcare", "Education", "Digital Connectivity", "Public Safety",
    "Housing", "Other",
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.join(APP_DIR, "data"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT,
            district TEXT,
            language TEXT,
            raw_text TEXT,
            translated_text TEXT,
            category TEXT,
            urgency_score REAL,
            sentiment TEXT,
            source TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state_index (
            state TEXT PRIMARY KEY,
            population_millions REAL,
            infra_index REAL,
            digital_penetration REAL,
            lat REAL,
            lng REAL
        )
    """)
    conn.commit()
    conn.close()


def seed_state_index():
    """Illustrative sample state-level demographic / infrastructure data.

    NOTE: figures are approximate/illustrative sample data for prototype
    purposes (per hackathon rules: 'public datasets, sample data, or APIs
    where live data isn't available'). Swap this table for a real dataset
    (e.g. Census/NITI Aayog indices) before production use.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT COUNT(*) FROM state_index")
    if cur.fetchone()[0] > 0:
        conn.close()
        return
    states = [
        # state, population_millions, infra_index(0-100), digital_penetration(%), lat, lng
        ("Uttar Pradesh", 231.5, 42, 38, 26.8, 80.9),
        ("Maharashtra", 126.2, 61, 55, 19.7, 75.7),
        ("Bihar", 128.5, 31, 29, 25.1, 85.3),
        ("West Bengal", 100.9, 46, 40, 22.9, 87.6),
        ("Madhya Pradesh", 85.4, 39, 33, 23.5, 77.4),
        ("Rajasthan", 81.0, 40, 34, 27.0, 74.2),
        ("Tamil Nadu", 77.8, 68, 60, 11.1, 78.7),
        ("Karnataka", 68.0, 63, 58, 15.3, 75.7),
        ("Gujarat", 70.4, 66, 52, 22.3, 72.6),
        ("Odisha", 46.4, 37, 31, 20.9, 85.1),
        ("Kerala", 35.7, 78, 70, 10.8, 76.3),
        ("Assam", 35.6, 34, 30, 26.2, 92.9),
        ("Punjab", 30.1, 55, 48, 31.1, 75.3),
        ("Jharkhand", 38.6, 33, 28, 23.6, 85.3),
        ("Chhattisgarh", 29.4, 36, 30, 21.3, 81.6),
        ("Delhi", 20.6, 72, 68, 28.6, 77.2),
    ]
    conn.executemany(
        """INSERT INTO state_index
           (state, population_millions, infra_index, digital_penetration, lat, lng)
           VALUES (?,?,?,?,?,?)""",
        states,
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# AI classification (Google Gemini, with a rule-based fallback)
# ---------------------------------------------------------------------------

FALLBACK_KEYWORDS = {
    "Roads & Transport": ["road", "pothole", "bridge", "transport", "bus", "traffic", "sadak", "gaddha", "gaddhe"],
    "Water Supply": ["water", "pani", "paani", "tap", "borewell", "jal"],
    "Electricity": ["electricity", "bijli", "power cut", "transformer", "voltage"],
    "Sanitation & Waste": ["garbage", "sanitation", "toilet", "sewage", "drainage", "naali", "kachra", "safai"],
    "Healthcare": ["hospital", "doctor", "medicine", "clinic", "aspatal", "swasthya", "dawai"],
    "Education": ["school", "teacher", "college", "shiksha", "padhai"],
    "Digital Connectivity": ["internet", "network", "signal", "broadband", "wifi", "mobile network"],
    "Public Safety": ["police", "crime", "safety", "theft", "suraksha"],
    "Housing": ["house", "housing", "makan", "shelter", "slum"],
}

URGENT_WORDS = ["urgent", "emergency", "danger", "died", "accident", "no water",
                "no electricity", "critical", "3 din", "3 days", "weeks"]
NEGATIVE_WORDS = ["bad", "worst", "problem", "issue", "not working", "kharab", "band", "jaam"]


def fallback_classify(text: str) -> dict:
    t = text.lower()
    category = "Other"
    for cat, kws in FALLBACK_KEYWORDS.items():
        if any(kw in t for kw in kws):
            category = cat
            break
    urgency = 0.85 if any(w in t for w in URGENT_WORDS) else 0.5
    sentiment = "negative" if any(w in t for w in NEGATIVE_WORDS) else "neutral"
    return {
        "language_detected": "auto",
        "translated_text": text,
        "category": category,
        "urgency_score": urgency,
        "sentiment": sentiment,
    }


def gemini_classify(text: str) -> dict:
    prompt = f"""You are an AI system for a citizen feedback platform used by Indian
government infrastructure planners. Analyze this citizen complaint or request,
which may be written in Hindi, English, Hinglish, or another Indian language:

"{text}"

Respond with ONLY valid JSON (no markdown fences, no extra text) in this exact schema:
{{
  "language_detected": "<language name>",
  "translated_text": "<English translation>",
  "category": "<one of: {', '.join(CATEGORIES)}>",
  "urgency_score": <float between 0 and 1>,
  "sentiment": "<positive|neutral|negative>"
}}"""
    try:
        response = MODEL.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        data["category"] = data.get("category") if data.get("category") in CATEGORIES else "Other"
        return data
    except Exception as exc:  # noqa: BLE001 — demo-grade fallback on any API error
        app.logger.warning("Gemini classification failed, using fallback: %s", exc)
        return fallback_classify(text)


def classify_feedback(text: str) -> dict:
    if MODEL is not None:
        return gemini_classify(text)
    return fallback_classify(text)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/submit", methods=["POST"])
def submit_feedback():
    payload = request.get_json(force=True) or {}
    text = (payload.get("text") or "").strip()
    state = payload.get("state") or "Unknown"
    district = payload.get("district") or ""
    source = payload.get("source") or "text"

    if not text:
        return jsonify({"error": "text is required"}), 400

    analysis = classify_feedback(text)

    conn = get_db()
    conn.execute(
        """INSERT INTO feedback
           (state, district, language, raw_text, translated_text, category,
            urgency_score, sentiment, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            state, district, analysis.get("language_detected", "unknown"), text,
            analysis.get("translated_text", text), analysis.get("category", "Other"),
            analysis.get("urgency_score", 0.5), analysis.get("sentiment", "neutral"),
            source, datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    return jsonify({"status": "ok", "analysis": analysis})


@app.route("/api/feedback", methods=["GET"])
def list_feedback():
    conn = get_db()
    rows = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 200").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/hotspots", methods=["GET"])
def hotspots():
    """Aggregate feedback by state + category and rank by a priority score.

    priority_score = complaint_count * avg_urgency * (100 - infra_index) / 100

    This rewards categories/states with many, urgent complaints AND weak
    existing infrastructure — i.e. where a new investment closes the biggest
    gap. This is a transparent, tunable scoring formula standing in for the
    'predictive modelling' component in this prototype; it can be swapped for
    a trained model without changing the API contract.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT f.state, f.category, COUNT(*) as complaint_count,
               AVG(f.urgency_score) as avg_urgency,
               s.infra_index, s.population_millions, s.lat, s.lng
        FROM feedback f
        LEFT JOIN state_index s ON f.state = s.state
        GROUP BY f.state, f.category
    """).fetchall()

    results = []
    for r in rows:
        infra = r["infra_index"] if r["infra_index"] is not None else 50
        avg_urgency = r["avg_urgency"] or 0.5
        priority = (r["complaint_count"] * avg_urgency * (100 - infra)) / 100
        results.append({
            "state": r["state"],
            "category": r["category"],
            "complaint_count": r["complaint_count"],
            "avg_urgency": round(avg_urgency, 2),
            "infra_index": infra,
            "population_millions": r["population_millions"],
            "priority_score": round(priority, 2),
            "lat": r["lat"],
            "lng": r["lng"],
        })
    results.sort(key=lambda x: x["priority_score"], reverse=True)
    return jsonify(results)


@app.route("/api/states", methods=["GET"])
def states():
    conn = get_db()
    rows = conn.execute("SELECT * FROM state_index ORDER BY state").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "gemini_enabled": MODEL is not None})


if __name__ == "__main__":
    init_db()
    seed_state_index()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)