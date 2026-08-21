-- =============================================================
-- Project: School Football League Database System
-- Script: createTables.sql
-- Description: Creates the 7 core relational tables with 
--              Primary Keys, Foreign Keys, and Constraints.
-- =============================================================
CREATE DATABASE IF NOT EXISTS school_football_db;
USE school_football_db;

-- 1. Schools Table
CREATE TABLE Schools (
    school_id INT NOT NULL,
    school_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    full_address VARCHAR(150) NOT NULL,
    education_network VARCHAR(80),
    sports_director_name VARCHAR(80) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    CONSTRAINT pk_schools PRIMARY KEY (school_id)
);

-- 2. Fields Table
CREATE TABLE Fields (
    field_id INT NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    city_address VARCHAR(150) NOT NULL,
    surface_type VARCHAR(30) NOT NULL,
    has_lighting VARCHAR(5) NOT NULL,
    maintenance_status VARCHAR(30) NOT NULL,
    CONSTRAINT pk_fields PRIMARY KEY (field_id),
    CONSTRAINT chk_surface_type CHECK (surface_type IN ('Asphalt', 'Synthetic Grass', 'Natural Grass', 'Parquet Hall')),
    CONSTRAINT chk_lighting CHECK (has_lighting IN ('Yes', 'No', 'TRUE', 'FALSE')),
    CONSTRAINT chk_field_status CHECK (maintenance_status IN ('Operational', 'Needs Renovation', 'Closed'))
);

-- 3. Students Table
CREATE TABLE Students (
    student_id VARCHAR(9) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    school_id INT NOT NULL,
    preferred_position VARCHAR(30) NOT NULL,
    strong_foot VARCHAR(10) NOT NULL,
    join_date DATE NOT NULL,
    technical_rating INT NOT NULL,
    mental_rating INT NOT NULL,
    CONSTRAINT pk_students PRIMARY KEY (student_id),
    CONSTRAINT fk_students_school FOREIGN KEY (school_id) REFERENCES Schools(school_id),
    CONSTRAINT chk_preferred_position CHECK (preferred_position IN ('Goalkeeper', 'Defender', 'Midfielder', 'Forward')),
    CONSTRAINT chk_strong_foot CHECK (strong_foot IN ('Right', 'Left', 'Both')),
    CONSTRAINT chk_technical_rating CHECK (technical_rating BETWEEN 1 AND 100),
    CONSTRAINT chk_mental_rating CHECK (mental_rating BETWEEN 1 AND 100),
    CONSTRAINT chk_join_after_birth CHECK (join_date > birth_date)
);

-- 4. Global Equipment Table
CREATE TABLE Global_Equipment (
    item_barcode VARCHAR(50) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    brand_model VARCHAR(80) NOT NULL,
    purchase_date DATE NOT NULL,
    unit_cost_usd NUMERIC(8, 2) NOT NULL,
    current_status VARCHAR(30) NOT NULL,
    school_id INT, -- Can be NULL if the item is currently in the central warehouse
    shipping_date DATE,
    CONSTRAINT pk_global_equipment PRIMARY KEY (item_barcode),
    CONSTRAINT fk_equipment_school FOREIGN KEY (school_id) REFERENCES Schools(school_id),
    CONSTRAINT chk_item_type CHECK (item_type IN ('Match Ball', 'Training Ball', 'Cones Set', 'Goal Net', 'Match Jersey', 'Training Bibs')),
    CONSTRAINT chk_cost_positive CHECK (unit_cost_usd >= 0),
    CONSTRAINT chk_equipment_status CHECK (current_status IN ('In Central Warehouse', 'In Use', 'Lost', 'Damaged/Scrapped')),
    CONSTRAINT chk_shipping_date CHECK (shipping_date IS NULL OR shipping_date >= purchase_date)
);

-- 5. Teams Table
CREATE TABLE Teams (
    team_id INT NOT NULL,
    team_name VARCHAR(80) NOT NULL,
    school_id INT NOT NULL,
    captain_student_id VARCHAR(9),
    age_group VARCHAR(10) NOT NULL,
    established_year INT NOT NULL,
    CONSTRAINT pk_teams PRIMARY KEY (team_id),
    CONSTRAINT fk_teams_school FOREIGN KEY (school_id) REFERENCES Schools(school_id),
    CONSTRAINT fk_teams_captain FOREIGN KEY (captain_student_id) REFERENCES Students(student_id),
    CONSTRAINT chk_age_group CHECK (age_group IN ('U12', 'U14', 'U16', 'U18')),
    CONSTRAINT chk_established_year CHECK (established_year BETWEEN 1900 AND 2100)
);

-- 6. Practices Table
CREATE TABLE Practices (
    practice_id INT NOT NULL,
    team_id INT NOT NULL,
    field_id INT NOT NULL,
    practice_date DATE NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    duration_minutes INT NOT NULL,
    practice_topic VARCHAR(50) NOT NULL,
    CONSTRAINT pk_practices PRIMARY KEY (practice_id),
    CONSTRAINT fk_practices_team FOREIGN KEY (team_id) REFERENCES Teams(team_id),
    CONSTRAINT fk_practices_field FOREIGN KEY (field_id) REFERENCES Fields(field_id),
    CONSTRAINT chk_duration CHECK (duration_minutes BETWEEN 15 AND 300),
    CONSTRAINT chk_practice_topic CHECK (practice_topic IN ('Fitness', 'Tactics', 'Internal Scrimmage', 'Passing Drills', 'Set Pieces'))
);

-- 7. Matches Table
CREATE TABLE Matches (
    match_id INT NOT NULL,
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    field_id INT NOT NULL,
    match_date DATE NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    home_score INT DEFAULT 0 NOT NULL,
    away_score INT DEFAULT 0 NOT NULL,
    match_status VARCHAR(20) NOT NULL,
    round_stage VARCHAR(30) NOT NULL,
    referee_name VARCHAR(80) NOT NULL,
    CONSTRAINT pk_matches PRIMARY KEY (match_id),
    CONSTRAINT fk_matches_home_team FOREIGN KEY (home_team_id) REFERENCES Teams(team_id),
    CONSTRAINT fk_matches_away_team FOREIGN KEY (away_team_id) REFERENCES Teams(team_id),
    CONSTRAINT fk_matches_field FOREIGN KEY (field_id) REFERENCES Fields(field_id),
    CONSTRAINT chk_different_teams CHECK (home_team_id <> away_team_id),
    CONSTRAINT chk_home_score CHECK (home_score >= 0),
    CONSTRAINT chk_away_score CHECK (away_score >= 0),
    CONSTRAINT chk_match_status CHECK (match_status IN ('Scheduled', 'Ongoing', 'Finished', 'Postponed', 'Cancelled'))
);