-- ONLY for a database you created BEFORE the mobile app (for example your old local food_db).
-- A brand-new database (Aiven, Render) does NOT need this: the backend creates everything itself.
-- Run once. If a line says "Duplicate column name", that column already exists: skip it.

ALTER TABLE donor MODIFY password VARCHAR(255);
ALTER TABLE donor
  ADD COLUMN fssai_no VARCHAR(14),
  ADD COLUMN license_file VARCHAR(120),
  ADD COLUMN verify_status VARCHAR(10) DEFAULT 'None';

ALTER TABLE ngo
  ADD COLUMN password VARCHAR(255),
  ADD COLUMN darpan_id VARCHAR(40),
  ADD COLUMN contact_person VARCHAR(100),
  ADD COLUMN reg_file VARCHAR(120),
  ADD COLUMN verify_status VARCHAR(10) DEFAULT 'None';

ALTER TABLE volunteer
  ADD COLUMN password VARCHAR(255),
  ADD COLUMN vehicle_no VARCHAR(20),
  ADD COLUMN emergency_contact VARCHAR(15),
  ADD COLUMN id_file VARCHAR(120),
  ADD COLUMN selfie_file VARCHAR(120),
  ADD COLUMN verify_status VARCHAR(10) DEFAULT 'None';

ALTER TABLE food_donation
  ADD COLUMN cooked_at VARCHAR(5),
  ADD COLUMN is_veg TINYINT(1) DEFAULT 1;

CREATE TABLE IF NOT EXISTS verification_file (
    file_key VARCHAR(120) PRIMARY KEY,
    mime     VARCHAR(40) NOT NULL,
    content  LONGBLOB NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
