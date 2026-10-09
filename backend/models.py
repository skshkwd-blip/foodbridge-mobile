from db import mysql

# ─────────────────────────────────────────────
# DONOR MODELS
# ─────────────────────────────────────────────

def get_all_donors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM donor ORDER BY registration_date DESC")
    rows = cur.fetchall()
    cur.close()
    return rows

def get_donor_by_id(donor_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM donor WHERE donor_id = %s", (donor_id,))
    row = cur.fetchone()
    cur.close()
    return row

def create_donor(donor_name, donor_type, contact_no, address, hygiene_rating):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO donor (donor_name, donor_type, contact_no, address, hygiene_rating)
           VALUES (%s, %s, %s, %s, %s)""",
        (donor_name, donor_type, contact_no, address, hygiene_rating)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

def update_donor(donor_id, donor_name, donor_type, contact_no, address, hygiene_rating):
    cur = mysql.connection.cursor()
    cur.execute(
        """UPDATE donor SET donor_name=%s, donor_type=%s, contact_no=%s,
           address=%s, hygiene_rating=%s WHERE donor_id=%s""",
        (donor_name, donor_type, contact_no, address, hygiene_rating, donor_id)
    )
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

def delete_donor(donor_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM donor WHERE donor_id = %s", (donor_id,))
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

# ─────────────────────────────────────────────
# NGO MODELS
# ─────────────────────────────────────────────

def get_all_ngos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM ngo ORDER BY priority_level, ngo_name")
    rows = cur.fetchall()
    cur.close()
    return rows

def get_ngo_by_id(ngo_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM ngo WHERE ngo_id = %s", (ngo_id,))
    row = cur.fetchone()
    cur.close()
    return row

def create_ngo(ngo_name, contact_no, address, capacity, priority_level):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO ngo (ngo_name, contact_no, address, capacity, priority_level)
           VALUES (%s, %s, %s, %s, %s)""",
        (ngo_name, contact_no, address, capacity, priority_level)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

def update_ngo(ngo_id, ngo_name, contact_no, address, capacity, priority_level):
    cur = mysql.connection.cursor()
    cur.execute(
        """UPDATE ngo SET ngo_name=%s, contact_no=%s, address=%s,
           capacity=%s, priority_level=%s WHERE ngo_id=%s""",
        (ngo_name, contact_no, address, capacity, priority_level, ngo_id)
    )
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

def delete_ngo(ngo_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM ngo WHERE ngo_id = %s", (ngo_id,))
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

# ─────────────────────────────────────────────
# VOLUNTEER MODELS
# ─────────────────────────────────────────────

def get_all_volunteers():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM volunteer ORDER BY availability_status, name")
    rows = cur.fetchall()
    cur.close()
    return rows

def get_volunteer_by_id(volunteer_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM volunteer WHERE volunteer_id = %s", (volunteer_id,))
    row = cur.fetchone()
    cur.close()
    return row

def create_volunteer(name, contact_no, vehicle_type, availability_status):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO volunteer (name, contact_no, vehicle_type, availability_status)
           VALUES (%s, %s, %s, %s)""",
        (name, contact_no, vehicle_type, availability_status)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

def update_volunteer(volunteer_id, name, contact_no, vehicle_type, availability_status):
    cur = mysql.connection.cursor()
    cur.execute(
        """UPDATE volunteer SET name=%s, contact_no=%s, vehicle_type=%s,
           availability_status=%s WHERE volunteer_id=%s""",
        (name, contact_no, vehicle_type, availability_status, volunteer_id)
    )
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

def delete_volunteer(volunteer_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM volunteer WHERE volunteer_id = %s", (volunteer_id,))
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

# ─────────────────────────────────────────────
# FOOD DONATION MODELS
# ─────────────────────────────────────────────

def get_all_food_donations():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT fd.*, d.donor_name
        FROM food_donation fd
        LEFT JOIN donor d ON fd.donor_id = d.donor_id
        ORDER BY fd.date_of_donation DESC, fd.time DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def get_food_donation_by_id(donation_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT fd.*, d.donor_name
        FROM food_donation fd
        LEFT JOIN donor d ON fd.donor_id = d.donor_id
        WHERE fd.donation_id = %s
    """, (donation_id,))
    row = cur.fetchone()
    cur.close()
    return row

def create_food_donation(food_type, quantity, donation_status, time, date_of_donation, donor_id):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO food_donation (food_type, quantity, donation_status, time, date_of_donation, donor_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (food_type, quantity, donation_status, time, date_of_donation, donor_id)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

def update_food_donation_status(donation_id, donation_status):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE food_donation SET donation_status=%s WHERE donation_id=%s",
        (donation_status, donation_id)
    )
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

def delete_food_donation(donation_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM food_donation WHERE donation_id = %s", (donation_id,))
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

# ─────────────────────────────────────────────
# PICKUP MODELS
# ─────────────────────────────────────────────

def get_all_pickups():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, fd.food_type, fd.quantity, v.name AS volunteer_name
        FROM pickup p
        LEFT JOIN food_donation fd ON p.donation_id = fd.donation_id
        LEFT JOIN volunteer v ON p.volunteer_id = v.volunteer_id
        ORDER BY p.pickup_id DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def create_pickup(time, status, otp_code, donation_id, volunteer_id):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO pickup (time, status, otp_code, donation_id, volunteer_id)
           VALUES (%s, %s, %s, %s, %s)""",
        (time, status, otp_code, donation_id, volunteer_id)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

def update_pickup_status(pickup_id, status):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE pickup SET status=%s WHERE pickup_id=%s", (status, pickup_id))
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

# ─────────────────────────────────────────────
# DELIVERY MODELS
# ─────────────────────────────────────────────

def get_all_deliveries():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT dl.*, n.ngo_name, p.status AS pickup_status
        FROM delivery dl
        LEFT JOIN ngo n ON dl.ngo_id = n.ngo_id
        LEFT JOIN pickup p ON dl.pickup_id = p.pickup_id
        ORDER BY dl.delivery_id DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def create_delivery(time, receiver_name, delivery_status, pickup_id, ngo_id):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO delivery (time, receiver_name, delivery_status, pickup_id, ngo_id)
           VALUES (%s, %s, %s, %s, %s)""",
        (time, receiver_name, delivery_status, pickup_id, ngo_id)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

def update_delivery_status(delivery_id, delivery_status):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE delivery SET delivery_status=%s WHERE delivery_id=%s",
        (delivery_status, delivery_id)
    )
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()
    return affected

# ─────────────────────────────────────────────
# FEEDBACK MODELS
# ─────────────────────────────────────────────

def get_all_feedback():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.*, n.ngo_name, fd.food_type
        FROM feedback f
        LEFT JOIN ngo n ON f.ngo_id = n.ngo_id
        LEFT JOIN food_donation fd ON f.donation_id = fd.donation_id
        ORDER BY f.feedback_date DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return rows

def create_feedback(rating, hygiene_score, comments, feedback_date, donation_id, ngo_id):
    cur = mysql.connection.cursor()
    cur.execute(
        """INSERT INTO feedback (rating, hygiene_score, comments, feedback_date, donation_id, ngo_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (rating, hygiene_score, comments, feedback_date, donation_id, ngo_id)
    )
    mysql.connection.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id

# ─────────────────────────────────────────────
# DASHBOARD / STATS MODELS
# ─────────────────────────────────────────────

def get_dashboard_stats():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM donor")
    total_donors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM ngo")
    total_ngos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM volunteer WHERE availability_status = 'Available'")
    available_volunteers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM food_donation")
    total_donations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donation_status = 'Pending'")
    pending_donations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM food_donation WHERE donation_status = 'Completed'")
    completed_donations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pickup WHERE status = 'In Progress'")
    active_pickups = cur.fetchone()[0]

    cur.execute("SELECT ROUND(AVG(rating), 1) FROM feedback")
    avg_rating = cur.fetchone()[0] or 0

    cur.close()
    return {
        "total_donors": total_donors,
        "total_ngos": total_ngos,
        "available_volunteers": available_volunteers,
        "total_donations": total_donations,
        "pending_donations": pending_donations,
        "completed_donations": completed_donations,
        "active_pickups": active_pickups,
        "avg_rating": float(avg_rating)
    }

def get_recent_donations(limit=5):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT fd.donation_id, fd.food_type, fd.quantity, fd.donation_status,
               fd.date_of_donation, d.donor_name
        FROM food_donation fd
        LEFT JOIN donor d ON fd.donor_id = d.donor_id
        ORDER BY fd.date_of_donation DESC, fd.time DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows
