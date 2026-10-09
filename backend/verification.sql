-- Run ONCE on your existing food_db (PythonAnywhere: Databases tab -> your database -> Mysql console).
-- If a line says "Duplicate column name", that column is already there: skip it.

ALTER TABLE donor
  ADD COLUMN fssai_no VARCHAR(14),
  ADD COLUMN license_file VARCHAR(120),
  ADD COLUMN verify_status VARCHAR(10) DEFAULT 'None';

ALTER TABLE ngo
  ADD COLUMN darpan_id VARCHAR(40),
  ADD COLUMN contact_person VARCHAR(100),
  ADD COLUMN reg_file VARCHAR(120),
  ADD COLUMN verify_status VARCHAR(10) DEFAULT 'None';

ALTER TABLE volunteer
  ADD COLUMN vehicle_no VARCHAR(20),
  ADD COLUMN emergency_contact VARCHAR(15),
  ADD COLUMN id_file VARCHAR(120),
  ADD COLUMN selfie_file VARCHAR(120),
  ADD COLUMN verify_status VARCHAR(10) DEFAULT 'None';

ALTER TABLE food_donation
  ADD COLUMN cooked_at VARCHAR(5),
  ADD COLUMN is_veg TINYINT(1) DEFAULT 1;

-- Accounts that already exist would be locked out until verified.
-- To let your test accounts keep working, uncomment these:
-- UPDATE ngo SET verify_status='Verified';
-- UPDATE volunteer SET verify_status='Verified';
