"""Verification features for FoodBridge: donor FSSAI licence, NGO registration,
volunteer ID, plus a small admin web page to approve or reject.

Setup (in app.py, AFTER init_mobile_auth(app)):
    from verification import init_verification
    init_verification(app)
Run verification.sql once. On PythonAnywhere set env var ADMIN_PASSWORD (WSGI file).
"""
import hmac
import json
import os

from flask import jsonify, redirect, render_template_string, request, send_file, session
from werkzeug.utils import secure_filename

from db import mysql

TABLE = {"donor": ("donor", "donor_id", "donor_name"),
         "ngo": ("ngo", "ngo_id", "ngo_name"),
         "volunteer": ("volunteer", "volunteer_id", "name")}
# role: (text fields, file fields). Names are also the DB column names.
FIELDS = {"donor": (["fssai_no"], ["license_file"]),
          "ngo": (["darpan_id", "contact_person"], ["reg_file"]),
          "volunteer": (["vehicle_no", "emergency_contact"], ["id_file", "selfie_file"])}
GATED = {("POST", "/api/ngo/accept-donation"): "ngo", ("POST", "/api/volunteer/accept-assignment"): "volunteer"}
UPLOADS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private_uploads")  # never served publicly

PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1"><title>FoodBridge admin</title>
<style>body{font-family:sans-serif;max-width:720px;margin:20px auto;padding:0 12px}.c{border:1px solid #ddd;border-radius:8px;padding:12px;margin:12px 0}button{padding:8px 14px;margin-right:6px}</style>
<h2>Pending verifications ({{rows|length}})</h2>
{% for r in rows %}<div class=c><b>{{r.name}}</b> ({{r.role}})
{% for k,v in r.texts %}<div>{{k}}: {{v}}</div>{% endfor %}
{% for k,v in r.files %}{% if v %}<div><a target=_blank href="/admin/file/{{v}}">View {{k}}</a></div>{% endif %}{% endfor %}
<form method=post action="/admin/decide"><input type=hidden name=role value="{{r.role}}"><input type=hidden name=id value="{{r.id}}">
<button name=d value=Verified>Approve</button><button name=d value=Rejected>Reject</button></form></div>
{% else %}<p>Nothing waiting.</p>{% endfor %}"""
LOGIN = "<form method=post style='margin:60px auto;max-width:300px;font-family:sans-serif'><h3>Admin</h3><input type=password name=pw placeholder=Password style='width:100%;padding:8px'><button style='margin-top:8px;padding:8px'>Log in</button></form>"


def q(sql, args=(), one=False, commit=False):
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    if commit:
        mysql.connection.commit()
        out = cur.lastrowid
    else:
        out = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return out


def init_verification(app):
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    def verified(table, name_col, name):
        return bool(name) and bool(q(f"SELECT 1 FROM {table} WHERE LOWER(TRIM({name_col}))=LOWER(TRIM(%s)) "
                                     "AND verify_status='Verified'", (name,), one=True))

    # NGOs and volunteers must be verified before accepting food or taking pickups
    @app.before_request
    def gate():
        role = GATED.get((request.method, request.path))
        if role and session.get("role") == role:
            t, idc, _ = TABLE[role]
            row = q(f"SELECT verify_status FROM {t} WHERE {idc}=%s", (session["user_id"],), one=True)
            if not row or row[0] != "Verified":
                return jsonify(error="Your account must be verified first. Open the Verify tab."), 403

    # Adds badges and food details to existing responses so your old routes stay untouched
    @app.after_request
    def enrich(resp):
        if request.method == "POST" and request.path == "/api/donations" and resp.status_code == 201:
            d = request.get_json(silent=True) or {}
            q("UPDATE food_donation SET cooked_at=%s, is_veg=%s WHERE donation_id=%s",
              (d.get("cooked_at") or None, 0 if d.get("is_veg") is False else 1, resp.get_json().get("donation_id")), commit=True)
        if request.path in ("/api/ngo/available-donations", "/api/donor/donations") and resp.status_code == 200:
            body = resp.get_json(silent=True)
            for r in (body or {}).get("data", []):
                if r.get("donor_name"):
                    r["donor_verified"] = verified("donor", "donor_name", r["donor_name"])
                info = q("SELECT cooked_at, is_veg FROM food_donation WHERE donation_id=%s", (r["donation_id"],), one=True)
                r["cooked_at"], r["is_veg"] = (info[0], info[1]) if info else (None, 1)
                if r.get("volunteer_name"):
                    r["volunteer_verified"] = verified("volunteer", "name", r["volunteer_name"])
                    v = q("SELECT vehicle_no FROM volunteer WHERE LOWER(TRIM(name))=LOWER(TRIM(%s))", (r["volunteer_name"],), one=True)
                    r["volunteer_vehicle"] = v[0] if v else None
            if body:
                resp.set_data(json.dumps(body))
        return resp

    @app.get("/api/verify/me")
    def verify_me():
        role = session.get("role")
        if role not in TABLE:
            return jsonify(error="not logged in"), 401
        t, idc, _ = TABLE[role]
        texts, files = FIELDS[role]
        cols = texts + files + ["verify_status"]
        d = dict(zip(cols, q(f"SELECT {','.join(cols)} FROM {t} WHERE {idc}=%s", (session["user_id"],), one=True)))
        d["status"] = d.pop("verify_status") or "None"
        return jsonify({k: (bool(v) if k in files else v) for k, v in d.items()})

    @app.post("/api/verify/submit")
    def verify_submit():
        role = session.get("role")
        if role not in TABLE:
            return jsonify(error="not logged in"), 401
        t, idc, _ = TABLE[role]
        texts, files = FIELDS[role]
        vals = {k: request.form.get(k, "").strip() for k in texts}
        if role == "donor" and not (vals["fssai_no"].isdigit() and len(vals["fssai_no"]) == 14):
            return jsonify(error="FSSAI number must be exactly 14 digits"), 400
        if role == "ngo" and not (vals["darpan_id"] and vals["contact_person"]):
            return jsonify(error="NGO Darpan ID and contact person are required"), 400
        if role == "volunteer" and not (vals["emergency_contact"].isdigit() and len(vals["emergency_contact"]) >= 10):
            return jsonify(error="Enter a valid emergency contact number"), 400
        os.makedirs(UPLOADS, exist_ok=True)
        for k in files:
            f = request.files.get(k)
            ext = os.path.splitext(secure_filename(f.filename or ""))[1].lower() if f else ""
            if ext not in (".jpg", ".jpeg", ".png", ".pdf"):
                return jsonify(error="Please attach every photo (jpg or png)"), 400
            vals[k] = f"{role}_{session['user_id']}_{k}{ext}"
            f.save(os.path.join(UPLOADS, vals[k]))
        sets = ",".join(f"{k}=%s" for k in vals)
        q(f"UPDATE {t} SET {sets}, verify_status='Pending' WHERE {idc}=%s", (*vals.values(), session["user_id"]), commit=True)
        return jsonify(success=True)

    # A donor can see the selfie of the volunteer assigned to their own donation
    @app.get("/api/verify/photo/<int:did>")
    def volunteer_photo(did):
        row = q("""SELECT v.selfie_file FROM food_donation fd JOIN pickup p ON p.donation_id=fd.donation_id
                   JOIN volunteer v ON v.volunteer_id=p.volunteer_id WHERE fd.donation_id=%s AND fd.donor_id=%s""",
                (did, session.get("user_id")), one=True) if session.get("role") == "donor" else None
        if not row or not row[0]:
            return jsonify(error="No photo"), 404
        return send_file(os.path.join(UPLOADS, row[0]))

    # ---- admin web page ----
    pw = os.environ.get("ADMIN_PASSWORD", "")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST" and pw and hmac.compare_digest(request.form.get("pw", ""), pw):
            session["is_admin"] = True
            return redirect("/admin")
        return LOGIN

    @app.get("/admin")
    def admin_home():
        if not session.get("is_admin"):
            return redirect("/admin/login")
        rows = []
        for role, (t, idc, namec) in TABLE.items():
            texts, files = FIELDS[role]
            for r in q(f"SELECT {idc},{namec},{','.join(texts + files)} FROM {t} WHERE verify_status='Pending'"):
                n = len(texts)
                rows.append(dict(role=role, id=r[0], name=r[1], texts=list(zip(texts, r[2:2 + n])), files=list(zip(files, r[2 + n:]))))
        return render_template_string(PAGE, rows=rows)

    @app.get("/admin/file/<fname>")
    def admin_file(fname):
        if not session.get("is_admin"):
            return redirect("/admin/login")
        return send_file(os.path.join(UPLOADS, secure_filename(fname)))

    @app.post("/admin/decide")
    def admin_decide():
        role, decision = request.form.get("role"), request.form.get("d")
        if not session.get("is_admin") or role not in TABLE or decision not in ("Verified", "Rejected"):
            return redirect("/admin/login")
        t, idc, _ = TABLE[role]
        q(f"UPDATE {t} SET verify_status=%s WHERE {idc}=%s", (decision, request.form.get("id")), commit=True)
        return redirect("/admin")
