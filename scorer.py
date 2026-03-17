from db import get_db_connection

# ── Weights (must sum to 1.0) ─────────────────────────────
WEIGHTS = {
    "attendance": 0.30,
    "debate":     0.30,
    "bills":      0.25,
    "policy":     0.15
}

def calculate_effectiveness(legislator_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Attendance Score
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(status = 'present') as present
        FROM attendance
        WHERE legislator_id = %s
    """, (legislator_id,))
    att = cursor.fetchone()
    attendance_score = (att['present'] / att['total'] * 100) if att['total'] > 0 else 0

    # 2. Debate Score
    level_map = {'none': 0, 'low': 25, 'medium': 60, 'high': 100}
    cursor.execute("""
        SELECT participation_level, speaking_time_mins
        FROM debates WHERE legislator_id = %s
    """, (legislator_id,))
    debates = cursor.fetchall()
    if debates:
        debate_score = sum(level_map[d['participation_level']] for d in debates) / len(debates)
    else:
        debate_score = 0

    # 3. Bills Score (capped at 100 for 5+ bills)
    cursor.execute("""
        SELECT COUNT(*) as count FROM bills WHERE proposed_by = %s
    """, (legislator_id,))
    bills = cursor.fetchone()
    bills_score = min(bills['count'] * 20, 100)

    # 4. Policy Score (passed bills ratio)
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(status = 'passed') as passed
        FROM bills WHERE proposed_by = %s
    """, (legislator_id,))
    policy = cursor.fetchone()
    policy_score = (policy['passed'] / policy['total'] * 100) if policy['total'] > 0 else 0

    # 5. Final Weighted Score
    final_score = (
        attendance_score * WEIGHTS['attendance'] +
        debate_score     * WEIGHTS['debate'] +
        bills_score      * WEIGHTS['bills'] +
        policy_score     * WEIGHTS['policy']
    )

    # 6. Rating
    if final_score >= 70:
        rating = 'high'
    elif final_score >= 40:
        rating = 'moderate'
    else:
        rating = 'low'

    # 7. Save to effectiveness_scores
    cursor.execute("""
        INSERT INTO effectiveness_scores 
        (legislator_id, period, attendance_score, debate_score, bills_score, policy_score, final_score, rating)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (legislator_id, '2024-Q1', attendance_score, debate_score, bills_score, policy_score, final_score, rating))

    # 8. Log to audit_log
    cursor.execute("""
        INSERT INTO audit_log (legislator_id, ai_score, approved)
        VALUES (%s, %s, %s)
    """, (legislator_id, final_score, False))

    conn.commit()
    conn.close()

    return {
        "legislator_id": legislator_id,
        "attendance_score": round(attendance_score, 2),
        "debate_score": round(debate_score, 2),
        "bills_score": round(bills_score, 2),
        "policy_score": round(policy_score, 2),
        "final_score": round(final_score, 2),
        "rating": rating
    }