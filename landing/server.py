"""
server.py — TradeIQ Flask Backend
מטרות:
  1. Serve landing page (index.html)
  2. Stripe checkout session creation
  3. Stripe webhook → עדכון pipeline
  4. User registration / login (JWT, SQLite)
  5. /app → proxy redirect ל-Streamlit
"""

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import (
    Flask, request, jsonify, redirect,
    send_from_directory, session, g
)

load_dotenv()

app = Flask(__name__, static_folder=".", template_folder=".")
app.secret_key = os.getenv("FLASK_SECRET", secrets.token_hex(32))

STRIPE_SECRET    = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK   = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STREAMLIT_URL    = os.getenv("STREAMLIT_URL", "http://localhost:8501")
DB_PATH          = os.path.join(os.path.dirname(__file__), "..", "data", "sales", "users.db")

PLANS = {
    "pro":   {"price_id": os.getenv("STRIPE_PRICE_PRO",   ""), "name": "Pro",   "amount": 2900},
    "elite": {"price_id": os.getenv("STRIPE_PRICE_ELITE", ""), "name": "Elite", "amount": 7900},
}


# ─── Database ────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan          TEXT DEFAULT 'free',
                stripe_cid    TEXT,
                stripe_sub    TEXT,
                trial_ends    TEXT,
                created_at    TEXT DEFAULT (datetime('now')),
                last_login    TEXT
            );
            CREATE TABLE IF NOT EXISTS tokens (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            );
        """)


init_db()


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _create_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=30)).isoformat()
    db = get_db()
    db.execute("INSERT INTO tokens VALUES (?,?,?)", (token, user_id, expires))
    db.commit()
    return token


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Unauthorized"}), 401
        db = get_db()
        row = db.execute(
            "SELECT user_id FROM tokens WHERE token=? AND expires_at > datetime('now')", (token,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Invalid or expired token"}), 401
        g.user_id = row["user_id"]
        return f(*args, **kwargs)
    return decorated


# ─── Static ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/app")
def app_redirect():
    """Redirect to Streamlit dashboard (only for paying users in production)."""
    return redirect(STREAMLIT_URL)


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    plan     = data.get("plan", "free")

    if not email or not password or len(password) < 6:
        return jsonify({"error": "Email and password (min 6 chars) required"}), 400

    db = get_db()
    if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
        return jsonify({"error": "Email already registered"}), 409

    trial_ends = (datetime.now() + timedelta(days=14)).isoformat()
    db.execute(
        "INSERT INTO users (email, password_hash, plan, trial_ends) VALUES (?,?,?,?)",
        (email, _hash(password), plan, trial_ends)
    )
    db.commit()
    user_id = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
    token = _create_token(user_id)

    # הוסף ל-pipeline כ-lead
    _add_to_sales_pipeline(email, "web_signup", plan)

    return jsonify({"token": token, "plan": plan, "trial_ends": trial_ends}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email=? AND password_hash=?", (email, _hash(password))
    ).fetchone()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    db.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],))
    db.commit()
    token = _create_token(user["id"])
    return jsonify({"token": token, "plan": user["plan"]}), 200


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    db = get_db()
    user = db.execute(
        "SELECT email, plan, trial_ends, created_at FROM users WHERE id=?", (g.user_id,)
    ).fetchone()
    return jsonify(dict(user))


# ─── Stripe Checkout ─────────────────────────────────────────────────────────

@app.route("/checkout")
def checkout_page():
    plan = request.args.get("plan", "pro")
    # JavaScript redirect to Stripe
    price_id = PLANS.get(plan, PLANS["pro"])["price_id"]
    if not STRIPE_SECRET or not price_id:
        return f"<h1>Stripe not configured yet</h1><p>Add STRIPE_SECRET_KEY and STRIPE_PRICE_{plan.upper()} to .env</p>", 503
    return redirect(f"/api/checkout?plan={plan}")


@app.route("/api/checkout", methods=["GET", "POST"])
def create_checkout():
    """יצירת Stripe Checkout Session."""
    if not STRIPE_SECRET:
        return jsonify({"error": "Stripe not configured"}), 503

    plan = request.args.get("plan", "pro")
    plan_data = PLANS.get(plan, PLANS["pro"])

    headers = {"Authorization": f"Bearer {STRIPE_SECRET}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "mode": "subscription",
        "line_items[0][price]": plan_data["price_id"],
        "line_items[0][quantity]": "1",
        "success_url": f"{request.host_url}success?session_id={{CHECKOUT_SESSION_ID}}&plan={plan}",
        "cancel_url":  f"{request.host_url}#pricing",
        "allow_promotion_codes": "true",
    }

    resp = requests.post("https://api.stripe.com/v1/checkout/sessions", headers=headers, data=data, timeout=10)
    if resp.status_code != 200:
        return jsonify({"error": "Stripe error", "detail": resp.json()}), 502

    checkout_url = resp.json().get("url")
    return redirect(checkout_url)


@app.route("/success")
def success():
    plan = request.args.get("plan", "pro")
    return f"""<!DOCTYPE html><html><head><title>TradeIQ — Welcome!</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-950 text-white flex items-center justify-center min-h-screen">
    <div class="text-center p-12">
      <div class="text-6xl mb-6">🎉</div>
      <h1 class="text-3xl font-bold mb-4">Welcome to TradeIQ {plan.capitalize()}!</h1>
      <p class="text-gray-400 mb-8">Your account is active. Start trading smarter.</p>
      <a href="/app" class="bg-green-500 hover:bg-green-600 text-white px-8 py-4 rounded-xl font-semibold text-lg">
        Open Dashboard →
      </a>
    </div></body></html>"""


# ─── Stripe Webhook ───────────────────────────────────────────────────────────

@app.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig     = request.headers.get("Stripe-Signature", "")

    if STRIPE_WEBHOOK:
        # אימות חתימה
        try:
            import hmac, hashlib
            timestamp = sig.split(",")[0].split("=")[1]
            signed_payload = f"{timestamp}.{payload.decode()}"
            expected = hmac.new(STRIPE_WEBHOOK.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
            received = sig.split("v1=")[1].split(",")[0]
            if not hmac.compare_digest(expected, received):
                return jsonify({"error": "Invalid signature"}), 400
        except Exception:
            return jsonify({"error": "Signature verification failed"}), 400

    event = request.get_json()
    etype = event.get("type", "")

    if etype == "checkout.session.completed":
        session_data = event["data"]["object"]
        customer_email = session_data.get("customer_details", {}).get("email")
        subscription_id = session_data.get("subscription")
        if customer_email:
            db = get_db()
            db.execute(
                "UPDATE users SET plan='pro', stripe_sub=? WHERE email=?",
                (subscription_id, customer_email)
            )
            db.commit()
            # קדם ב-pipeline ל-paying
            _advance_pipeline_to_paying(customer_email)

    elif etype == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]
        db = get_db()
        db.execute("UPDATE users SET plan='free' WHERE stripe_sub=?", (sub_id,))
        db.commit()

    return jsonify({"received": True})


# ─── Sales Pipeline Integration ───────────────────────────────────────────────

def _add_to_sales_pipeline(email: str, source: str, plan: str):
    """מוסיף משתמש חדש ל-pipeline כ-lead."""
    pipeline_path = os.path.join(os.path.dirname(__file__), "..", "data", "sales", "pipeline.json")
    try:
        with open(pipeline_path, encoding="utf-8") as f:
            pipeline = json.load(f)
        pipeline["stages"]["lead"].append({
            "id": email,
            "source": source,
            "contact": email,
            "intent_score": 0.8,
            "title": f"Signup: {plan} plan",
            "added_at": datetime.now().isoformat(),
            "status": "new",
            "notes": f"Registered via website, plan: {plan}",
        })
        pipeline["last_updated"] = datetime.now().isoformat()
        with open(pipeline_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _advance_pipeline_to_paying(email: str):
    """מעביר ל-paying אחרי Stripe checkout."""
    pipeline_path = os.path.join(os.path.dirname(__file__), "..", "data", "sales", "pipeline.json")
    try:
        with open(pipeline_path, encoding="utf-8") as f:
            pipeline = json.load(f)
        for stage in ["lead", "trial", "prospect"]:
            for i, item in enumerate(pipeline["stages"].get(stage, [])):
                if item.get("id") == email:
                    entry = pipeline["stages"][stage].pop(i)
                    entry["stage"] = "paying"
                    entry["converted_at"] = datetime.now().isoformat()
                    pipeline["stages"].setdefault("paying", []).append(entry)
                    break
        pipeline["last_updated"] = datetime.now().isoformat()
        with open(pipeline_path, "w", encoding="utf-8") as f:
            json.dump(pipeline, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "product": "TradeIQ", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
