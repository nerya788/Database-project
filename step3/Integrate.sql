-- ============================================================================
-- Stage C: Database Integration Script (Integrate.sql)
-- Project: school_football_db integrated with the partner "Fantasy League &
--          Trading" system.
-- Author: Nerya Cohen (ID: 316482801)
-- ============================================================================

USE school_football_db;

-- ============================================================================
-- SECTION A: IDEMPOTENT SCHEMA SETUP
-- ============================================================================

-- ----------------------------------------------------------------------------
-- A.1 Entity Unification: conditionally add current_price to Students
-- Uses the same INFORMATION_SCHEMA + dynamic SQL guard pattern as
-- step2/Constraints.sql and step2/Index.sql, so the ALTER TABLE only runs
-- once even if this script is executed multiple times.
-- ----------------------------------------------------------------------------
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Students'
      AND COLUMN_NAME = 'current_price'
);
SET @sql = IF(@exists = 0,
    'ALTER TABLE Students ADD COLUMN current_price DECIMAL(10,2) DEFAULT 50.00',
    'SELECT ''current_price column already present - skipping'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ----------------------------------------------------------------------------
-- A.2 Core-Schema Support Table: Team_Players
-- The original step1 schema only records ONE captain per team
-- (Teams.captain_student_id); it has no way to represent a full squad
-- roster. Team_Players is the missing M:N junction between Students and
-- Teams that View 1 (Stage C) needs. This is a core-schema addition, not a
-- partner-system table, so it is created first.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Team_Players (
    team_id INT NOT NULL,
    student_id VARCHAR(10) NOT NULL,
    PRIMARY KEY (team_id, student_id),
    CONSTRAINT fk_teamplayers_team
        FOREIGN KEY (team_id) REFERENCES Teams(team_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_teamplayers_student
        FOREIGN KEY (student_id) REFERENCES Students(student_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- A.3 Partner System Tables (Fantasy League & Trading)
-- Created in FK-dependency order: USERS/ROUNDS have no dependencies;
-- USER_SQUADS/TRANSACTIONS depend on USERS + Students; PRICE_HISTORY
-- depends on Students + ROUNDS.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS USERS (
    user_id INT PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    current_budget DECIMAL(12,2) NOT NULL DEFAULT 1000.00
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ROUNDS (
    round_id INT PRIMARY KEY,
    round_number INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS USER_SQUADS (
    squad_record_id INT PRIMARY KEY,
    lineup_status VARCHAR(50) NOT NULL,
    user_id INT NOT NULL,
    player_id VARCHAR(10) NOT NULL,
    CONSTRAINT fk_squad_user
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_squad_student
        FOREIGN KEY (player_id) REFERENCES Students(student_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS TRANSACTIONS (
    transaction_id INT PRIMARY KEY,
    transaction_time DATETIME NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    transaction_price DECIMAL(10,2) NOT NULL,
    user_id INT NOT NULL,
    player_id VARCHAR(10) NOT NULL,
    CONSTRAINT fk_tx_user
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tx_student
        FOREIGN KEY (player_id) REFERENCES Students(student_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS PRICE_HISTORY (
    history_id INT PRIMARY KEY,
    recorded_price DECIMAL(10,2) NOT NULL,
    player_id VARCHAR(10) NOT NULL,
    round_id INT NOT NULL,
    CONSTRAINT fk_price_student
        FOREIGN KEY (player_id) REFERENCES Students(student_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_price_round
        FOREIGN KEY (round_id) REFERENCES ROUNDS(round_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;


-- ============================================================================
-- >>> STOP HERE if this is the first run: execute step3/USERS.sql and
-- >>> step3/ROUNDS.sql now, then continue with SECTION B below. <<<
-- ============================================================================


-- ============================================================================
-- SECTION B: DATA POPULATION
-- ============================================================================

-- Diagnostic: confirm the partner reference tables are populated before
-- proceeding. If either count is 0, run USERS.sql / ROUNDS.sql first.
SELECT
    (SELECT COUNT(*) FROM USERS)  AS users_available,
    (SELECT COUNT(*) FROM ROUNDS) AS rounds_available;

-- ----------------------------------------------------------------------------
-- B.1 Populate current_price for every student
-- Pure function of technical_rating/mental_rating - naturally idempotent,
-- safe to re-run (always yields the same result for the same ratings).
-- ----------------------------------------------------------------------------
UPDATE Students
SET current_price = ROUND(30.00 + (technical_rating * 0.70) + (mental_rating * 0.30), 2);

-- ----------------------------------------------------------------------------
-- B.2 Populate Team_Players
-- Step 1 (always safe): every team's captain is on its own roster.
-- INSERT IGNORE + the composite PRIMARY KEY make this naturally idempotent.
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO Team_Players (team_id, student_id)
SELECT team_id, captain_student_id
FROM Teams;

-- Step 2 (guarded synthetic roster expansion): step1's data only records
-- ONE captain per team, so we deterministically fill out the rest of each
-- squad from the SAME school's remaining students, round-robin per school,
-- capped at 17 extra players per team (18-player squad including the
-- captain). Guarded so it only runs once: if Team_Players already holds
-- more rows than there are Teams, the expansion has already happened.
SET @needs_expansion = (
    (SELECT COUNT(*) FROM Team_Players) <= (SELECT COUNT(*) FROM Teams)
);
SET @sql = IF(@needs_expansion,
    'INSERT IGNORE INTO Team_Players (team_id, student_id)
    WITH school_teams AS (
        SELECT team_id, school_id,
               ROW_NUMBER() OVER (PARTITION BY school_id ORDER BY team_id) - 1 AS team_rank,
               COUNT(*) OVER (PARTITION BY school_id) AS team_count
        FROM Teams
    ),
    eligible_students AS (
        SELECT s.student_id, s.school_id,
               ROW_NUMBER() OVER (PARTITION BY s.school_id ORDER BY s.student_id) - 1 AS student_rank
        FROM Students s
        WHERE NOT EXISTS (
            SELECT 1 FROM (SELECT student_id FROM Team_Players) AS tp_snapshot
            WHERE tp_snapshot.student_id = s.student_id
        )
    )
    SELECT st.team_id, es.student_id
    FROM eligible_students es
    JOIN school_teams st
      ON st.school_id = es.school_id
     AND st.team_rank = es.student_rank MOD st.team_count
    WHERE es.student_rank < st.team_count * 17',
    'SELECT ''Team_Players roster already expanded - skipping'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ----------------------------------------------------------------------------
-- B.3 Populate USER_SQUADS
-- Only students who actually made a team roster (Team_Players) are
-- fantasy-draftable - this keeps the fantasy layer narratively and
-- referentially tied to the real league. The first 300 USERS each receive a
-- deterministic 15-player squad (11 "Starting XI" + 4 "Bench") drawn via a
-- wraparound window over the distinct Team_Players roster, so re-running
-- this script reproduces the exact same assignment (INSERT IGNORE +
-- deterministic ROW_NUMBER ordering => idempotent).
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO USER_SQUADS (squad_record_id, lineup_status, user_id, player_id)
WITH roster_pool AS (
    SELECT student_id,
           CAST(ROW_NUMBER() OVER (ORDER BY student_id) AS SIGNED) - 1 AS player_rank,
           COUNT(*) OVER () AS pool_size
    FROM (SELECT DISTINCT student_id FROM Team_Players) AS distinct_roster
),
squad_users AS (
    SELECT user_id,
           CAST(ROW_NUMBER() OVER (ORDER BY user_id) AS SIGNED) - 1 AS user_rank
    FROM (SELECT user_id FROM USERS ORDER BY user_id LIMIT 300) AS limited_users
),
squad_windows AS (
    SELECT su.user_id,
           (su.user_rank * 15) MOD rp_size.pool_size AS window_start,
           rp_size.pool_size
    FROM squad_users su
    CROSS JOIN (SELECT MAX(pool_size) AS pool_size FROM roster_pool) AS rp_size
)
SELECT
    ROW_NUMBER() OVER (ORDER BY sw.user_id, rp.player_rank) AS squad_record_id,
    CASE WHEN ((rp.player_rank - sw.window_start + sw.pool_size) MOD sw.pool_size) < 11
         THEN 'Starting XI' ELSE 'Bench' END AS lineup_status,
    sw.user_id,
    rp.student_id AS player_id
FROM squad_windows sw
JOIN roster_pool rp
  ON ((rp.player_rank - sw.window_start + sw.pool_size) MOD sw.pool_size) < 15;

-- ----------------------------------------------------------------------------
-- B.4 Populate TRANSACTIONS
-- Every squad slot implies at least one BUY transaction (fully FK-safe,
-- sourced directly from USER_SQUADS). Bench players additionally get a
-- SELL transaction, simulating a partial squad rotation.
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO TRANSACTIONS (transaction_id, transaction_time, action_type, transaction_price, user_id, player_id)
SELECT
    ROW_NUMBER() OVER (ORDER BY us.user_id, us.player_id) AS transaction_id,
    DATE_SUB(CURDATE(), INTERVAL (MOD(us.user_id * 7 + CAST(SUBSTRING(us.player_id, -3) AS UNSIGNED), 300)) DAY) AS transaction_time,
    'BUY' AS action_type,
    s.current_price AS transaction_price,
    us.user_id,
    us.player_id
FROM USER_SQUADS us
JOIN Students s ON s.student_id = us.player_id;

INSERT IGNORE INTO TRANSACTIONS (transaction_id, transaction_time, action_type, transaction_price, user_id, player_id)
SELECT
    (SELECT COUNT(*) FROM USER_SQUADS) + ROW_NUMBER() OVER (ORDER BY us.user_id, us.player_id) AS transaction_id,
    DATE_SUB(CURDATE(), INTERVAL (MOD(us.user_id * 11 + CAST(SUBSTRING(us.player_id, -3) AS UNSIGNED), 200)) DAY) AS transaction_time,
    'SELL' AS action_type,
    ROUND(s.current_price * 1.05, 2) AS transaction_price,
    us.user_id,
    us.player_id
FROM USER_SQUADS us
JOIN Students s ON s.student_id = us.player_id
WHERE us.lineup_status = 'Bench';

-- ----------------------------------------------------------------------------
-- B.5 Populate PRICE_HISTORY
-- Every distinct fantasy-drafted player (from USER_SQUADS) gets a price
-- sample for the first 10 ROUNDS, with a deterministic +/-10% fluctuation
-- band derived from the player_id and round_id (no RAND(), so re-running
-- this script reproduces identical values).
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO PRICE_HISTORY (history_id, recorded_price, player_id, round_id)
SELECT
    ROW_NUMBER() OVER (ORDER BY p.player_id, r.round_id) AS history_id,
    ROUND(s.current_price * (0.90 + (MOD(CAST(SUBSTRING(p.player_id, -2) AS UNSIGNED) + r.round_id, 21)) / 100.0), 2) AS recorded_price,
    p.player_id,
    r.round_id
FROM (SELECT DISTINCT player_id FROM USER_SQUADS) p
JOIN Students s ON s.student_id = p.player_id
CROSS JOIN (SELECT round_id FROM ROUNDS ORDER BY round_id LIMIT 10) r;


-- ----------------------------------------------------------------------------
-- B.6 Verification: row counts across the integrated schema
-- ----------------------------------------------------------------------------
SELECT 'Team_Players' AS tbl, COUNT(*) AS total FROM Team_Players
UNION ALL
SELECT 'Users', COUNT(*) FROM USERS
UNION ALL
SELECT 'Rounds', COUNT(*) FROM ROUNDS
UNION ALL
SELECT 'User_Squads', COUNT(*) FROM USER_SQUADS
UNION ALL
SELECT 'Transactions', COUNT(*) FROM TRANSACTIONS
UNION ALL
SELECT 'Price_History', COUNT(*) FROM PRICE_HISTORY;
