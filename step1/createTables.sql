-- ============================================================================
-- Database Creation & Configuration
-- ============================================================================
CREATE DATABASE IF NOT EXISTS school_football_db;
USE school_football_db;

-- ============================================================================
-- 1. Base Core Entities
-- ============================================================================

-- Table 1: Schools
CREATE TABLE Schools (
    school_id INT AUTO_INCREMENT PRIMARY KEY,
    school_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    full_address VARCHAR(255) NOT NULL,
    education_network VARCHAR(50) NOT NULL,
    sports_director_name VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL
) ENGINE=InnoDB;

-- Table 2: Fields
CREATE TABLE Fields (
    field_id INT AUTO_INCREMENT PRIMARY KEY,
    field_name VARCHAR(100) NOT NULL,
    city_address VARCHAR(100) NOT NULL,
    surface_type ENUM('Natural Grass', 'Artificial Turf', 'Hybrid') NOT NULL,
    has_lighting ENUM('Yes', 'No') NOT NULL,
    maintenance_status ENUM('Operational', 'Needs Renovation', 'Closed') NOT NULL
) ENGINE=InnoDB;

-- Table 3: Students (Large Table #1)
CREATE TABLE Students (
    student_id VARCHAR(10) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    school_id INT NOT NULL,
    preferred_position ENUM('Goalkeeper', 'Defender', 'Midfielder', 'Forward') NOT NULL,
    strong_foot ENUM('Right', 'Left', 'Both') NOT NULL,
    join_date DATE NOT NULL,
    technical_rating INT NOT NULL CHECK (technical_rating BETWEEN 1 AND 100),
    mental_rating INT NOT NULL CHECK (mental_rating BETWEEN 1 AND 100),
    CONSTRAINT fk_students_school 
        FOREIGN KEY (school_id) REFERENCES Schools(school_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Table 4: Teams
CREATE TABLE Teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,
    school_id INT NOT NULL,
    captain_student_id VARCHAR(10) NOT NULL UNIQUE,
    age_group ENUM('U12', 'U14', 'U16', 'U18') NOT NULL,
    established_year INT NOT NULL CHECK (established_year BETWEEN 1900 AND 2026),
    CONSTRAINT fk_teams_school 
        FOREIGN KEY (school_id) REFERENCES Schools(school_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_teams_captain 
        FOREIGN KEY (captain_student_id) REFERENCES Students(student_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- 2. Inheritance Hierarchy (Generalization / Specialization)
-- ============================================================================

-- Table 5: Global_Equipment (Supertype / Large Table #2)
CREATE TABLE Global_Equipment (
    item_barcode VARCHAR(64) PRIMARY KEY,
    brand_model VARCHAR(100) NOT NULL,
    purchase_date DATE NOT NULL,
    unit_cost_usd DECIMAL(8, 2) NOT NULL CHECK (unit_cost_usd > 0),
    current_status ENUM('Operational', 'Under Repair', 'Needs Inspection', 'In Central Warehouse') NOT NULL,
    school_id INT NULL,
    shipping_date DATE NULL,
    CONSTRAINT fk_equipment_school 
        FOREIGN KEY (school_id) REFERENCES Schools(school_id) 
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_shipping_after_purchase 
        CHECK (shipping_date IS NULL OR shipping_date >= purchase_date)
) ENGINE=InnoDB;

-- Table 5.1: Training_Gear (Subtype 1)
CREATE TABLE Training_Gear (
    item_barcode VARCHAR(64) PRIMARY KEY,
    gear_category ENUM('Balls', 'Cones', 'Vests', 'Agility Ladders', 'Goal Nets') NOT NULL,
    size_standard ENUM('Size 4', 'Size 5', 'Standard', 'Junior') NOT NULL,
    CONSTRAINT fk_training_gear_parent 
        FOREIGN KEY (item_barcode) REFERENCES Global_Equipment(item_barcode) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Table 5.2: Medical_Kits (Subtype 2)
CREATE TABLE Medical_Kits (
    item_barcode VARCHAR(64) PRIMARY KEY,
    kit_type ENUM('First Aid Kit', 'Ice Packs & Strapping', 'Bandages & Tape', 'Defibrillator & AED Kit') NOT NULL,
    expiry_date DATE NOT NULL,
    is_sterile BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_medical_kits_parent 
        FOREIGN KEY (item_barcode) REFERENCES Global_Equipment(item_barcode) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- 3. Operations & Weak Entities
-- ============================================================================

-- Table 6: Practices
CREATE TABLE Practices (
    practice_id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    field_id INT NOT NULL,
    practice_date DATE NOT NULL,
    start_time TIME NOT NULL,
    duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
    practice_topic VARCHAR(100) NOT NULL,
    CONSTRAINT fk_practices_team 
        FOREIGN KEY (team_id) REFERENCES Teams(team_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_practices_field 
        FOREIGN KEY (field_id) REFERENCES Fields(field_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Table 7: Matches
CREATE TABLE Matches (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    field_id INT NOT NULL,
    match_date DATE NOT NULL,
    start_time TIME NOT NULL,
    home_score INT NOT NULL DEFAULT 0 CHECK (home_score >= 0),
    away_score INT NOT NULL DEFAULT 0 CHECK (away_score >= 0),
    match_status ENUM('Completed', 'Scheduled', 'Postponed', 'In Progress') NOT NULL,
    round_stage ENUM('Round 1', 'Round 2', 'Round 3', 'Quarter Final', 'Semi Final', 'Final') NOT NULL,
    referee_name VARCHAR(100) NOT NULL,
    CONSTRAINT fk_matches_home_team 
        FOREIGN KEY (home_team_id) REFERENCES Teams(team_id) 
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_matches_away_team 
        FOREIGN KEY (away_team_id) REFERENCES Teams(team_id) 
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_matches_field 
        FOREIGN KEY (field_id) REFERENCES Fields(field_id) 
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_different_teams 
        CHECK (home_team_id <> away_team_id)
) ENGINE=InnoDB;

-- Table 8: Maintenance_Logs (Identifying Weak Entity of Fields)
CREATE TABLE Maintenance_Logs (
    field_id INT NOT NULL,
    log_date DATE NOT NULL,
    performed_by VARCHAR(100) NOT NULL,
    maintenance_cost DECIMAL(8, 2) NOT NULL CHECK (maintenance_cost >= 0),
    work_summary VARCHAR(255) NOT NULL,
    safety_passed BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (field_id, log_date),
    CONSTRAINT fk_maintenance_field 
        FOREIGN KEY (field_id) REFERENCES Fields(field_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- 4. Associative Entity (M:N Relationship)
-- ============================================================================

-- Table 9: Match_Events (M:N Associative Entity between Students and Matches)
CREATE TABLE Match_Events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT NOT NULL,
    student_id VARCHAR(10) NOT NULL,
    minute_in_game INT NOT NULL CHECK (minute_in_game BETWEEN 1 AND 120),
    event_type ENUM('Goal', 'Yellow Card', 'Red Card', 'Assist', 'Substitution') NOT NULL,
    description VARCHAR(255) NULL,
    CONSTRAINT fk_events_match 
        FOREIGN KEY (match_id) REFERENCES Matches(match_id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_events_student 
        FOREIGN KEY (student_id) REFERENCES Students(student_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;