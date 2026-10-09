from flask import Blueprint, request, jsonify
import models

volunteer_bp = Blueprint('volunteer', __name__)


def volunteer_to_dict(row):
    if not row:
        return None
    return {
        "volunteer_id": row[0],
        "name": row[1],
        "contact_no": row[2],
        "vehicle_type": row[3],
        "availability_status": row[4],
        "registration_date": str(row[5]) if row[5] else None
    }


# ── GET all volunteers ──────────────────────────────────────
@volunteer_bp.route('/', methods=['GET'])
def get_volunteers():
    rows = models.get_all_volunteers()
    return jsonify({"success": True, "data": [volunteer_to_dict(r) for r in rows]}), 200


# ── GET single volunteer ────────────────────────────────────
@volunteer_bp.route('/<int:volunteer_id>', methods=['GET'])
def get_volunteer(volunteer_id):
    row = models.get_volunteer_by_id(volunteer_id)
    if not row:
        return jsonify({"success": False, "message": "Volunteer not found"}), 404
    return jsonify({"success": True, "data": volunteer_to_dict(row)}), 200


# ── CREATE volunteer ────────────────────────────────────────
@volunteer_bp.route('/', methods=['POST'])
def create_volunteer():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    if not data.get('name'):
        return jsonify({"success": False, "message": "'name' is required"}), 400

    new_id = models.create_volunteer(
        name=data.get('name'),
        contact_no=data.get('contact_no'),
        vehicle_type=data.get('vehicle_type'),
        availability_status=data.get('availability_status', 'Available')
    )
    return jsonify({"success": True, "message": "Volunteer registered", "volunteer_id": new_id}), 201


# ── UPDATE volunteer ────────────────────────────────────────
@volunteer_bp.route('/<int:volunteer_id>', methods=['PUT'])
def update_volunteer(volunteer_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    existing = models.get_volunteer_by_id(volunteer_id)
    if not existing:
        return jsonify({"success": False, "message": "Volunteer not found"}), 404

    affected = models.update_volunteer(
        volunteer_id=volunteer_id,
        name=data.get('name', existing[1]),
        contact_no=data.get('contact_no', existing[2]),
        vehicle_type=data.get('vehicle_type', existing[3]),
        availability_status=data.get('availability_status', existing[4])
    )
    return jsonify({"success": True, "message": "Volunteer updated", "rows_affected": affected}), 200


# ── UPDATE availability status only ────────────────────────
@volunteer_bp.route('/<int:volunteer_id>/status', methods=['PATCH'])
def update_availability(volunteer_id):
    data = request.get_json()
    if not data or 'availability_status' not in data:
        return jsonify({"success": False, "message": "'availability_status' is required"}), 400

    existing = models.get_volunteer_by_id(volunteer_id)
    if not existing:
        return jsonify({"success": False, "message": "Volunteer not found"}), 404

    allowed = ['Available', 'Busy', 'Inactive']
    if data['availability_status'] not in allowed:
        return jsonify({
            "success": False,
            "message": f"Status must be one of: {', '.join(allowed)}"
        }), 400

    models.update_volunteer(
        volunteer_id=volunteer_id,
        name=existing[1],
        contact_no=existing[2],
        vehicle_type=existing[3],
        availability_status=data['availability_status']
    )
    return jsonify({"success": True, "message": "Availability updated"}), 200


# ── DELETE volunteer ────────────────────────────────────────
@volunteer_bp.route('/<int:volunteer_id>', methods=['DELETE'])
def delete_volunteer(volunteer_id):
    existing = models.get_volunteer_by_id(volunteer_id)
    if not existing:
        return jsonify({"success": False, "message": "Volunteer not found"}), 404

    models.delete_volunteer(volunteer_id)
    return jsonify({"success": True, "message": "Volunteer deleted"}), 200


# ── GET pickups assigned to volunteer ──────────────────────
@volunteer_bp.route('/<int:volunteer_id>/pickups', methods=['GET'])
def get_volunteer_pickups(volunteer_id):
    existing = models.get_volunteer_by_id(volunteer_id)
    if not existing:
        return jsonify({"success": False, "message": "Volunteer not found"}), 404

    cur = models.mysql.connection.cursor()
    cur.execute("""
        SELECT p.pickup_id, p.time, p.status, p.otp_code,
               p.donation_id, p.volunteer_id,
               fd.food_type, fd.quantity
        FROM pickup p
        LEFT JOIN food_donation fd ON p.donation_id = fd.donation_id
        WHERE p.volunteer_id = %s
        ORDER BY p.pickup_id DESC
    """, (volunteer_id,))
    rows = cur.fetchall()
    cur.close()

    pickups = []
    for r in rows:
        pickups.append({
            "pickup_id": r[0],
            "time": str(r[1]) if r[1] else None,
            "status": r[2],
            "otp_code": r[3],
            "donation_id": r[4],
            "volunteer_id": r[5],
            "food_type": r[6],
            "quantity": r[7]
        })
    return jsonify({"success": True, "data": pickups}), 200