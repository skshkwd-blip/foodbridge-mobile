from flask import Blueprint, request, jsonify
import models

donor_bp = Blueprint('donor', __name__)


def donor_to_dict(row):
    if not row:
        return None
    return {
        "donor_id": row[0],
        "donor_name": row[1],
        "donor_type": row[2],
        "contact_no": row[3],
        "address": row[4],
        "hygiene_rating": float(row[5]) if row[5] else None,
        "registration_date": str(row[6]) if row[6] else None
    }


# ── GET all donors ──────────────────────────────────────────
@donor_bp.route('/', methods=['GET'])
def get_donors():
    rows = models.get_all_donors()
    return jsonify({"success": True, "data": [donor_to_dict(r) for r in rows]}), 200


# ── GET single donor ────────────────────────────────────────
@donor_bp.route('/<int:donor_id>', methods=['GET'])
def get_donor(donor_id):
    row = models.get_donor_by_id(donor_id)
    if not row:
        return jsonify({"success": False, "message": "Donor not found"}), 404
    return jsonify({"success": True, "data": donor_to_dict(row)}), 200


# ── CREATE donor ────────────────────────────────────────────
@donor_bp.route('/', methods=['POST'])
def create_donor():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    required = ['donor_name']
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"'{field}' is required"}), 400

    new_id = models.create_donor(
        donor_name=data.get('donor_name'),
        donor_type=data.get('donor_type', 'Individual'),
        contact_no=data.get('contact_no'),
        address=data.get('address'),
        hygiene_rating=data.get('hygiene_rating')
    )
    return jsonify({"success": True, "message": "Donor created", "donor_id": new_id}), 201


# ── UPDATE donor ────────────────────────────────────────────
@donor_bp.route('/<int:donor_id>', methods=['PUT'])
def update_donor(donor_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    existing = models.get_donor_by_id(donor_id)
    if not existing:
        return jsonify({"success": False, "message": "Donor not found"}), 404

    affected = models.update_donor(
        donor_id=donor_id,
        donor_name=data.get('donor_name', existing[1]),
        donor_type=data.get('donor_type', existing[2]),
        contact_no=data.get('contact_no', existing[3]),
        address=data.get('address', existing[4]),
        hygiene_rating=data.get('hygiene_rating', existing[5])
    )
    return jsonify({"success": True, "message": "Donor updated", "rows_affected": affected}), 200


# ── DELETE donor ────────────────────────────────────────────
@donor_bp.route('/<int:donor_id>', methods=['DELETE'])
def delete_donor(donor_id):
    existing = models.get_donor_by_id(donor_id)
    if not existing:
        return jsonify({"success": False, "message": "Donor not found"}), 404

    models.delete_donor(donor_id)
    return jsonify({"success": True, "message": "Donor deleted"}), 200


# ── GET donations by donor ──────────────────────────────────
@donor_bp.route('/<int:donor_id>/donations', methods=['GET'])
def get_donor_donations(donor_id):
    existing = models.get_donor_by_id(donor_id)
    if not existing:
        return jsonify({"success": False, "message": "Donor not found"}), 404

    cur = models.mysql.connection.cursor()
    cur.execute("""
        SELECT donation_id, food_type, quantity, donation_status,
               time, date_of_donation, donor_id
        FROM food_donation WHERE donor_id = %s
        ORDER BY date_of_donation DESC
    """, (donor_id,))
    rows = cur.fetchall()
    cur.close()

    donations = []
    for r in rows:
        donations.append({
            "donation_id": r[0],
            "food_type": r[1],
            "quantity": r[2],
            "donation_status": r[3],
            "time": str(r[4]) if r[4] else None,
            "date_of_donation": str(r[5]) if r[5] else None,
            "donor_id": r[6]
        })
    return jsonify({"success": True, "data": donations}), 200


# ── CREATE food donation ────────────────────────────────────
@donor_bp.route('/<int:donor_id>/donations', methods=['POST'])
def create_donation_for_donor(donor_id):
    existing = models.get_donor_by_id(donor_id)
    if not existing:
        return jsonify({"success": False, "message": "Donor not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    new_id = models.create_food_donation(
        food_type=data.get('food_type'),
        quantity=data.get('quantity'),
        donation_status=data.get('donation_status', 'Pending'),
        time=data.get('time'),
        date_of_donation=data.get('date_of_donation'),
        donor_id=donor_id
    )
    return jsonify({"success": True, "message": "Donation created", "donation_id": new_id}), 201