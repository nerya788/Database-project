CREATE DATABASE IF NOT EXISTS school_football_db;
USE school_football_db;

-- ============================================================================
-- INDEX 1: idx_events_type_student on Match_Events(event_type, student_id)
-- Motivation: Match_Events is the largest associative table and is almost
-- always filtered by event_type first (e.g. 'Goal', 'Yellow Card') and then
-- aggregated per student (see Queries.sql Query 1 and Query 5). Without an
-- index, MySQL must perform a full table scan of Match_Events and build a
-- temporary structure to group by student_id.
-- Access Path Improvement: The composite index lets MySQL (a) seek directly
-- to the matching event_type range instead of scanning every row, and
-- (b) read those rows already ordered by student_id, which MySQL can use
-- for "Using index for group-by" - eliminating both the full table scan
-- and the filesort/temporary table that GROUP BY would otherwise require.
-- ============================================================================

-- 1.0 Safety Guard: drop the index first if it already exists (idempotency)
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Match_Events'
      AND INDEX_NAME = 'idx_events_type_student'
);
SET @sql = IF(@exists > 0,
    'DROP INDEX idx_events_type_student ON Match_Events',
    'SELECT ''idx_events_type_student not present - nothing to drop'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 1.1 BEFORE: representative target query, plan captured with no index present
-- Expected: type = ALL (full table scan of Match_Events) and
-- "Using temporary; Using filesort" for the GROUP BY / ORDER BY.
EXPLAIN
SELECT
    me.student_id,
    COUNT(*) AS total_goals
FROM Match_Events me
WHERE me.event_type = 'Goal'
GROUP BY me.student_id
ORDER BY total_goals DESC;

EXPLAIN ANALYZE
SELECT
    me.student_id,
    COUNT(*) AS total_goals
FROM Match_Events me
WHERE me.event_type = 'Goal'
GROUP BY me.student_id
ORDER BY total_goals DESC;

-- 1.2 Create the strategic composite index
CREATE INDEX idx_events_type_student
ON Match_Events (event_type, student_id);

-- 1.3 AFTER: identical query, plan captured with the index in place
-- Expected: type = ref (or range) on idx_events_type_student, a sharply
-- lower "rows" estimate, and "Using index for group-by" replacing the
-- earlier filesort/temporary step.
EXPLAIN
SELECT
    me.student_id,
    COUNT(*) AS total_goals
FROM Match_Events me
WHERE me.event_type = 'Goal'
GROUP BY me.student_id
ORDER BY total_goals DESC;

EXPLAIN ANALYZE
SELECT
    me.student_id,
    COUNT(*) AS total_goals
FROM Match_Events me
WHERE me.event_type = 'Goal'
GROUP BY me.student_id
ORDER BY total_goals DESC;


-- ============================================================================
-- INDEX 2: idx_students_pos_rating on Students(preferred_position, technical_rating)
-- Motivation: Students is the largest table (25,000+ rows) and coaching/
-- scouting screens repeatedly filter by preferred_position and rank
-- candidates by technical_rating (see Queries.sql Query 1). Without an
-- index, every such lookup requires a full table scan plus a filesort to
-- produce the ranked result.
-- Access Path Improvement: The composite index stores rows pre-sorted by
-- technical_rating within each preferred_position group, so MySQL can seek
-- straight to the requested position and stream rows out in the already-
-- correct order - eliminating the full table scan AND the filesort.
-- ============================================================================

-- 2.0 Safety Guard: drop the index first if it already exists (idempotency)
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Students'
      AND INDEX_NAME = 'idx_students_pos_rating'
);
SET @sql = IF(@exists > 0,
    'DROP INDEX idx_students_pos_rating ON Students',
    'SELECT ''idx_students_pos_rating not present - nothing to drop'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2.1 BEFORE: representative target query, plan captured with no index present
-- Expected: type = ALL (full table scan of Students, ~25,000 rows) and
-- "Using filesort" to satisfy ORDER BY technical_rating DESC.
EXPLAIN
SELECT
    student_id,
    first_name,
    last_name,
    technical_rating
FROM Students
WHERE preferred_position = 'Forward'
ORDER BY technical_rating DESC
LIMIT 20;

EXPLAIN ANALYZE
SELECT
    student_id,
    first_name,
    last_name,
    technical_rating
FROM Students
WHERE preferred_position = 'Forward'
ORDER BY technical_rating DESC
LIMIT 20;

-- 2.2 Create the strategic composite index
CREATE INDEX idx_students_pos_rating
ON Students (preferred_position, technical_rating);

-- 2.3 AFTER: identical query, plan captured with the index in place
-- Expected: type = ref on idx_students_pos_rating, "rows" collapses to
-- roughly the Forward-only subset, and "Using filesort" disappears because
-- the index already returns rows in technical_rating DESC order.
EXPLAIN
SELECT
    student_id,
    first_name,
    last_name,
    technical_rating
FROM Students
WHERE preferred_position = 'Forward'
ORDER BY technical_rating DESC
LIMIT 20;

EXPLAIN ANALYZE
SELECT
    student_id,
    first_name,
    last_name,
    technical_rating
FROM Students
WHERE preferred_position = 'Forward'
ORDER BY technical_rating DESC
LIMIT 20;


-- ============================================================================
-- INDEX 3: idx_matches_stage_status_date on Matches(round_stage, match_status, match_date)
-- Motivation: Tournament/fixture screens filter Matches by round_stage and
-- match_status together and then order the results chronologically (see
-- Queries.sql Query 6). Without an index, MySQL must scan every Matches row
-- and filesort the survivors by match_date.
-- Access Path Improvement: The composite index applies both equality
-- filters (round_stage, then match_status) as an index seek and leaves the
-- matching rows already ordered by match_date, eliminating the full table
-- scan AND the filesort on the ORDER BY clause.
-- ============================================================================

-- 3.0 Safety Guard: drop the index first if it already exists (idempotency)
SET @exists = (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'Matches'
      AND INDEX_NAME = 'idx_matches_stage_status_date'
);
SET @sql = IF(@exists > 0,
    'DROP INDEX idx_matches_stage_status_date ON Matches',
    'SELECT ''idx_matches_stage_status_date not present - nothing to drop'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3.1 BEFORE: representative target query, plan captured with no index present
-- Expected: type = ALL (full table scan of Matches) and "Using filesort"
-- to satisfy ORDER BY match_date DESC.
EXPLAIN
SELECT
    match_id,
    round_stage,
    match_status,
    match_date,
    referee_name
FROM Matches
WHERE round_stage = 'Final'
  AND match_status = 'Completed'
ORDER BY match_date DESC;

EXPLAIN ANALYZE
SELECT
    match_id,
    round_stage,
    match_status,
    match_date,
    referee_name
FROM Matches
WHERE round_stage = 'Final'
  AND match_status = 'Completed'
ORDER BY match_date DESC;

-- 3.2 Create the strategic composite index
CREATE INDEX idx_matches_stage_status_date
ON Matches (round_stage, match_status, match_date);

-- 3.3 AFTER: identical query, plan captured with the index in place
-- Expected: type = ref on idx_matches_stage_status_date, "rows" collapses
-- to only Final/Completed matches, and "Using filesort" disappears because
-- match_date is already the trailing (sorted) column of the index range.
EXPLAIN
SELECT
    match_id,
    round_stage,
    match_status,
    match_date,
    referee_name
FROM Matches
WHERE round_stage = 'Final'
  AND match_status = 'Completed'
ORDER BY match_date DESC;

EXPLAIN ANALYZE
SELECT
    match_id,
    round_stage,
    match_status,
    match_date,
    referee_name
FROM Matches
WHERE round_stage = 'Final'
  AND match_status = 'Completed'
ORDER BY match_date DESC;
