-- ═════════════════════════════════════════════════════════════
-- FoodBridge — food_db schema
-- Run with:  mysql -u root -p < schema.sql
-- ═════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS donor (
    donor_id           INT AUTO_INCREMENT PRIMARY KEY,
    donor_name         VARCHAR(100) NOT NULL,
    donor_type         VARCHAR(50),
    contact_no         VARCHAR(15),
    address            TEXT,
    hygiene_rating     DECIMAL(5,2),
    registration_date  DATE,
    password           VARCHAR(255),
    role               VARCHAR(100),
    email              VARCHAR(100),
    fssai_no           VARCHAR(14),
    license_file       VARCHAR(120),
    verify_status      VARCHAR(10) DEFAULT 'None'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS ngo (
    ngo_id             INT AUTO_INCREMENT PRIMARY KEY,
    ngo_name           VARCHAR(100) NOT NULL,
    contact_no         VARCHAR(15),
    address            TEXT,
    capacity           INT,
    priority_level     VARCHAR(20),
    registration_date  DATE,
    password           VARCHAR(255),
    darpan_id          VARCHAR(40),
    contact_person     VARCHAR(100),
    reg_file           VARCHAR(120),
    verify_status      VARCHAR(10) DEFAULT 'None'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS volunteer (
    volunteer_id         INT AUTO_INCREMENT PRIMARY KEY,
    name                 VARCHAR(100),
    contact_no           VARCHAR(15),
    vehicle_type         VARCHAR(50),
    availability_status  VARCHAR(50) DEFAULT 'Available',
    registration_date    DATE,
    password             VARCHAR(255),
    vehicle_no           VARCHAR(20),
    emergency_contact    VARCHAR(15),
    id_file              VARCHAR(120),
    selfie_file          VARCHAR(120),
    verify_status        VARCHAR(10) DEFAULT 'None'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS food_donation (
    donation_id          INT AUTO_INCREMENT PRIMARY KEY,
    food_type            VARCHAR(100),
    quantity              INT,
    original_quantity     INT,
    accepted_quantity     INT DEFAULT 0,
    parent_donation_id    INT,
    donation_status       ENUM('PENDING','ACCEPTED','COMPLETED','WASTED') DEFAULT 'PENDING',
    time                  TIME,
    date_of_donation      DATE,
    donor_id              INT,
    cooked_at             VARCHAR(5),
    is_veg                TINYINT(1) DEFAULT 1,
    KEY idx_fd_parent (parent_donation_id),
    KEY idx_fd_donor (donor_id),
    CONSTRAINT fk_fd_donor  FOREIGN KEY (donor_id) REFERENCES donor(donor_id) ON DELETE SET NULL,
    CONSTRAINT fk_fd_parent FOREIGN KEY (parent_donation_id) REFERENCES food_donation(donation_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS pickup (
    pickup_id       INT AUTO_INCREMENT PRIMARY KEY,
    time            DATETIME,
    status          VARCHAR(50) DEFAULT 'Pending',
    otp_code        INT,
    donation_id     INT,
    volunteer_id    INT,
    KEY idx_pu_donation (donation_id),
    KEY idx_pu_volunteer (volunteer_id),
    CONSTRAINT fk_pu_donation  FOREIGN KEY (donation_id) REFERENCES food_donation(donation_id) ON DELETE SET NULL,
    CONSTRAINT fk_pu_volunteer FOREIGN KEY (volunteer_id) REFERENCES volunteer(volunteer_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS delivery (
    delivery_id       INT AUTO_INCREMENT PRIMARY KEY,
    time              DATETIME,
    receiver_name     VARCHAR(100),
    delivery_status   VARCHAR(50) DEFAULT 'Pending',
    pickup_id         INT,
    ngo_id            INT,
    KEY idx_dl_pickup (pickup_id),
    KEY idx_dl_ngo (ngo_id),
    CONSTRAINT fk_dl_pickup FOREIGN KEY (pickup_id) REFERENCES pickup(pickup_id) ON DELETE SET NULL,
    CONSTRAINT fk_dl_ngo    FOREIGN KEY (ngo_id) REFERENCES ngo(ngo_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id       INT AUTO_INCREMENT PRIMARY KEY,
    rating            INT,
    hygiene_score     FLOAT,
    comments          TEXT,
    feedback_date     DATE,
    donation_id       INT NOT NULL,
    ngo_id            INT NOT NULL,
    from_ngo          TINYINT(1) DEFAULT 0,
    donor_id          INT NOT NULL,
    KEY idx_fb_donation (donation_id),
    KEY idx_fb_ngo (ngo_id),
    KEY idx_fb_donor (donor_id),
    CONSTRAINT fk_fb_donation FOREIGN KEY (donation_id) REFERENCES food_donation(donation_id) ON DELETE CASCADE,
    CONSTRAINT fk_fb_ngo      FOREIGN KEY (ngo_id) REFERENCES ngo(ngo_id) ON DELETE CASCADE,
    CONSTRAINT fk_fb_donor    FOREIGN KEY (donor_id) REFERENCES donor(donor_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS verification_file (
    file_key    VARCHAR(120) PRIMARY KEY,
    mime        VARCHAR(40) NOT NULL,
    content     LONGBLOB NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
