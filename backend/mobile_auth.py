"""Bearer-token login for the FoodBridge mobile app.

Your existing /api/... routes read Flask's `session`. This hook fills `session`
from a token, so every existing route works for the app with no other changes.

Setup:  pip install pyjwt
In app.py, right after `mysql.init_app(app)` add:
    from mobile_auth import init_mobile_auth
    init_mobile_auth(app)
"""
import datetime

import jwt
from flask import jsonify, request, session

from db import mysql

FIND = {
    "donor": "SELECT donor_id, donor_name, password FROM donor WHERE LOWER(TRIM(donor_name))=LOWER(TRIM(%s))",
    "ngo": "SELECT ngo_id, ngo_name, NULL FROM ngo WHERE LOWER(TRIM(ngo_name))=LOWER(TRIM(%s))",
    "volunteer": "SELECT volunteer_id, name, NULL FROM volunteer WHERE LOWER(TRIM(name))=LOWER(TRIM(%s))",
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
        d = request.get_json(force=True)
        role, name = str(d.get("role", "")).lower(), str(d.get("name", "")).strip()
        if role not in FIND or not name:
            return jsonify(error="Enter your name and choose a role"), 400
        cur = mysql.connection.cursor()
        cur.execute(FIND[role], (name,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify(error="No account with that name"), 401
        if role == "donor" and str(row[2]).strip() != str(d.get("password", "")).strip():
            return jsonify(error="Incorrect password"), 401
        return reply(row[0], row[1], role)

    @app.post("/api/auth/signup")
    def mobile_signup():
        d = request.get_json(force=True)
        role, name = str(d.get("role", "")).lower(), str(d.get("name", "")).strip()
        email, mobile = str(d.get("email", "")).strip(), str(d.get("mobile", "")).strip()
        password = str(d.get("password", "")).strip()
        if role not in FIND or not name or not email or not password:
            return jsonify(error="Name, email, password and role are required"), 400
        cur = mysql.connection.cursor()
        cur.execute(FIND[role], (name,))
        if cur.fetchone():
            cur.close()
            return jsonify(error="That name is already registered"), 409
        if role == "donor":
            cur.execute("INSERT INTO donor (donor_name,donor_type,contact_no,address,hygiene_rating,password,role,email) "
                        "VALUES (%s,'Individual',%s,'',0,%s,'donor',%s)", (name, mobile, password, email))
        elif role == "volunteer":
            cur.execute("INSERT INTO volunteer (name,contact_no,vehicle_type,availability_status) "
                        "VALUES (%s,%s,'None','Available')", (name, mobile))
        else:
            cur.execute("INSERT INTO ngo (ngo_name,contact_no,address,capacity,priority_level) "
                        "VALUES (%s,%s,%s,0,'Medium')", (name, mobile, d.get("address", "")))
        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.close()
        return reply(new_id, name, role, 201)
