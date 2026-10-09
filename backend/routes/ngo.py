from flask import Blueprint, request, jsonify
import models

ngo_bp = Blueprint('ngo', __name__)


def ngo_to_dict(row):
    if not row:
        return None
    return {
        "ngo_id": row[0],
        "ngo_name": row[1],
        "contact_no": row[2],
        "address": row[3],
        "capacity": row[4],
        "priority_level": row[5],
        "registration_date": str(row[6]) if row[6] else None
    }


# ── GET all NGOs ────────────────────────────────────────────
@ngo_bp.route('/', methods=['GET'])
def get_ngos():
    rows = models.get_all_ngos()
    return jsonify({"success": True, "data": [ngo_to_dict(r) for r in rows]}), 200


# ── GET single NGO ──────────────────────────────────────────
@ngo_bp.route('/<int:ngo_id>', methods=['GET'])
def get_ngo(ngo_id):
    row = models.get_ngo_by_id(ngo_id)
    if not row:
        return jsonify({"success": False, "message": "NGO not found"}), 404
    return jsonify({"success": True, "data": ngo_to_dict(row)}), 200


# ── CREATE NGO ──────────────────────────────────────────────
@ngo_bp.route('/', methods=['POST'])
def create_ngo():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    if not data.get('ngo_name'):
        return jsonify({"success": False, "message": "'ngo_name' is required"}), 400

    new_id = models.create_ngo(
        ngo_name=data.get('ngo_name'),
        contact_no=data.get('contact_no'),
        address=data.get('address'),
        capacity=data.get('capacity'),
        priority_level=data.get('priority_level', 'Medium')
    )
    return jsonify({"success": True, "message": "NGO created", "ngo_id": new_id}), 201


# ── UPDATE NGO ──────────────────────────────────────────────
@ngo_bp.route('/<int:ngo_id>', methods=['PUT'])
def update_ngo(ngo_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    existing = models.get_ngo_by_id(ngo_id)
    if not existing:
        return jsonify({"success": False, "message": "NGO not found"}), 404

    affected = models.update_ngo(
        ngo_id=ngo_id,
        ngo_name=data.get('ngo_name', existing[1]),
        contact_no=data.get('contact_no', existing[2]),
        address=data.get('address', existing[3]),
        capacity=data.get('capacity', existing[4]),
        priority_level=data.get('priority_level', existing[5])
    )
    return jsonify({"success": True, "message": "NGO updated", "rows_affected": affected}), 200


# ── DELETE NGO ──────────────────────────────────────────────
@ngo_bp.route('/<int:ngo_id>', methods=['DELETE'])
def delete_ngo(ngo_id):
    existing = models.get_ngo_by_id(ngo_id)
    if not existing:
        return jsonify({"success": False, "message": "NGO not found"}), 404

    models.delete_ngo(ngo_id)
    return jsonify({"success": True, "message": "NGO deleted"}), 200


# ── GET deliveries for NGO ──────────────────────────────────
@ngo_bp.route('/<int:ngo_id>/deliveries', methods=['GET'])
def get_ngo_deliveries(ngo_id):
    existing = models.get_ngo_by_id(ngo_id)
    if not existing:
        return jsonify({"success": False, "message": "NGO not found"}), 404

    cur = models.mysql.connection.cursor()
    cur.execute("""
        SELECT d.delivery_id, d.time, d.receiver_name, d.delivery_status,
               d.pickup_id, d.ngo_id
        FROM delivery d WHERE d.ngo_id = %s
        ORDER BY d.delivery_id DESC
    """, (ngo_id,))
    rows = cur.fetchall()
    cur.close()

    deliveries = []
    for r in rows:
        deliveries.append({
            "delivery_id": r[0],
            "time": str(r[1]) if r[1] else None,
            "receiver_name": r[2],
            "delivery_status": r[3],
            "pickup_id": r[4],
            "ngo_id": r[5]
        })
    return jsonify({"success": True, "data": deliveries}), 200


# ── GET feedback for NGO ────────────────────────────────────
@ngo_bp.route('/<int:ngo_id>/feedback', methods=['GET'])
def get_ngo_feedback(ngo_id):
    existing = models.get_ngo_by_id(ngo_id)
    if not existing:
        return jsonify({"success": False, "message": "NGO not found"}), 404

    cur = models.mysql.connection.cursor()
    cur.execute("""
        SELECT f.feedback_id, f.rating, f.hygiene_score, f.comments,
               f.feedback_date, f.donation_id, f.ngo_id
        FROM feedback f WHERE f.ngo_id = %s
        ORDER BY f.feedback_date DESC
    """, (ngo_id,))
    rows = cur.fetchall()
    cur.close()

    feedbacks = []
    for r in rows:
        feedbacks.append({
            "feedback_id": r[0],
            "rating": r[1],
            "hygiene_score": r[2],
            "comments": r[3],
            "feedback_date": str(r[4]) if r[4] else None,
            "donation_id": r[5],
            "ngo_id": r[6]
        })
    return jsonify({"success": True, "data": feedbacks}), 200