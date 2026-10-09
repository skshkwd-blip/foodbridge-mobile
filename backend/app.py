import sys
import os
import pymysql
import random
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from db import mysql
from passwords import hash_pw, check_pw

# ═════════════════════════════════════════════════════════════
# DATABASE CONFIG  (override any of these with env vars)
# ═════════════════════════════════════════════════════════════

DB_HOST     = os.environ.get('MYSQL_HOST', 'localhost')
DB_USER     = os.environ.get('MYSQL_USER', 'root')
DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
DB_NAME     = os.environ.get('MYSQL_DB', 'food_db')
DB_PORT     = int(os.environ.get('MYSQL_PORT', 3306))
DB_USE_SSL  = os.environ.get('MYSQL_USE_SSL', 'false').lower() == 'true'

# ═════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# Full schema lives in schema.sql (same folder as this file).
# ═════════════════════════════════════════════════════════════

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')


def _load_schema_statements():
    """Reads schema.sql and splits it into individual executable statements."""
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        raw_sql = f.read()
    lines = [ln for ln in raw_sql.splitlines() if not ln.strip().startswith('--')]
    return [st.strip() for st in '\n'.join(lines).split(';') if st.strip()]


def init_database():
    """
    Creates every table from schema.sql if it is missing. Hosted databases
    (Aiven, PythonAnywhere ...) already provide the database, so the
    CREATE DATABASE / USE statements are skipped. If the database does not
    exist at all (typical on a laptop) it is created.
    """
    statements = [st for st in _load_schema_statements()
                  if not st.upper().startswith(('CREATE DATABASE', 'USE '))]

    ssl_ctx = None
    if DB_USE_SSL:
        import ssl as ssl_lib
        ssl_ctx = ssl_lib.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_lib.CERT_NONE

    def connect(db=None):
        return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                               port=DB_PORT, ssl=ssl_ctx, database=db)

    try:
        conn = connect(DB_NAME)
    except pymysql.err.OperationalError as e:
        if e.args[0] != 1049:          # 1049 = unknown database
            raise
        root = connect()
        with root.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4")
        root.close()
        conn = connect(DB_NAME)
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
        print("Database tables verified/created from schema.sql.")
    finally:
        conn.close()


init_database()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    if os.environ.get('RENDER'):
        raise RuntimeError('Set the SECRET_KEY environment variable')
    app.secret_key = 'dev-only-secret-change-me'   # local development only
app.config['MYSQL_HOST']        = DB_HOST
app.config['MYSQL_USER']        = DB_USER
app.config['MYSQL_PASSWORD']    = DB_PASSWORD
app.config['MYSQL_DB']          = DB_NAME
app.config['MYSQL_PORT']        = DB_PORT
app.config['MYSQL_USE_SSL']     = DB_USE_SSL
app.config['MYSQL_CURSORCLASS'] = 'Cursor'

mysql.init_app(app)

from mobile_auth import init_mobile_auth
from verification import init_verification
init_mobile_auth(app)
init_verification(app)

# ═════════════════════════════════════════════════════════════
# EXPIRY HELPER
# Marks all Pending donations as 'Wasted' where:
#   - donation_status = 'Pending'
#   - date_of_donation <= TODAY
#   - time (available_until) < NOW() current time
#   - time is not NULL
# Called automatically before any endpoint that reads Pending donations.
# ═════════════════════════════════════════════════════════════

def expire_donations(cur):
    """
    Marks Pending donations as Wasted when:
      - The donation date is today and available-until time has passed, OR
      - The donation date is before today (entirely past).
    Only affects donations with a non-NULL time field.
    """
    now = datetime.now()
    today = date.today()
    current_time_str = now.strftime('%H:%M:%S')
    today_str = today.strftime('%Y-%m-%d')

    cur.execute("""
        UPDATE food_donation
        SET donation_status = 'Wasted'
        WHERE donation_status = 'Pending'
          AND time IS NOT NULL
          AND (
            -- Date is in the past
            date_of_donation < %s
            OR
            -- Date is today but the available-until time has passed
            (date_of_donation = %s AND time < %s)
          )
    """, (today_str, today_str, current_time_str))


# ═════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═════════════════════════════════════════════════════════════

@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM donor")
    donors = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ngo")
    ngos = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM food_donation")
    meals = cur.fetchone()[0]
    cur.close()
    return render_template("index.html", donors=donors, ngos=ngos, meals=meals)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/donor')
def donor():
    if 'user_id' not in session or session.get('role') != 'donor':
        return redirect(url_for('login'))
    return render_template('donor.html', name=session.get('user_name'))

@app.route('/ngo')
def ngo():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return redirect('/login')
    cur = mysql.connection.cursor()
    cur.execute("SELECT ngo_name FROM ngo WHERE ngo_id = %s", (session['user_id'],))
    row = cur.fetchone()
    cur.close()
    if not row:
        return "NGO not found", 404
    session['user_name'] = row[0]
    return render_template('ngo.html', name=row[0])

@app.route('/volunteer')
def volunteer_page():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return redirect('/login')
    cur = mysql.connection.cursor()
    cur.execute("SELECT name FROM volunteer WHERE volunteer_id = %s", (session['user_id'],))
    row = cur.fetchone()
    cur.close()
    if not row:
        return "Volunteer not found", 404
    return render_template('volunteer.html', name=row[0])

# ── LOGIN ─────────────────────────────────────────────────────

@app.route('/do_login', methods=['POST'])
def do_login():
    name     = request.form.get('name', '').strip()
    password = request.form.get('password', '').strip()
    role     = request.form.get('role', 'donor').strip().lower()

    if not name or not password:
        return render_template('login.html', error="Please fill in all fields")

    cur = mysql.connection.cursor()

    if role == 'donor':
        cur.execute(
            "SELECT donor_id,donor_name,password FROM donor WHERE LOWER(TRIM(donor_name))=LOWER(TRIM(%s))",
            (name,))
        user = cur.fetchone(); cur.close()
        if not user:
            return render_template('login.html', error="Donor not found.")
        if not check_pw(user[2], password):
            return render_template('login.html', error="Incorrect password.")
        session.clear()
        session['user_id'] = user[0]; session['user_name'] = user[1]; session['role'] = 'donor'
        return redirect('/donor')

    if role == 'ngo':
        cur.execute(
            "SELECT ngo_id,ngo_name,password FROM ngo WHERE LOWER(TRIM(ngo_name))=LOWER(TRIM(%s))",
            (name,))
        row = cur.fetchone(); cur.close()
        if not row:
            return render_template('login.html', error="NGO not found.")
        if not check_pw(row[2], password):
            return render_template('login.html', error="Incorrect password.")
        session.clear()
        session['user_id'] = row[0]; session['user_name'] = row[1]; session['role'] = 'ngo'
        return redirect('/ngo')

    if role == 'volunteer':
        cur.execute(
            "SELECT volunteer_id,name,password FROM volunteer WHERE LOWER(TRIM(name))=LOWER(TRIM(%s))",
            (name,))
        vol = cur.fetchone(); cur.close()
        if not vol:
            return render_template('login.html', error="Volunteer not found.")
        if not check_pw(vol[2], password):
            return render_template('login.html', error="Incorrect password.")
        session.clear()
        session['user_id'] = vol[0]; session['user_name'] = vol[1]; session['role'] = 'volunteer'
        return redirect('/volunteer')

    cur.close()
    return render_template('login.html', error="Invalid role.")

# ── SIGNUP ────────────────────────────────────────────────────

@app.route('/do_signup', methods=['POST'])
def do_signup():
    name     = request.form.get('name', '').strip()
    email    = request.form.get('email', '').strip()
    mobile   = request.form.get('mobile', '').strip()
    password = request.form.get('password', '').strip()
    role     = request.form.get('role', 'donor').strip().lower()

    if not name or not password or not email:
        return render_template('signup.html', error="Please fill in all required fields.")

    cur = mysql.connection.cursor()

    if role == 'donor':
        cur.execute("SELECT donor_id FROM donor WHERE LOWER(TRIM(donor_name))=LOWER(TRIM(%s))", (name,))
        if cur.fetchone():
            cur.close()
            return render_template('signup.html', error="Donor name already exists.")
        cur.execute(
            "INSERT INTO donor (donor_name,donor_type,contact_no,address,hygiene_rating,password,role,email) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (name, 'Individual', mobile, '', 0, hash_pw(password), 'donor', email))

    elif role == 'volunteer':
        cur.execute("SELECT volunteer_id FROM volunteer WHERE LOWER(TRIM(name))=LOWER(TRIM(%s))", (name,))
        if cur.fetchone():
            cur.close()
            return render_template('signup.html', error="Volunteer name already exists.")
        cur.execute(
            "INSERT INTO volunteer (name,contact_no,vehicle_type,availability_status,password) VALUES (%s,%s,%s,%s,%s)",
            (name, mobile, 'None', 'Available', hash_pw(password)))

    elif role == 'ngo':
        address      = request.form.get('address', '')
        capacity_raw = request.form.get('capacity', '').strip()
        capacity     = int(capacity_raw) if capacity_raw.isdigit() else 0
        priority     = request.form.get('priority', 'Medium')
        cur.execute(
            "INSERT INTO ngo (ngo_name,contact_no,address,capacity,priority_level,password) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, mobile, address, capacity, priority, hash_pw(password)))
    else:
        cur.close()
        return render_template('signup.html', error="Invalid role.")

    mysql.connection.commit()
    cur.close()
    return redirect('/login')

# ── LOGOUT ────────────────────────────────────────────────────

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── SESSION INFO ──────────────────────────────────────────────

@app.route('/api/me')
def me():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    if session.get('role') == 'ngo':
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT ngo_name FROM ngo WHERE ngo_id=%s", (session['user_id'],))
            row = cur.fetchone()
            cur.close()
            if row:
                session['user_name'] = row[0]
        except Exception:
            pass
    return jsonify({
        "user_id":   session['user_id'],
        "user_name": session['user_name'],
        "role":      session['role']
    })

# ═════════════════════════════════════════════════════════════
# API — DONOR PROFILE
# ═════════════════════════════════════════════════════════════

@app.route('/api/donor/profile')
def donor_profile():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT donor_name,contact_no,address,hygiene_rating,email FROM donor WHERE donor_id=%s",
        (session['user_id'],))
    row = cur.fetchone(); cur.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "donor_name": row[0], "contact_no":     row[1],
        "address":    row[2], "hygiene_rating": float(row[3]) if row[3] else 0,
        "email":      row[4]
    })

@app.route('/api/donor/update', methods=['POST'])
def update_donor_profile():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    d = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE donor SET donor_name=%s,contact_no=%s,address=%s,email=%s WHERE donor_id=%s",
        (d.get('donor_name'), d.get('contact_no'), d.get('address'), d.get('email'), session['user_id']))
    mysql.connection.commit(); cur.close()
    session['user_name'] = d.get('donor_name')
    return jsonify({"success": True, "message": "Profile updated"})

# ═════════════════════════════════════════════════════════════
# API — DONOR STATS
# ═════════════════════════════════════════════════════════════

@app.route('/api/donor/stats')
def donor_stats():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    # Expire donations before counting
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in stats:", e)

    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donor_id=%s", (session['user_id'],))
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donor_id=%s AND donation_status='Pending'", (session['user_id'],))
    pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donor_id=%s AND donation_status='Accepted'", (session['user_id'],))
    accepted = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donor_id=%s AND donation_status='Completed'", (session['user_id'],))
    completed = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donor_id=%s AND donation_status='Wasted'", (session['user_id'],))
    wasted = cur.fetchone()[0]
    cur.close()
    return jsonify({"success": True, "stats": {
        "total": total, "pending": pending, "accepted": accepted,
        "completed": completed, "wasted": wasted
    }})

# ═════════════════════════════════════════════════════════════
# API — DONOR DONATIONS
# ═════════════════════════════════════════════════════════════

@app.route('/api/donor/donations')
def donor_own_donations():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    # Expire donations before fetching
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in donations:", e)

    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity, fd.donation_status,
               fd.time, fd.date_of_donation,
               fd.original_quantity, fd.accepted_quantity,
               p.status       AS pickup_status,
               p.otp_code,
               v.name         AS volunteer_name,
               v.contact_no   AS volunteer_contact,
               dl.delivery_status,
               n.ngo_name
        FROM food_donation fd
        LEFT JOIN pickup    p  ON p.donation_id  = fd.donation_id
        LEFT JOIN volunteer v  ON v.volunteer_id = p.volunteer_id
        LEFT JOIN delivery  dl ON dl.pickup_id   = p.pickup_id
        LEFT JOIN ngo       n  ON n.ngo_id        = dl.ngo_id
        WHERE fd.donor_id = %s
          AND fd.donation_status != 'Wasted'
        ORDER BY fd.donation_id DESC
    """, (session['user_id'],))
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "donation_id":        r[0],  "food_type":          r[1],
            "quantity":           r[2],  "donation_status":    r[3],
            "time":               str(r[4])  if r[4]  else None,
            "date_of_donation":   str(r[5])  if r[5]  else None,
            "original_quantity":  r[6],
            "accepted_quantity":  r[7],
            "pickup_status":      r[8],  "otp_code":            r[9],
            "volunteer_name":     r[10], "volunteer_contact":   r[11],
            "delivery_status":    r[12], "ngo_name":             r[13]
        })
    return jsonify({"success": True, "data": data})

# ═════════════════════════════════════════════════════════════
# API — DONOR WASTED DONATIONS
# ═════════════════════════════════════════════════════════════

@app.route('/api/donor/wasted-donations')
def donor_wasted_donations():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    # Run expiry check so newly expired ones show up immediately
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in wasted:", e)

    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity,
               fd.time, fd.date_of_donation,
               fd.original_quantity, fd.accepted_quantity
        FROM food_donation fd
        WHERE fd.donor_id = %s
          AND fd.donation_status = 'Wasted'
        ORDER BY fd.donation_id DESC
    """, (session['user_id'],))
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "donation_id":       r[0],
            "food_type":         r[1],
            "quantity":          r[2],
            "available_until":   str(r[3]) if r[3] else None,
            "date_of_donation":  str(r[4]) if r[4] else None,
            "original_quantity": r[5],
            "accepted_quantity": r[6]
        })
    return jsonify({"success": True, "data": data})

# ═════════════════════════════════════════════════════════════
# API — NGO & VOLUNTEER WASTED DONATIONS
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/wasted-donations')
def ngo_wasted_donations():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in ngo wasted:", e)

    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity,
               fd.time, fd.date_of_donation,
               fd.original_quantity, fd.accepted_quantity
        FROM food_donation fd
        WHERE fd.donation_status = 'Wasted'
        ORDER BY fd.donation_id DESC
    """)
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "donation_id":       r[0],
            "food_type":         r[1],
            "quantity":          r[2],
            "available_until":   str(r[3]) if r[3] else None,
            "date_of_donation":  str(r[4]) if r[4] else None,
            "original_quantity": r[5],
            "accepted_quantity": r[6]
        })
    return jsonify({"success": True, "data": data})

@app.route('/api/volunteer/wasted-donations')
def volunteer_wasted_donations():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in vol wasted:", e)

    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity,
               fd.time, fd.date_of_donation,
               fd.original_quantity, fd.accepted_quantity
        FROM food_donation fd
        WHERE fd.donation_status = 'Wasted'
        ORDER BY fd.donation_id DESC
    """)
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "donation_id":       r[0],
            "food_type":         r[1],
            "quantity":          r[2],
            "available_until":   str(r[3]) if r[3] else None,
            "date_of_donation":  str(r[4]) if r[4] else None,
            "original_quantity": r[5],
            "accepted_quantity": r[6]
        })
    return jsonify({"success": True, "data": data})

@app.route('/api/donations', methods=['POST'])
def create_donation():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    d = request.get_json()
    if not d:
        return jsonify({"error": "No data received"}), 400
    quantity = d.get('quantity')
    if quantity is None or quantity == "":
        return jsonify({"error": "Quantity is required"}), 400
    try:
        quantity = int(quantity)
    except Exception:
        return jsonify({"error": "Quantity must be a number"}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO food_donation
            (food_type, quantity, original_quantity, accepted_quantity, donation_status,
             time, date_of_donation, donor_id)
            VALUES (%s, %s, %s, 0, %s, %s, %s, %s)
        """, (d.get('food_type'), quantity, quantity, 'Pending',
              d.get('time'), d.get('date_of_donation'), session['user_id']))
        mysql.connection.commit()
        new_id = cur.lastrowid
        return jsonify({"success": True, "message": "Donation submitted", "donation_id": new_id}), 201
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

@app.route('/api/donations/<int:donation_id>', methods=['DELETE'])
def delete_donation(donation_id):
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM food_donation WHERE donation_id=%s AND donor_id=%s AND donation_status='Pending'",
                (donation_id, session['user_id']))
    mysql.connection.commit(); cur.close()
    return jsonify({"success": True})

# ═════════════════════════════════════════════════════════════
# API — DONOR: feedback received from NGOs
# ═════════════════════════════════════════════════════════════

@app.route("/api/donor/feedback-received", methods=["GET"])
def donor_feedback_received():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.feedback_id, f.rating, f.comments, f.hygiene_score, f.feedback_date,
               fd.food_type, n.ngo_name
        FROM feedback f
        JOIN food_donation fd ON f.donation_id = fd.donation_id
        JOIN ngo n ON f.ngo_id = n.ngo_id
        WHERE f.donor_id = %s AND f.from_ngo = TRUE
        ORDER BY f.feedback_date DESC
    """, (session['user_id'],))
    rows = cur.fetchall()
    cur.close()
    data = []
    for r in rows:
        data.append({
            "feedback_id": r[0], "rating": r[1], "comments": r[2],
            "hygiene_score": r[3], "feedback_date": str(r[4]) if r[4] else None,
            "food_type": r[5], "ngo_name": r[6]
        })
    return jsonify({"success": True, "data": data})

# ═════════════════════════════════════════════════════════════
# API — NGO PROFILE
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/profile')
def ngo_profile():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT ngo_name,contact_no,address,capacity,priority_level FROM ngo WHERE ngo_id=%s",
        (session['user_id'],))
    row = cur.fetchone(); cur.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "ngo_name": row[0], "contact_no": row[1],
        "address": row[2], "capacity": row[3], "priority_level": row[4]
    })

@app.route('/api/ngo/update', methods=['POST'])
def update_ngo_profile():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    d = request.get_json()
    if not d:
        return jsonify({"error": "No data received"}), 400
    capacity_raw = d.get('capacity', '')
    try:
        capacity = int(capacity_raw) if str(capacity_raw).strip() != '' else None
    except (ValueError, TypeError):
        capacity = None
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE ngo SET ngo_name=%s,contact_no=%s,address=%s,capacity=%s,priority_level=%s WHERE ngo_id=%s",
            (d.get('ngo_name'), d.get('contact_no'), d.get('address'),
             capacity, d.get('priority_level'), session['user_id']))
        mysql.connection.commit()
        session['user_name'] = d.get('ngo_name')
        return jsonify({"success": True, "message": "Profile updated"})
    except Exception as e:
        print("ERROR update_ngo_profile:", e)
        mysql.connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()

# ═════════════════════════════════════════════════════════════
# API — NGO STATS
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/stats')
def ngo_stats():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    # Expire donations before stats
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in ngo_stats:", e)

    cur.execute("""
        SELECT COUNT(*) FROM delivery dl
        JOIN pickup p ON p.pickup_id = dl.pickup_id
        WHERE dl.ngo_id=%s
    """, (session['user_id'],))
    total = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM delivery dl
        JOIN pickup p ON p.pickup_id = dl.pickup_id
        WHERE dl.ngo_id=%s AND dl.delivery_status='Pending'
    """, (session['user_id'],))
    pending = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM delivery dl
        JOIN pickup p ON p.pickup_id = dl.pickup_id
        WHERE dl.ngo_id=%s AND dl.delivery_status='Delivered'
    """, (session['user_id'],))
    delivered = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donation_status='Pending'")
    available = cur.fetchone()[0]
    cur.close()
    return jsonify({"success": True, "stats": {
        "total": total, "pending": pending, "delivered": delivered, "available": available
    }})

# ═════════════════════════════════════════════════════════════
# API — NGO: available donations feed
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/available-donations')
def ngo_available_donations():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    # Expire donations before showing available ones
    try:
        expire_donations(cur)
        mysql.connection.commit()
    except Exception as e:
        print("Expiry error in available-donations:", e)

    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity,
               fd.original_quantity, fd.accepted_quantity,
               fd.date_of_donation, fd.time,
               d.donor_name, d.contact_no AS donor_contact, d.address AS donor_address,
               d.hygiene_rating AS donor_rating
        FROM food_donation fd
        LEFT JOIN donor d ON d.donor_id = fd.donor_id
        WHERE fd.donation_status = 'Pending'
        ORDER BY fd.donation_id DESC
    """)
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "donation_id": r[0], "food_type": r[1], "quantity": r[2],
            "original_quantity": r[3], "accepted_quantity": r[4],
            "date_of_donation": str(r[5]) if r[5] else None,
            "time": str(r[6]) if r[6] else None,
            "donor_name": r[7], "donor_contact": r[8], "donor_address": r[9],
            "donor_rating": float(r[10]) if r[10] else 0.0
        })
    return jsonify({"success": True, "data": data})

# ═════════════════════════════════════════════════════════════
# API — NGO: ACCEPT a donation (supports PARTIAL quantity)
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/accept-donation', methods=['POST'])
def ngo_accept_donation():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return jsonify({"error": "not logged in"}), 401

    d           = request.get_json()
    donation_id = d.get('donation_id')
    ngo_id      = session['user_id']

    raw_qty = d.get('accepted_qty')
    try:
        accepted_qty = int(raw_qty) if raw_qty is not None and str(raw_qty).strip() != '' else None
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid accepted_qty"}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT donation_id, quantity, original_quantity, accepted_quantity,
                   food_type, time, date_of_donation, donor_id
            FROM food_donation
            WHERE donation_id = %s AND donation_status = 'Pending'
            FOR UPDATE
        """, (donation_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Donation no longer available"}), 400

        orig_id, avail_qty, orig_qty, already_accepted, food_type, fdtime, fddate, donor_id = row

        if accepted_qty is None:
            accepted_qty = avail_qty

        if accepted_qty <= 0 or accepted_qty > avail_qty:
            return jsonify({"error": f"Invalid quantity. Available: {avail_qty}"}), 400

        is_partial = (accepted_qty < avail_qty)
        remaining  = avail_qty - accepted_qty
        effective_original = orig_qty if orig_qty else avail_qty

        if is_partial:
            cur.execute("""
                UPDATE food_donation
                SET quantity = %s,
                    accepted_quantity = COALESCE(accepted_quantity, 0) + %s,
                    original_quantity = %s
                WHERE donation_id = %s
            """, (remaining, accepted_qty, effective_original, donation_id))

            cur.execute("""
                INSERT INTO food_donation
                (food_type, quantity, original_quantity, accepted_quantity, donation_status,
                 time, date_of_donation, donor_id, parent_donation_id)
                VALUES (%s, %s, %s, %s, 'Accepted', %s, %s, %s, %s)
            """, (food_type, accepted_qty, accepted_qty, accepted_qty,
                  fdtime, fddate, donor_id, donation_id))
            child_id = cur.lastrowid
            working_donation_id = child_id
        else:
            cur.execute("""
                UPDATE food_donation
                SET donation_status = 'Accepted',
                    accepted_quantity = %s,
                    original_quantity = %s
                WHERE donation_id = %s
            """, (accepted_qty, effective_original, donation_id))
            working_donation_id = donation_id

        cur.execute("""
            INSERT INTO pickup (time, status, otp_code, donation_id, volunteer_id)
            VALUES (NOW(), 'Pending', NULL, %s, NULL)
        """, (working_donation_id,))
        pickup_id = cur.lastrowid

        cur.execute("""
            INSERT INTO delivery (time, receiver_name, delivery_status, pickup_id, ngo_id)
            VALUES (NOW(), %s, 'Pending', %s, %s)
        """, (session['user_name'], pickup_id, ngo_id))

        mysql.connection.commit()

        msg = (
            f"Partial acceptance: {accepted_qty} accepted, {remaining} still available for other NGOs."
            if is_partial else
            "Donation accepted! Waiting for a volunteer to claim it."
        )
        return jsonify({
            "success":      True,
            "message":      msg,
            "pickup_id":    pickup_id,
            "is_partial":   is_partial,
            "accepted_qty": accepted_qty,
            "remaining_qty": remaining if is_partial else 0
        })

    except Exception as e:
        print("ERROR ngo_accept_donation:", e)
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

# ═════════════════════════════════════════════════════════════
# API — NGO: view accepted orders
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/orders')
def ngo_orders():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT dl.delivery_id, dl.delivery_status, dl.time,
               fd.food_type,  fd.quantity,
               fd.original_quantity, fd.parent_donation_id,
               d.donor_name,  d.address   AS donor_address,
               v.name         AS volunteer_name,
               v.contact_no   AS volunteer_contact,
               v.vehicle_type,
               p.status       AS pickup_status,
               p.otp_code,
               p.pickup_id,
               fd.donation_id,
               d.hygiene_rating AS donor_rating
        FROM delivery dl
        JOIN pickup        p  ON p.pickup_id   = dl.pickup_id
        JOIN food_donation fd ON fd.donation_id = p.donation_id
        JOIN donor         d  ON d.donor_id     = fd.donor_id
        LEFT JOIN volunteer v ON v.volunteer_id = p.volunteer_id
        WHERE dl.ngo_id = %s
        ORDER BY dl.delivery_id DESC
    """, (session['user_id'],))
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "delivery_id": r[0], "delivery_status": r[1],
            "time": str(r[2]) if r[2] else None,
            "food_type": r[3], "quantity": r[4],
            "original_quantity": r[5], "parent_donation_id": r[6],
            "donor_name": r[7], "donor_address": r[8],
            "volunteer_name": r[9], "volunteer_contact": r[10],
            "vehicle_type": r[11], "pickup_status": r[12],
            "otp_code": r[13], "pickup_id": r[14], "donation_id": r[15],
            "donor_rating": float(r[16]) if r[16] else 0.0
        })
    return jsonify({"success": True, "data": data})

# ═════════════════════════════════════════════════════════════
# API — NGO: mark delivery received
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/mark-received', methods=['POST'])
def ngo_mark_received():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    d           = request.get_json()
    delivery_id = d.get('delivery_id')
    pickup_id   = d.get('pickup_id')
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE delivery SET delivery_status='Delivered' WHERE delivery_id=%s AND ngo_id=%s",
        (delivery_id, session['user_id']))
    cur.execute("UPDATE pickup SET status='Delivered' WHERE pickup_id=%s", (pickup_id,))
    cur.execute("""
        UPDATE volunteer SET availability_status='Available'
        WHERE volunteer_id=(SELECT volunteer_id FROM pickup WHERE pickup_id=%s)
    """, (pickup_id,))
    cur.execute("""
        UPDATE food_donation SET donation_status='Completed'
        WHERE donation_id=(SELECT donation_id FROM pickup WHERE pickup_id=%s)
    """, (pickup_id,))
    mysql.connection.commit(); cur.close()
    return jsonify({"success": True, "message": "Marked as received"})

# ═════════════════════════════════════════════════════════════
# API — NGO: submit feedback
# ═════════════════════════════════════════════════════════════

@app.route('/api/ngo/feedback', methods=['POST'])
def submit_ngo_feedback():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json()
    donation_id = data.get('donation_id')
    rating      = data.get('rating', 0)
    comments    = data.get('comments', "")
    hygiene     = data.get('hygiene_score', 0)

    if not donation_id:
        return jsonify({"success": False, "error": "Donation ID missing"}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT donor_id FROM food_donation WHERE donation_id = %s",
            (donation_id,)
        )
        donor = cur.fetchone()
        if not donor:
            return jsonify({"error": "Donation not found"}), 404
        donor_id = donor[0]

        cur.execute("""
            INSERT INTO feedback
            (donation_id, donor_id, ngo_id, rating, comments, hygiene_score, feedback_date, from_ngo)
            VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), TRUE)
        """, (donation_id, donor_id, session['user_id'], rating, comments, hygiene))

        cur.execute("""
            UPDATE donor
            SET hygiene_rating = (
                SELECT AVG(hygiene_score)
                FROM feedback
                WHERE donor_id = %s AND from_ngo = TRUE
            )
            WHERE donor_id = %s
        """, (donor_id, donor_id))

        mysql.connection.commit()
        return jsonify({"success": True, "message": "Feedback submitted"})
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()

# ═════════════════════════════════════════════════════════════
# API — NGO: view feedback given
# ═════════════════════════════════════════════════════════════

@app.route("/api/ngo/feedback-given", methods=["GET"])
def ngo_feedback_given():
    if 'user_id' not in session or session.get('role') != 'ngo':
        return jsonify({"error": "not logged in"}), 401

    ngo_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.rating, f.comments, f.hygiene_score, f.feedback_date,
               d.food_type, dnr.donor_name
        FROM feedback f
        JOIN food_donation d ON f.donation_id = d.donation_id
        JOIN donor dnr ON f.donor_id = dnr.donor_id
        WHERE f.ngo_id = %s AND f.from_ngo = TRUE
        ORDER BY f.feedback_date DESC
    """, (ngo_id,))
    data = cur.fetchall()
    result = []
    for row in data:
        result.append({
            "rating": row[0], "comments": row[1], "hygiene_score": row[2],
            "feedback_date": str(row[3]), "food_type": row[4], "donor_name": row[5]
        })
    return jsonify({"success": True, "data": result})

# ═════════════════════════════════════════════════════════════
# API — VOLUNTEER PROFILE
# ═════════════════════════════════════════════════════════════

@app.route('/api/volunteer/profile')
def volunteer_profile():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT name,contact_no,vehicle_type,availability_status FROM volunteer WHERE volunteer_id=%s",
        (session['user_id'],))
    row = cur.fetchone(); cur.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "name": row[0], "contact_no": row[1],
        "vehicle_type": row[2], "availability_status": row[3]
    })

@app.route('/api/volunteer/update', methods=['POST'])
def update_volunteer_profile():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    d = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE volunteer SET name=%s,contact_no=%s,vehicle_type=%s,availability_status=%s WHERE volunteer_id=%s",
        (d.get('name'), d.get('contact_no'), d.get('vehicle_type'),
         d.get('availability_status'), session['user_id']))
    mysql.connection.commit(); cur.close()
    session['user_name'] = d.get('name')
    return jsonify({"success": True, "message": "Profile updated"})

# ═════════════════════════════════════════════════════════════
# API — VOLUNTEER STATS
# ═════════════════════════════════════════════════════════════

@app.route('/api/volunteer/stats')
def volunteer_stats():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM pickup WHERE volunteer_id=%s", (session['user_id'],))
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pickup WHERE volunteer_id=%s AND status='Pending'", (session['user_id'],))
    pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pickup WHERE volunteer_id=%s AND status='In Progress'", (session['user_id'],))
    in_progress = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pickup WHERE volunteer_id=%s AND status='Delivered'", (session['user_id'],))
    delivered = cur.fetchone()[0]
    cur.close()
    return jsonify({"success": True, "stats": {
        "total": total, "pending": pending, "in_progress": in_progress, "delivered": delivered
    }})

# ═════════════════════════════════════════════════════════════
# API — VOLUNTEER: all pickups visible to this volunteer
# ═════════════════════════════════════════════════════════════

@app.route('/api/volunteer/pickups')
def volunteer_own_pickups():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401

    vid = session['user_id']
    cur = mysql.connection.cursor()

    # 🔹 OPEN PICKUPS (has donor_rating)
    cur.execute("""
        SELECT p.pickup_id,   p.time,         p.status,      p.otp_code,
               fd.food_type,  fd.quantity,
               d.donor_name,  d.contact_no    AS donor_contact,
               d.address      AS donor_address,
               n.ngo_name,    n.address       AS ngo_address,
               n.contact_no   AS ngo_contact,
               dl.delivery_id, dl.delivery_status,
               d.hygiene_rating AS donor_rating
        FROM pickup p
        JOIN food_donation fd ON fd.donation_id = p.donation_id
        JOIN donor         d  ON d.donor_id     = fd.donor_id
        LEFT JOIN delivery dl ON dl.pickup_id   = p.pickup_id
        LEFT JOIN ngo      n  ON n.ngo_id       = dl.ngo_id
        WHERE p.volunteer_id IS NULL AND p.status = 'Pending'
        ORDER BY p.pickup_id DESC
    """)
    open_rows = cur.fetchall()

    # 🔹 MY PICKUPS (NO donor_rating)
    cur.execute("""
        SELECT p.pickup_id,   p.time,         p.status,      p.otp_code,
               fd.food_type,  fd.quantity,
               d.donor_name,  d.contact_no    AS donor_contact,
               d.address      AS donor_address,
               n.ngo_name,    n.address       AS ngo_address,
               n.contact_no   AS ngo_contact,
               dl.delivery_id, dl.delivery_status
        FROM pickup p
        JOIN food_donation fd ON fd.donation_id = p.donation_id
        JOIN donor         d  ON d.donor_id     = fd.donor_id
        LEFT JOIN delivery dl ON dl.pickup_id   = p.pickup_id
        LEFT JOIN ngo      n  ON n.ngo_id       = dl.ngo_id
        WHERE p.volunteer_id = %s
        ORDER BY p.pickup_id DESC
    """, (vid,))
    my_rows = cur.fetchall()

    cur.close()

    # 🔹 FIXED FUNCTION (INSIDE ROUTE)
    def row_to_dict(r, is_mine):
        return {
            "pickup_id":      r[0],
            "time":           str(r[1]) if r[1] else None,
            "status":         r[2],
            "otp_code":       r[3],

            "food_type":      r[4],
            "quantity":       r[5],

            "donor_name":     r[6],
            "donor_contact":  r[7],
            "donor_address":  r[8],

            "ngo_name":       r[9],
            "ngo_address":    r[10],
            "ngo_contact":    r[11],

            "delivery_id":    r[12],
            "delivery_status":r[13],

            # ✅ SAFE FIX (handles both queries)
            "donor_rating":   float(r[14]) if len(r) > 14 and r[14] else 0.0,

            "is_mine":        is_mine
        }

    # 🔹 ALSO INSIDE FUNCTION
    all_mine  = [row_to_dict(r, True)  for r in my_rows]
    available = [row_to_dict(r, False) for r in open_rows]

    return jsonify({
        "success": True,
        "data": all_mine,
        "available": available
    }), 200

# ═════════════════════════════════════════════════════════════
# API — VOLUNTEER: self-claim an open pickup
# ═════════════════════════════════════════════════════════════

@app.route('/api/volunteer/accept-assignment', methods=['POST'])
def volunteer_accept_assignment():
    if 'user_id' not in session or session.get('role') != 'volunteer':
        return jsonify({"error": "not logged in"}), 401

    d = request.get_json()
    pickup_id = d.get('pickup_id')
    vid = session['user_id']

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "SELECT volunteer_id, status FROM pickup WHERE pickup_id = %s FOR UPDATE",
            (pickup_id,)
        )
        row = cur.fetchone()

        if not row:
            return jsonify({"error": "Pickup not found"}), 404

        if row[0] is not None:
            return jsonify({
                "success": False,
                "error": "This assignment was just claimed by another volunteer."
            }), 409

        if row[1] != 'Pending':
            return jsonify({
                "success": False,
                "error": "This assignment is no longer available."
            }), 409

        otp = str(random.randint(1000, 9999))

        cur.execute(
            "UPDATE pickup SET volunteer_id = %s, otp_code = %s WHERE pickup_id = %s",
            (vid, otp, pickup_id)
        )
        cur.execute(
            "UPDATE volunteer SET availability_status = 'Busy' WHERE volunteer_id = %s",
            (vid,)
        )

        mysql.connection.commit()
        return jsonify({
            "success": True,
            "message": "Assignment accepted! Head to the pickup location.",
            "otp": otp,
            "pickup_id": pickup_id
        })

    except Exception as e:
        print("ERROR accept-assignment:", e)
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()

# ═════════════════════════════════════════════════════════════
# API — VOLUNTEER: update pickup status
# ═════════════════════════════════════════════════════════════

@app.route('/api/volunteer/update-pickup', methods=['POST'])
def volunteer_update_pickup():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401

    d = request.get_json()
    pickup_id  = d.get('pickup_id')
    status     = d.get('status')
    otp_input  = d.get('otp')

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT volunteer_id, otp_code FROM pickup WHERE pickup_id=%s",
        (pickup_id,)
    )
    row = cur.fetchone()

    if not row or row[0] != session['user_id']:
        cur.close()
        return jsonify({"error": "Not authorised"}), 403

    if status == 'Delivered':
        stored_otp = str(row[1]).strip() if row[1] is not None else ''
        provided   = str(otp_input).strip() if otp_input is not None else ''
        if not provided or provided != stored_otp:
            cur.close()
            return jsonify({"error": "Invalid OTP. Delivery cannot be confirmed."}), 400

    cur.execute(
        "UPDATE pickup SET status=%s WHERE pickup_id=%s",
        (status, pickup_id)
    )

    if status == 'Delivered':
        cur.execute(
            "UPDATE delivery SET delivery_status='Delivered' WHERE pickup_id=%s",
            (pickup_id,)
        )
        cur.execute(
            "UPDATE volunteer SET availability_status='Available' WHERE volunteer_id=%s",
            (session['user_id'],)
        )
        cur.execute("""
            UPDATE food_donation SET donation_status='Completed'
            WHERE donation_id = (SELECT donation_id FROM pickup WHERE pickup_id=%s)
        """, (pickup_id,))

    mysql.connection.commit()
    cur.close()

    return jsonify({"success": True, "message": f"Pickup marked as {status}"})

# ═════════════════════════════════════════════════════════════
# API — SHARED donations list
# ═════════════════════════════════════════════════════════════

@app.route('/api/donations', methods=['GET'])
def get_donations():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity, fd.donation_status,
               fd.time, fd.date_of_donation, d.donor_name
        FROM food_donation fd
        LEFT JOIN donor d ON d.donor_id = fd.donor_id
        ORDER BY fd.donation_id DESC
    """)
    rows = cur.fetchall(); cur.close()
    data = []
    for r in rows:
        data.append({
            "donation_id": r[0], "food_type": r[1], "quantity": r[2],
            "donation_status": r[3],
            "time": str(r[4]) if r[4] else None,
            "date_of_donation": str(r[5]) if r[5] else None,
            "donor_name": r[6]
        })
    return jsonify({"success": True, "data": data})

# ═════════════════════════════════════════════════════════════
# API — HEALTH / DASHBOARD STATS
# ═════════════════════════════════════════════════════════════

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/dashboard')
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM donor")
    total_donors = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ngo")
    total_ngos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM volunteer WHERE availability_status='Available'")
    available_volunteers = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation")
    total_donations = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donation_status='Pending'")
    pending_donations = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donation_status='Completed'")
    completed_donations = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pickup WHERE status='In Progress'")
    active_pickups = cur.fetchone()[0]
    cur.execute("SELECT ROUND(AVG(rating),1) FROM feedback")
    avg_rating = cur.fetchone()[0] or 0
    cur.close()
    return jsonify({
        "success": True,
        "stats": {
            "total_donors": total_donors, "total_ngos": total_ngos,
            "available_volunteers": available_volunteers,
            "total_donations": total_donations, "pending_donations": pending_donations,
            "completed_donations": completed_donations, "active_pickups": active_pickups,
            "avg_rating": float(avg_rating)
        }
    })

# ═════════════════════════════════════════════════════════════
# RUN
# ═════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 50)
    print("  Food Donation Management System")
    print("  Running at http://127.0.0.1:5000/")
    print("=" * 50)
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
