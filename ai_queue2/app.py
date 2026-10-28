import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATABASE = "database.db"
AVERAGE_SERVICE_TIME_MINUTES = 5


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the queue_entries table if it doesn't exist yet."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue_entries (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT    NOT NULL,
            service       TEXT    NOT NULL,
            token_number  TEXT    NOT NULL UNIQUE,
            status        TEXT    NOT NULL DEFAULT 'WAITING',
            created_at    TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def generate_next_token(conn):
    """Generate the next token like A-01, A-02, A-03..."""
    row = conn.execute("""
        SELECT token_number FROM queue_entries
        WHERE token_number LIKE 'A-%'
        ORDER BY id DESC LIMIT 1
    """).fetchone()

    if row is None:
        next_num = 1
    else:
        next_num = int(row["token_number"].split("-")[1]) + 1

    return f"A-{next_num:02d}"


def get_current_serving_token(conn):
    """Return the token_number currently being served, or None."""
    row = conn.execute("""
        SELECT token_number FROM queue_entries
        WHERE status = 'SERVING'
        ORDER BY id ASC LIMIT 1
    """).fetchone()
    return row["token_number"] if row else None


def count_people_ahead(conn, token_number):
    """Count WAITING customers ahead of this token."""
    row = conn.execute("""
        SELECT COUNT(*) AS c FROM queue_entries
        WHERE status = 'WAITING' AND token_number < ?
    """, (token_number,)).fetchone()
    return row["c"]


def serialize_entry(row):
    """Convert a sqlite3.Row to a plain dict for JSON responses."""
    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "service": row["service"],
        "token_number": row["token_number"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


# ============================================================
# HTML PAGE ROUTES
# ============================================================

@app.route("/")
def home():
    """Homepage."""
    conn = get_db()

    current = get_current_serving_token(conn) or "—"
    waiting_count = conn.execute(
        "SELECT COUNT(*) AS c FROM queue_entries WHERE status = 'WAITING'"
    ).fetchone()["c"]
    conn.close()

    queue_info = {
        "current_token": current,
        "people_waiting": waiting_count,
        "estimated_wait_minutes": waiting_count * AVERAGE_SERVICE_TIME_MINUTES,
    }

    services = [
        {"id": 1, "name": "General Consultation", "icon": "🩺"},
        {"id": 2, "name": "Technical Support",    "icon": "💻"},
        {"id": 3, "name": "Customer Service",     "icon": "🎧"},
        {"id": 4, "name": "Other Service",        "icon": "📋"},
    ]

    return render_template("index.html", queue=queue_info, services=services)


@app.route("/queue/<token>")
def queue_page(token):
    """Live queue page for a specific token."""
    return render_template("queue.html", token=token)


@app.route("/staff")
def staff_page():
    """Staff dashboard."""
    return render_template("staff.html")


# ============================================================
# JSON API ENDPOINTS
# ============================================================

@app.route("/api/join-queue", methods=["POST"])
def api_join_queue():
    """Create a new queue entry and return the ticket info."""
    data = request.get_json() or {}
    name = (data.get("customer_name") or "").strip()
    service = (data.get("service") or "").strip()

    if not name or not service:
        return jsonify({"error": "customer_name and service are required"}), 400

    conn = get_db()
    try:
        token = generate_next_token(conn)
        conn.execute("""
            INSERT INTO queue_entries
                (customer_name, service, token_number, status, created_at)
            VALUES (?, ?, ?, 'WAITING', ?)
        """, (name, service, token, datetime.now().isoformat()))
        conn.commit()

        people_ahead = count_people_ahead(conn, token)
        estimated_wait = people_ahead * AVERAGE_SERVICE_TIME_MINUTES

        return jsonify({
            "token_number": token,
            "customer_name": name,
            "service": service,
            "status": "WAITING",
            "people_ahead": people_ahead,
            "estimated_wait_minutes": estimated_wait,
        }), 201
    finally:
        conn.close()


@app.route("/api/queue")
def api_queue():
    """Return the full queue (staff dashboard)."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM queue_entries ORDER BY id ASC").fetchall()
    current = get_current_serving_token(conn)
    conn.close()

    return jsonify({
        "current_serving": current,
        "entries": [serialize_entry(r) for r in rows],
    })


@app.route("/api/queue/<token>")
def api_queue_by_token(token):
    """Return info for one specific token."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM queue_entries WHERE token_number = ?", (token,)
    ).fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "Token not found"}), 404

    people_ahead = count_people_ahead(conn, token)
    estimated_wait = people_ahead * AVERAGE_SERVICE_TIME_MINUTES
    current = get_current_serving_token(conn)
    conn.close()

    return jsonify({
        **serialize_entry(row),
        "people_ahead": people_ahead,
        "estimated_wait_minutes": estimated_wait,
        "current_serving": current,
    })


@app.route("/api/queue/<token>/cancel", methods=["POST"])
def api_cancel(token):
    """Cancel a WAITING token."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM queue_entries WHERE token_number = ?", (token,)
    ).fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "Token not found"}), 404

    if row["status"] != "WAITING":
        conn.close()
        return jsonify({"error": f"Cannot cancel a token with status {row['status']}"}), 400

    conn.execute(
        "UPDATE queue_entries SET status = 'CANCELLED' WHERE token_number = ?",
        (token,)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Cancelled", "token_number": token})


# ============================================================
# STAFF ACTIONS
# ============================================================

@app.route("/api/staff/call-next", methods=["POST"])
def api_call_next():
    """Move the first WAITING customer to SERVING."""
    conn = get_db()

    existing = conn.execute(
        "SELECT token_number FROM queue_entries WHERE status = 'SERVING'"
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({
            "error": f"Please complete {existing['token_number']} first"
        }), 400

    next_row = conn.execute("""
        SELECT * FROM queue_entries WHERE status = 'WAITING'
        ORDER BY id ASC LIMIT 1
    """).fetchone()

    if next_row is None:
        conn.close()
        return jsonify({"error": "No waiting customers"}), 404

    conn.execute(
        "UPDATE queue_entries SET status = 'SERVING' WHERE id = ?",
        (next_row["id"],)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Now serving", "token_number": next_row["token_number"]})


@app.route("/api/staff/complete", methods=["POST"])
def api_complete():
    """Mark the currently SERVING token as COMPLETED."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM queue_entries WHERE status = 'SERVING' LIMIT 1"
    ).fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "No customer is being served"}), 404

    conn.execute(
        "UPDATE queue_entries SET status = 'COMPLETED' WHERE id = ?",
        (row["id"],)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Completed", "token_number": row["token_number"]})


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)