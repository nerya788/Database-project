USE school_football_db;

-- ============================================================================
-- Idempotency Note
-- MySQL has no "ADD CONSTRAINT IF NOT EXISTS" clause for CHECK/UNIQUE
-- constraints, so re-running this script would normally fail on the second
-- attempt with "Duplicate check constraint name" / "Duplicate key name".
-- Each constraint below is therefore preceded by a small safety guard: an
-- INFORMATION_SCHEMA lookup + dynamic SQL block that drops the constraint
-- first IF it already exists. This makes the entire script safely
-- re-executable from top to bottom, any number of times, with no manual
-- cleanup required between runs.
-- ============================================================================

-- ============================================================================
-- Pre-Flight Sanitization
-- Business Logic: Existing Practices rows must satisfy the new minimum-duration
-- rule before it is enforced, otherwise ALTER TABLE ... ADD CONSTRAINT will fail
-- validation against pre-existing data. Any session shorter than 40 minutes is
-- normalized to the standard 45-minute slot. (This UPDATE is naturally
-- idempotent - re-running it is harmless.)
-- ============================================================================
UPDATE Practices
SET duration_minutes = 45
WHERE duration_minutes < 40;


-- ============================================================================
-- Constraint 1: Minimum Practice Duration Threshold
-- Business Logic: Training sessions must be at least 40 minutes to meet
-- official league athletic development standards.
-- ============================================================================

-- 1.0 Safety Guard: drop the CHECK constraint first if it already exists
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Practices'
      AND CONSTRAINT_NAME = 'chk_min_practice_duration'
      AND CONSTRAINT_TYPE = 'CHECK'
);
SET @sql = IF(@exists > 0,
    'ALTER TABLE Practices DROP CHECK chk_min_practice_duration',
    'SELECT ''chk_min_practice_duration not present - nothing to drop'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 1.1 Add Constraint via ALTER TABLE
ALTER TABLE Practices
ADD CONSTRAINT chk_min_practice_duration
CHECK (duration_minutes >= 40);

-- 1.2 Demonstration: Intentional Constraint Violation Test (Expected to FAIL)
-- Attempting to insert a 30-minute practice session
-- Error Code Expected: 3819 (Check constraint 'chk_min_practice_duration' is violated)
INSERT INTO Practices (
    practice_id,
    team_id,
    field_id,
    practice_date,
    start_time,
    duration_minutes,
    practice_topic
) VALUES (
    99991,
    1,
    1,
    '2026-09-01',
    '16:00:00',
    30,
    'Quick Warmup Drill'
);


-- ============================================================================
-- Constraint 2: Cap on Match Score Sanity Check
-- Business Logic: In school tournaments, each team's score must fall within a
-- realistic 0-25 range to prevent data entry anomalies or unrealistic blowouts.
-- ============================================================================

-- 2.0 Safety Guard: drop the CHECK constraint first if it already exists
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Matches'
      AND CONSTRAINT_NAME = 'chk_match_max_score_cap'
      AND CONSTRAINT_TYPE = 'CHECK'
);
SET @sql = IF(@exists > 0,
    'ALTER TABLE Matches DROP CHECK chk_match_max_score_cap',
    'SELECT ''chk_match_max_score_cap not present - nothing to drop'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.1 Add Constraint via ALTER TABLE
ALTER TABLE Matches
ADD CONSTRAINT chk_match_max_score_cap
CHECK (home_score BETWEEN 0 AND 25 AND away_score BETWEEN 0 AND 25);

-- 2.2 Demonstration: Intentional Constraint Violation Test (Expected to FAIL)
-- Attempting to insert a match result with an invalid score of 32
-- Error Code Expected: 3819 (Check constraint 'chk_match_max_score_cap' is violated)
INSERT INTO Matches (
    match_id,
    home_team_id,
    away_team_id,
    field_id,
    match_date,
    start_time,
    home_score,
    away_score,
    match_status,
    round_stage,
    referee_name
) VALUES (
    99992,
    10,
    20,
    1,
    '2026-09-10',
    '17:30:00',
    32,
    2,
    'Completed',
    'Round 1',
    'Alon Yefet'
);


-- ============================================================================
-- Constraint 3: Unique Team Name per School
-- Business Logic: Prevent duplicate squad naming collisions within the same
-- school. A school cannot have two distinct teams registered with the exact
-- same team name.
-- ============================================================================

-- 3.0 Safety Guard: drop the UNIQUE constraint first if it already exists
-- NOTE: UNIQUE constraints are implemented as indexes in MySQL, so they must
-- be removed with DROP INDEX (DROP CHECK / DROP CONSTRAINT do not apply here).
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Teams'
      AND CONSTRAINT_NAME = 'uq_school_team_name'
      AND CONSTRAINT_TYPE = 'UNIQUE'
);
SET @sql = IF(@exists > 0,
    'ALTER TABLE Teams DROP INDEX uq_school_team_name',
    'SELECT ''uq_school_team_name not present - nothing to drop'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3.1 Add Constraint via ALTER TABLE
ALTER TABLE Teams
ADD CONSTRAINT uq_school_team_name
UNIQUE (school_id, team_name);

-- 3.2 Demonstration: Intentional Constraint Violation Test (Expected to FAIL)
-- Attempting to insert a second team named 'Team #1' under school_id 1
-- (captain_student_id 100000501 is not yet a captain of any team, so this
-- insert fails solely on the uq_school_team_name violation)
-- Error Code Expected: 1062 (Duplicate entry '1-Team #1' for key 'uq_school_team_name')
INSERT INTO Teams (
    team_id,
    team_name,
    school_id,
    captain_student_id,
    age_group,
    established_year
) VALUES (
    99993,
    'Team #1',
    1,
    '100000501',
    'U16',
    2022
);
