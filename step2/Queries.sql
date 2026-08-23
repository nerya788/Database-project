USE school_football_db;

-- ============================================================================
-- 1. SELECT QUERIES (8 Queries total, 1-4 with dual implementations)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- SELECT Query 1 (Dual Form): Forward Player Goal-Scoring Performance Report
-- Target GUI Screen: "Goal Scorers & Offensive Performance Dashboard"
-- Business Purpose: Identifies high-performing Forwards who scored in matches,
-- breaking down event dates by Year and Month with school and rating data.
-- ----------------------------------------------------------------------------

-- Form 1A: Multi-table JOIN with GROUP BY, HAVING, and Date Deconstruction
SELECT 
    s.student_id,
    CONCAT(s.first_name, ' ', s.last_name) AS player_full_name,
    sc.school_name,
    s.technical_rating,
    YEAR(m.match_date) AS match_year,
    MONTHNAME(m.match_date) AS match_month,
    COUNT(me.event_id) AS total_goals_scored
FROM Students s
JOIN Schools sc ON s.school_id = sc.school_id
JOIN Match_Events me ON s.student_id = me.student_id
JOIN Matches m ON me.match_id = m.match_id
WHERE s.preferred_position = 'Forward' 
  AND me.event_type = 'Goal'
GROUP BY 
    s.student_id, 
    s.first_name, 
    s.last_name, 
    sc.school_name, 
    s.technical_rating, 
    YEAR(m.match_date), 
    MONTHNAME(m.match_date)
HAVING COUNT(me.event_id) >= 1
ORDER BY total_goals_scored DESC, s.technical_rating DESC;

-- Form 1B: Correlated Subquery with EXISTS and Aggregate Sub-selection
-- NOTE: Must preserve the same (student, year, month) grain as Form 1A, so
-- Match_Events/Matches are still used to drive the rows; the aggregate and
-- school lookup are computed via correlated subqueries instead of GROUP BY.
SELECT DISTINCT
    s.student_id,
    CONCAT(s.first_name, ' ', s.last_name) AS player_full_name,
    (SELECT sc.school_name FROM Schools sc WHERE sc.school_id = s.school_id) AS school_name,
    s.technical_rating,
    YEAR(m.match_date) AS match_year,
    MONTHNAME(m.match_date) AS match_month,
    (
        SELECT COUNT(*)
        FROM Match_Events me2
        JOIN Matches m2 ON me2.match_id = m2.match_id
        WHERE me2.student_id = s.student_id
          AND me2.event_type = 'Goal'
          AND YEAR(m2.match_date) = YEAR(m.match_date)
          AND MONTHNAME(m2.match_date) = MONTHNAME(m.match_date)
    ) AS total_goals_scored
FROM Students s
JOIN Match_Events me ON s.student_id = me.student_id
JOIN Matches m ON me.match_id = m.match_id
WHERE s.preferred_position = 'Forward'
  AND me.event_type = 'Goal'
  AND EXISTS (
      SELECT 1
      FROM Match_Events me3
      WHERE me3.student_id = s.student_id
        AND me3.event_type = 'Goal'
  )
ORDER BY total_goals_scored DESC, s.technical_rating DESC;


-- ----------------------------------------------------------------------------
-- SELECT Query 2 (Dual Form): Field Safety & Maintenance Budget Analysis
-- Target GUI Screen: "Facility Management & Infrastructure Audit"
-- Business Purpose: Finds Artificial Turf fields whose cumulative maintenance 
-- costs exceed the national average field maintenance expenditure.
-- ----------------------------------------------------------------------------

-- Form 2A: Derived Table (Subquery in FROM) with Aggregation and JOIN
SELECT 
    f.field_id,
    f.field_name,
    f.city_address,
    f.surface_type,
    f.maintenance_status,
    field_stats.total_spent,
    field_stats.inspection_count
FROM Fields f
JOIN (
    SELECT 
        field_id,
        SUM(maintenance_cost) AS total_spent,
        COUNT(*) AS inspection_count
    FROM Maintenance_Logs
    GROUP BY field_id
) AS field_stats ON f.field_id = field_stats.field_id
WHERE f.surface_type = 'Artificial Turf'
  AND field_stats.total_spent > (
      SELECT AVG(total_per_field)
      FROM (
          SELECT SUM(maintenance_cost) AS total_per_field
          FROM Maintenance_Logs
          GROUP BY field_id
      ) AS avg_table
  )
ORDER BY field_stats.total_spent DESC;

-- Form 2B: Non-Correlated Subquery in HAVING Clause
SELECT 
    f.field_id,
    f.field_name,
    f.city_address,
    f.surface_type,
    f.maintenance_status,
    SUM(ml.maintenance_cost) AS total_spent,
    COUNT(ml.log_date) AS inspection_count
FROM Fields f
JOIN Maintenance_Logs ml ON f.field_id = ml.field_id
WHERE f.surface_type = 'Artificial Turf'
GROUP BY 
    f.field_id, 
    f.field_name, 
    f.city_address, 
    f.surface_type, 
    f.maintenance_status
HAVING SUM(ml.maintenance_cost) > (
    SELECT AVG(total_per_field)
    FROM (
        SELECT SUM(maintenance_cost) AS total_per_field
        FROM Maintenance_Logs
        GROUP BY field_id
    ) AS avg_table
)
ORDER BY total_spent DESC;


-- ----------------------------------------------------------------------------
-- SELECT Query 3 (Dual Form): Critical Medical Equipment Expiration Tracking
-- Target GUI Screen: "Medical Compliance & Emergency Supplies Monitor"
-- Business Purpose: Identifies schools holding sterile medical kits expiring 
-- in the upcoming year (2026/2027) to coordinate replenishment.
-- ----------------------------------------------------------------------------

-- Form 3A: Direct Multi-table JOIN across ISA Subclass and Superclass
SELECT 
    sc.school_name,
    sc.city,
    sc.sports_director_name,
    sc.contact_phone,
    ge.item_barcode,
    ge.brand_model,
    mk.kit_type,
    YEAR(mk.expiry_date) AS expiry_year,
    MONTH(mk.expiry_date) AS expiry_month
FROM Schools sc
JOIN Global_Equipment ge ON sc.school_id = ge.school_id
JOIN Medical_Kits mk ON ge.item_barcode = mk.item_barcode
WHERE mk.is_sterile = TRUE
  AND YEAR(mk.expiry_date) BETWEEN 2026 AND 2027
ORDER BY sc.school_name ASC, ge.item_barcode ASC
LIMIT 100;

-- Form 3B: Nested Subquery using IN Operator
SELECT
    sc.school_name,
    sc.city,
    sc.sports_director_name,
    sc.contact_phone,
    ge.item_barcode,
    ge.brand_model,
    (SELECT mk.kit_type FROM Medical_Kits mk WHERE mk.item_barcode = ge.item_barcode) AS kit_type,
    (SELECT YEAR(mk.expiry_date) FROM Medical_Kits mk WHERE mk.item_barcode = ge.item_barcode) AS expiry_year,
    (SELECT MONTH(mk.expiry_date) FROM Medical_Kits mk WHERE mk.item_barcode = ge.item_barcode) AS expiry_month
FROM Schools sc
JOIN Global_Equipment ge ON sc.school_id = ge.school_id
WHERE ge.item_barcode IN (
    SELECT mk.item_barcode
    FROM Medical_Kits mk
    WHERE mk.is_sterile = TRUE
      AND YEAR(mk.expiry_date) BETWEEN 2026 AND 2027
)
ORDER BY sc.school_name ASC, ge.item_barcode ASC
LIMIT 100;


-- ----------------------------------------------------------------------------
-- SELECT Query 4 (Dual Form): High-Intensity Youth Practice Session Audit
-- Target GUI Screen: "Athletic Program & Practice Workload Overview"
-- Business Purpose: Analyzes intensive training sessions (>= 90 mins) held by 
-- junior squads (U16/U18) on venues equipped with floodlighting.
-- ----------------------------------------------------------------------------

-- Form 4A: Relational INNER JOIN on Multiple Predicates
SELECT 
    t.team_name,
    t.age_group,
    f.field_name,
    f.city_address,
    p.practice_topic,
    p.duration_minutes,
    DATE_FORMAT(p.practice_date, '%d/%m/%Y') AS formatted_practice_date,
    p.start_time
FROM Teams t
JOIN Practices p ON t.team_id = p.team_id
JOIN Fields f ON p.field_id = f.field_id
WHERE t.age_group IN ('U16', 'U18')
  AND p.duration_minutes >= 90
  AND f.has_lighting = 'Yes'
ORDER BY p.practice_date DESC, p.duration_minutes DESC;

-- Form 4B: Nested Correlated EXISTS Subquery with CTE-like Structure
SELECT
    t.team_name,
    t.age_group,
    (SELECT f.field_name FROM Fields f WHERE f.field_id = p.field_id) AS field_name,
    (SELECT f.city_address FROM Fields f WHERE f.field_id = p.field_id) AS city_address,
    p.practice_topic,
    p.duration_minutes,
    DATE_FORMAT(p.practice_date, '%d/%m/%Y') AS formatted_practice_date,
    p.start_time
FROM Teams t
JOIN Practices p ON t.team_id = p.team_id
WHERE t.age_group IN ('U16', 'U18')
  AND p.duration_minutes >= 90
  AND EXISTS (
      SELECT 1
      FROM Fields f
      WHERE f.field_id = p.field_id
        AND f.has_lighting = 'Yes'
  )
ORDER BY p.practice_date DESC, p.duration_minutes DESC;


-- ----------------------------------------------------------------------------
-- SELECT Query 5: Disciplinary Infractions & Card Tracking by Tournament Stage
-- Target GUI Screen: "Disciplinary Committee & League Sanctions"
-- Business Purpose: Aggregates cards received by athletes grouped by competition stage.
-- ----------------------------------------------------------------------------
SELECT 
    s.student_id,
    CONCAT(s.first_name, ' ', s.last_name) AS athlete_name,
    sc.school_name,
    m.round_stage,
    me.event_type AS sanction_type,
    COUNT(me.event_id) AS total_sanctions,
    AVG(me.minute_in_game) AS avg_minute_received
FROM Students s
JOIN Schools sc ON s.school_id = sc.school_id
JOIN Match_Events me ON s.student_id = me.student_id
JOIN Matches m ON me.match_id = m.match_id
WHERE me.event_type IN ('Yellow Card', 'Red Card')
GROUP BY 
    s.student_id, 
    s.first_name, 
    s.last_name, 
    sc.school_name, 
    m.round_stage, 
    me.event_type
HAVING COUNT(me.event_id) >= 1
ORDER BY total_sanctions DESC, s.last_name ASC;


-- ----------------------------------------------------------------------------
-- SELECT Query 6: Decisive Knockout Fixture Logistics & Referee Appointments
-- Target GUI Screen: "Tournament Fixtures & Match Official Assignment"
-- Business Purpose: Coordinates field surfaces, scores, and referees for playoff games.
-- ----------------------------------------------------------------------------
SELECT 
    m.match_id,
    m.round_stage,
    ht.team_name AS home_squad,
    at.team_name AS away_squad,
    CONCAT(m.home_score, ' - ', m.away_score) AS match_result,
    f.field_name AS stadium,
    f.surface_type,
    m.referee_name,
    DAYNAME(m.match_date) AS match_day,
    m.match_date
FROM Matches m
JOIN Teams ht ON m.home_team_id = ht.team_id
JOIN Teams at ON m.away_team_id = at.team_id
JOIN Fields f ON m.field_id = f.field_id
WHERE m.round_stage IN ('Quarter Final', 'Semi Final', 'Final')
  AND m.match_status = 'Completed'
ORDER BY m.match_date DESC, m.round_stage ASC;


-- ----------------------------------------------------------------------------
-- SELECT Query 7: Brand Gear Allocation by Educational Network
-- Target GUI Screen: "League Equipment Distribution & Network Sponsorship"
-- Business Purpose: Evaluates investment volume in training gear per network.
-- ----------------------------------------------------------------------------
SELECT 
    sc.education_network,
    tg.gear_category,
    ge.brand_model,
    COUNT(ge.item_barcode) AS total_units_distributed,
    SUM(ge.unit_cost_usd) AS aggregate_inventory_value,
    ROUND(AVG(ge.unit_cost_usd), 2) AS average_unit_cost
FROM Schools sc
JOIN Global_Equipment ge ON sc.school_id = ge.school_id
JOIN Training_Gear tg ON ge.item_barcode = tg.item_barcode
GROUP BY 
    sc.education_network, 
    tg.gear_category, 
    ge.brand_model
HAVING COUNT(ge.item_barcode) > 50
ORDER BY aggregate_inventory_value DESC;


-- ----------------------------------------------------------------------------
-- SELECT Query 8: High-Caliber Captains Leadership Assessment
-- Target GUI Screen: "Team Captaincy & Elite Leadership Registry"
-- Business Purpose: Identifies established teams led by elite captains (Mental Rating >= 85).
-- ----------------------------------------------------------------------------
SELECT 
    t.team_id,
    t.team_name,
    t.age_group,
    t.established_year,
    CONCAT(s.first_name, ' ', s.last_name) AS captain_name,
    s.preferred_position,
    s.mental_rating,
    s.technical_rating,
    sc.school_name
FROM Teams t
JOIN Students s ON t.captain_student_id = s.student_id
JOIN Schools sc ON t.school_id = sc.school_id
WHERE s.mental_rating >= 85
  AND t.established_year <= 2020
ORDER BY s.mental_rating DESC, s.technical_rating DESC;


-- ============================================================================
-- 2. UPDATE QUERIES (3 Non-Trivial Queries using Subqueries)
-- Each query is structured as Step A (BEFORE verification SELECT),
-- Step B (the UPDATE execution), and Step C (AFTER verification SELECT),
-- so before/after screenshots can be captured for the project report.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- UPDATE Query 1: Flag Substandard Fields Requiring Overhaul
-- Business Purpose: Sets field status to 'Needs Renovation' if aggregate maintenance
-- costs exceeded $5,000 across inspection history.
-- ----------------------------------------------------------------------------

-- Step A (BEFORE Verification): Show the targeted fields and their current
-- maintenance_status, using the exact same subquery logic the UPDATE below
-- uses to select its target rows.
SELECT
    field_id,
    field_name,
    maintenance_status
FROM Fields
WHERE field_id IN (
    SELECT field_id
    FROM (
        SELECT field_id
        FROM Maintenance_Logs
        GROUP BY field_id
        HAVING SUM(maintenance_cost) > 5000.00
    ) AS costly_fields
)
ORDER BY field_id;

-- Step B (EXECUTION): Flag every field whose cumulative maintenance cost
-- exceeds $5,000 as 'Needs Renovation'.
UPDATE Fields
SET maintenance_status = 'Needs Renovation'
WHERE field_id IN (
    SELECT field_id
    FROM (
        SELECT field_id
        FROM Maintenance_Logs
        GROUP BY field_id
        HAVING SUM(maintenance_cost) > 5000.00
    ) AS costly_fields
);

-- Step C (AFTER Verification): Re-run the identical query; every row must
-- now show maintenance_status = 'Needs Renovation'.
SELECT
    field_id,
    field_name,
    maintenance_status
FROM Fields
WHERE field_id IN (
    SELECT field_id
    FROM (
        SELECT field_id
        FROM Maintenance_Logs
        GROUP BY field_id
        HAVING SUM(maintenance_cost) > 5000.00
    ) AS costly_fields
)
ORDER BY field_id;


-- ----------------------------------------------------------------------------
-- UPDATE Query 2: Mark Expiring Medical Kits for Safety Inspection
-- Business Purpose: Changes equipment condition status to 'Needs Inspection'
-- for non-sterile or expired medical kits allocated to schools.
-- ----------------------------------------------------------------------------

-- Step A (BEFORE Verification): Show the targeted equipment items and their
-- current_status, using the exact same WHERE/subquery logic the UPDATE below
-- uses to select its target rows.
SELECT
    item_barcode,
    brand_model,
    current_status,
    school_id
FROM Global_Equipment
WHERE item_barcode IN (
    SELECT item_barcode
    FROM Medical_Kits
    WHERE expiry_date < '2026-12-31'
       OR is_sterile = FALSE
) AND school_id IS NOT NULL
ORDER BY item_barcode;

-- Step B (EXECUTION): Mark expiring or non-sterile medical kits allocated
-- to schools as 'Needs Inspection'.
UPDATE Global_Equipment
SET current_status = 'Needs Inspection'
WHERE item_barcode IN (
    SELECT item_barcode
    FROM Medical_Kits
    WHERE expiry_date < '2026-12-31'
       OR is_sterile = FALSE
) AND school_id IS NOT NULL;

-- Step C (AFTER Verification): Re-run the identical query; every row must
-- now show current_status = 'Needs Inspection'.
SELECT
    item_barcode,
    brand_model,
    current_status,
    school_id
FROM Global_Equipment
WHERE item_barcode IN (
    SELECT item_barcode
    FROM Medical_Kits
    WHERE expiry_date < '2026-12-31'
       OR is_sterile = FALSE
) AND school_id IS NOT NULL
ORDER BY item_barcode;


-- ----------------------------------------------------------------------------
-- UPDATE Query 3: Skill Rating Bonus for Star Finishers
-- Business Purpose: Increments technical rating by 2 points (capped at 99) for
-- players who registered multiple goals in tournament stages.
-- ----------------------------------------------------------------------------

-- Step A (BEFORE Verification): Show the targeted players and their current
-- technical_rating, using the exact same subquery logic the UPDATE below
-- uses to select its target rows.
SELECT
    student_id,
    first_name,
    last_name,
    technical_rating
FROM Students
WHERE student_id IN (
    SELECT student_id
    FROM (
        SELECT me.student_id
        FROM Match_Events me
        JOIN Matches m ON me.match_id = m.match_id
        WHERE me.event_type = 'Goal'
          AND m.round_stage IN ('Quarter Final', 'Semi Final', 'Final')
        GROUP BY me.student_id
        HAVING COUNT(me.event_id) >= 1
    ) AS top_scorers
)
ORDER BY student_id;

-- Step B (EXECUTION): Award a 2-point technical_rating bonus (capped at 99)
-- to every player who scored a goal in a Quarter Final, Semi Final, or Final.
UPDATE Students
SET technical_rating = LEAST(technical_rating + 2, 99)
WHERE student_id IN (
    SELECT student_id
    FROM (
        SELECT me.student_id
        FROM Match_Events me
        JOIN Matches m ON me.match_id = m.match_id
        WHERE me.event_type = 'Goal'
          AND m.round_stage IN ('Quarter Final', 'Semi Final', 'Final')
        GROUP BY me.student_id
        HAVING COUNT(me.event_id) >= 1
    ) AS top_scorers
);

-- Step C (AFTER Verification): Re-run the identical query; every row must
-- now reflect the +2 rating bonus (capped at 99).
SELECT
    student_id,
    first_name,
    last_name,
    technical_rating
FROM Students
WHERE student_id IN (
    SELECT student_id
    FROM (
        SELECT me.student_id
        FROM Match_Events me
        JOIN Matches m ON me.match_id = m.match_id
        WHERE me.event_type = 'Goal'
          AND m.round_stage IN ('Quarter Final', 'Semi Final', 'Final')
        GROUP BY me.student_id
        HAVING COUNT(me.event_id) >= 1
    ) AS top_scorers
)
ORDER BY student_id;


-- ============================================================================
-- 3. DELETE QUERIES (3 Non-Trivial Queries using Subqueries)
-- Each query is structured as Step A (BEFORE verification SELECT),
-- Step B (the DELETE execution), and Step C (AFTER verification SELECT
-- proving 0 rows remain), so before/after screenshots can be captured for
-- the project report.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DELETE Query 1: Purge Outdated Maintenance Records of Closed Facilities
-- Business Purpose: Removes historical logs of fields permanently marked 'Closed'.
-- ----------------------------------------------------------------------------

-- Step A (BEFORE Verification): Show the maintenance log rows that will be
-- deleted, using the exact same subquery logic the DELETE below uses to
-- select its target rows.
SELECT
    field_id,
    log_date,
    performed_by,
    maintenance_cost
FROM Maintenance_Logs
WHERE field_id IN (
    SELECT field_id
    FROM Fields
    WHERE maintenance_status = 'Closed'
)
ORDER BY field_id, log_date;

-- Step B (EXECUTION): Remove all maintenance history for permanently closed
-- fields.
DELETE FROM Maintenance_Logs
WHERE field_id IN (
    SELECT field_id
    FROM Fields
    WHERE maintenance_status = 'Closed'
);

-- Step C (AFTER Verification): Re-run the identical query; it must now
-- return 0 rows, confirming the deletion succeeded.
SELECT
    field_id,
    log_date,
    performed_by,
    maintenance_cost
FROM Maintenance_Logs
WHERE field_id IN (
    SELECT field_id
    FROM Fields
    WHERE maintenance_status = 'Closed'
)
ORDER BY field_id, log_date;


-- ----------------------------------------------------------------------------
-- DELETE Query 2: Remove Orphaned Events from Postponed / Rescheduled Fixtures
-- Business Purpose: Deletes match event logs mistakenly attributed to postponed games.
-- ----------------------------------------------------------------------------

-- Step A (BEFORE Verification): Show the match event rows that will be
-- deleted, using the exact same subquery logic the DELETE below uses to
-- select its target rows.
SELECT
    event_id,
    match_id,
    student_id,
    event_type,
    minute_in_game
FROM Match_Events
WHERE match_id IN (
    SELECT match_id
    FROM Matches
    WHERE match_status = 'Postponed'
)
ORDER BY event_id;

-- Step B (EXECUTION): Remove event logs tied to matches that were postponed.
DELETE FROM Match_Events
WHERE match_id IN (
    SELECT match_id
    FROM Matches
    WHERE match_status = 'Postponed'
);

-- Step C (AFTER Verification): Re-run the identical query; it must now
-- return 0 rows, confirming the deletion succeeded.
SELECT
    event_id,
    match_id,
    student_id,
    event_type,
    minute_in_game
FROM Match_Events
WHERE match_id IN (
    SELECT match_id
    FROM Matches
    WHERE match_status = 'Postponed'
)
ORDER BY event_id;


-- ----------------------------------------------------------------------------
-- DELETE Query 3: Prune Training Sessions of Inactive Low-Tier Squads
-- Business Purpose: Deletes scheduled practices for U12 teams conducted on unlit fields.
-- ----------------------------------------------------------------------------

-- Step A (BEFORE Verification): Show the practice sessions that will be
-- deleted, using the exact same subquery logic the DELETE below uses to
-- select its target rows.
SELECT
    practice_id,
    team_id,
    field_id,
    practice_date,
    practice_topic
FROM Practices
WHERE team_id IN (
    SELECT team_id
    FROM Teams
    WHERE age_group = 'U12'
)
AND field_id IN (
    SELECT field_id
    FROM Fields
    WHERE has_lighting = 'No'
)
ORDER BY practice_id;

-- Step B (EXECUTION): Remove scheduled practices for U12 teams held on
-- fields without floodlighting.
DELETE FROM Practices
WHERE team_id IN (
    SELECT team_id
    FROM Teams
    WHERE age_group = 'U12'
)
AND field_id IN (
    SELECT field_id
    FROM Fields
    WHERE has_lighting = 'No'
);

-- Step C (AFTER Verification): Re-run the identical query; it must now
-- return 0 rows, confirming the deletion succeeded.
SELECT
    practice_id,
    team_id,
    field_id,
    practice_date,
    practice_topic
FROM Practices
WHERE team_id IN (
    SELECT team_id
    FROM Teams
    WHERE age_group = 'U12'
)
AND field_id IN (
    SELECT field_id
    FROM Fields
    WHERE has_lighting = 'No'
)
ORDER BY practice_id;