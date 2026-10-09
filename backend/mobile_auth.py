"""Token login for the FoodBridge mobile app.

The existing /api/... routes read Flask's `session`. A before_request hook fills
`session` from the app's bearer token, so every existing route works for the app
unchanged. Wired in from app.py: init_mobile_auth(app)
"""
import datetime

import jwt
from flask import jsonify, request, session

from db import mysql
from passwords import check_pw, hash_pw

FIND = {
    "donor": "SELECT donor_id, donor_name, password FROM donor WHERE LOWER(TRIM(donor_name))=LOWER(TRIM(%s))",
    "ngo": "SELECT ngo_id, ngo_name, password FROM ngo WHERE LOWER(TRIM(ngo_name))=LOWER(TRIM(%s))",
    "volunteer": "SELECT volunteer_id, name, password FROM volunteer WHERE LOWER(TRIM(name))=LOWER(TRIM(%s))",
}


def init_mobile_auth(app):
    def reply(uid, name, role, code=200):
        exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)
        token = jwt.encode({"id": uid, "name": name, "role": role, "exp": exp}, app.secret_key, algorithm="HS256")
        return jsonify(token=token, user={"id": uid, "name": name, "role": role}), code

    @app.before_request
    def bearer_to_session():
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return
        try:
            p = jwt.decode(header[7:], app.secret_key, algorithms=["HS256"])
            session["user_id"], session["user_name"], session["role"] = p["id"], p["name"], p["role"]
        except jwt.PyJWTError:
            session.clear()

    @app.post("/api/auth/login")
    def mobile_login():
        d = request.get_json(force=True, silent=True) or {}
        role, name = str(d.get("role", "")).lower(), str(d.get("name", "")).strip()
        if role not in FIND or not name:
            return jsonify(error="Enter your name and choose a role"), 400
        cur = mysql.connection.cursor()
        cur.execute(FIND[role], (name,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify(error="No account with that name"), 401
        if not check_pw(row[2], d.get("password", "")):
            return jsonify(error="Incorrect password"), 401
        return reply(row[0], row[1], role)

    @app.post("/api/auth/signup")
    def mobile_signup():
        d = request.get_json(force=True, silent=True) or {}
        role, name = str(d.get("role", "")).lower(), str(d.get("name", "")).strip()
        email, mobile = str(d.get("email", "")).strip(), str(d.get("mobile", "")).strip()
        password = str(d.get("password", "")).strip()
        if role not in FIND or not name or not email or len(password) < 6:
            return jsonify(error="Name, email, role and a password of at least 6 characters are required"), 400
        cur = mysql.connection.cursor()
        cur.execute(FIND[role], (name,))
        if cur.fetchone():
            cur.close()
            return jsonify(error="That name is already registered"), 409
        pw = hash_pw(password)
        if role == "donor":
            cur.execute("INSERT INTO donor (donor_name,donor_type,contact_no,address,hygiene_rating,password,role,email) "
                        "VALUES (%s,'Individual',%s,'',0,%s,'donor',%s)", (name, mobile, pw, email))
        elif role == "volunteer":
            cur.execute("INSERT INTO volunteer (name,contact_no,vehicle_type,availability_status,password) "
                        "VALUES (%s,%s,'None','Available',%s)", (name, mobile, pw))
        else:
            cur.execute("INSERT INTO ngo (ngo_name,contact_no,address,capacity,priority_level,password) "
                        "VALUES (%s,%s,%s,0,'Medium',%s)", (name, mobile, d.get("address", ""), pw))
        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.close()
        return reply(new_id, name, role, 201)
