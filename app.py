from flask import Flask, jsonify, request
from db import get_db_connection
from scorer import calculate_effectiveness

app = Flask(__name__)

# ── Health Check ──────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({"message": "Attendance vs Impact Analyzer API is running."})

# ── Get all legislators ───────────────────────────────────
@app.route('/legislators', methods=['GET'])
def get_legislators():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM legislators")
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

# ── Get attendance for a legislator ──────────────────────
@app.route('/attendance/<int:legislator_id>', methods=['GET'])
def get_attendance(legislator_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.session_date, s.topic, a.status
        FROM attendance a
        JOIN sessions s ON a.session_id = s.id
        WHERE a.legislator_id = %s
    """, (legislator_id,))
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

# ── Calculate and return effectiveness score ──────────────
@app.route('/score/<int:legislator_id>', methods=['GET'])
def get_score(legislator_id):
    score_data = calculate_effectiveness(legislator_id)
    return jsonify(score_data)

# ── Get all scores (dashboard view) ──────────────────────
@app.route('/dashboard', methods=['GET'])
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.name, l.constituency, e.final_score, e.rating, e.period
        FROM effectiveness_scores e
        JOIN legislators l ON e.legislator_id = l.id
        ORDER BY e.final_score DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

# ── Audit log ─────────────────────────────────────────────
@app.route('/audit', methods=['GET'])
def get_audit_log():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, l.name as legislator_name
        FROM audit_log a
        JOIN legislators l ON a.legislator_id = l.id
        ORDER BY a.created_at DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)