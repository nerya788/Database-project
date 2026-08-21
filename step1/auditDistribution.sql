-- =============================================================
-- Project: School Football League Database System
-- Script: auditDistribution.sql
-- Description: Statistical audit of generated data — categorical
--              balance, numeric variance, temporal spread, and
--              duplicate/clustering checks across all 7 tables.
-- =============================================================
USE school_football_db;

-- =====================================================================
-- 1. STUDENTS — name diversity
-- =====================================================================
SELECT first_name, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Students), 2) AS pct
FROM Students GROUP BY first_name ORDER BY cnt DESC LIMIT 20;

SELECT last_name, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Students), 2) AS pct
FROM Students GROUP BY last_name ORDER BY cnt DESC LIMIT 20;

SELECT first_name, last_name, COUNT(*) AS cnt
FROM Students GROUP BY first_name, last_name ORDER BY cnt DESC LIMIT 20;

-- =====================================================================
-- 2. STUDENTS — rating variance (technical/mental)
-- =====================================================================
SELECT
    MIN(technical_rating) AS min_tech, MAX(technical_rating) AS max_tech,
    ROUND(AVG(technical_rating), 2) AS avg_tech, ROUND(STDDEV_POP(technical_rating), 2) AS sd_tech,
    MIN(mental_rating) AS min_mental, MAX(mental_rating) AS max_mental,
    ROUND(AVG(mental_rating), 2) AS avg_mental, ROUND(STDDEV_POP(mental_rating), 2) AS sd_mental
FROM Students;

-- =====================================================================
-- 3. STUDENTS — categorical spread (position / foot)
-- =====================================================================
SELECT preferred_position, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Students), 2) AS pct
FROM Students GROUP BY preferred_position ORDER BY cnt DESC;

SELECT strong_foot, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Students), 2) AS pct
FROM Students GROUP BY strong_foot ORDER BY cnt DESC;

-- =====================================================================
-- 4. STUDENTS — FK clustering check (rows per school)
-- =====================================================================
SELECT MIN(cnt) AS min_per_school, MAX(cnt) AS max_per_school,
       ROUND(AVG(cnt), 2) AS avg_per_school, ROUND(STDDEV_POP(cnt), 2) AS sd_per_school
FROM (SELECT school_id, COUNT(*) AS cnt FROM Students GROUP BY school_id) t;

-- =====================================================================
-- 5. STUDENTS — date clustering (birth_date / join_date)
-- =====================================================================
SELECT birth_date, COUNT(*) AS cnt FROM Students GROUP BY birth_date ORDER BY cnt DESC LIMIT 10;
SELECT join_date,  COUNT(*) AS cnt FROM Students GROUP BY join_date  ORDER BY cnt DESC LIMIT 10;

-- exact duplicate student profiles (same name/attrs, different student_id)
SELECT first_name, last_name, birth_date, school_id, preferred_position,
       strong_foot, join_date, technical_rating, mental_rating, COUNT(*) AS cnt
FROM Students
GROUP BY first_name, last_name, birth_date, school_id, preferred_position,
         strong_foot, join_date, technical_rating, mental_rating
HAVING cnt > 1;

-- =====================================================================
-- 6. GLOBAL_EQUIPMENT — categorical spread
-- =====================================================================
-- item_type no longer exists on Global_Equipment (replaced by the
-- Training_Gear / Medical_Kits specialization); use gear_category / kit_type instead.
SELECT gear_category, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Training_Gear), 2) AS pct
FROM Training_Gear GROUP BY gear_category ORDER BY cnt DESC;

SELECT kit_type, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Medical_Kits), 2) AS pct
FROM Medical_Kits GROUP BY kit_type ORDER BY cnt DESC;

SELECT brand_model, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Global_Equipment), 2) AS pct
FROM Global_Equipment GROUP BY brand_model ORDER BY cnt DESC;

SELECT current_status, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Global_Equipment), 2) AS pct
FROM Global_Equipment GROUP BY current_status ORDER BY cnt DESC;

-- =====================================================================
-- 7. GLOBAL_EQUIPMENT — cost variance & date clustering
-- =====================================================================
SELECT MIN(unit_cost_usd) AS min_cost, MAX(unit_cost_usd) AS max_cost,
       ROUND(AVG(unit_cost_usd), 2) AS avg_cost, ROUND(STDDEV_POP(unit_cost_usd), 2) AS sd_cost
FROM Global_Equipment;

SELECT purchase_date, COUNT(*) AS cnt FROM Global_Equipment GROUP BY purchase_date ORDER BY cnt DESC LIMIT 10;
SELECT shipping_date, COUNT(*) AS cnt FROM Global_Equipment
WHERE shipping_date IS NOT NULL GROUP BY shipping_date ORDER BY cnt DESC LIMIT 10;

SELECT MIN(cnt) AS min_per_school, MAX(cnt) AS max_per_school,
       ROUND(AVG(cnt), 2) AS avg_per_school, ROUND(STDDEV_POP(cnt), 2) AS sd_per_school
FROM (SELECT school_id, COUNT(*) AS cnt FROM Global_Equipment WHERE school_id IS NOT NULL GROUP BY school_id) t;

-- =====================================================================
-- 8. SCHOOLS / FIELDS — categorical spread
-- =====================================================================
SELECT city, COUNT(*) AS cnt FROM Schools GROUP BY city ORDER BY cnt DESC;
SELECT education_network, COUNT(*) AS cnt FROM Schools GROUP BY education_network ORDER BY cnt DESC;
SELECT surface_type, COUNT(*) AS cnt FROM Fields GROUP BY surface_type ORDER BY cnt DESC;
SELECT has_lighting, COUNT(*) AS cnt FROM Fields GROUP BY has_lighting ORDER BY cnt DESC;
SELECT maintenance_status, COUNT(*) AS cnt FROM Fields GROUP BY maintenance_status ORDER BY cnt DESC;

-- =====================================================================
-- 9. TEAMS / PRACTICES / MATCHES — categorical & numeric spread
-- =====================================================================
SELECT age_group, COUNT(*) AS cnt FROM Teams GROUP BY age_group ORDER BY cnt DESC;
SELECT MIN(established_year), MAX(established_year),
       ROUND(AVG(established_year), 2), ROUND(STDDEV_POP(established_year), 2)
FROM Teams;

SELECT practice_topic, COUNT(*) AS cnt FROM Practices GROUP BY practice_topic ORDER BY cnt DESC;
SELECT MIN(duration_minutes), MAX(duration_minutes),
       ROUND(AVG(duration_minutes), 2), ROUND(STDDEV_POP(duration_minutes), 2)
FROM Practices;
SELECT practice_date, COUNT(*) AS cnt FROM Practices GROUP BY practice_date ORDER BY cnt DESC LIMIT 10;

SELECT match_status, COUNT(*) AS cnt FROM Matches GROUP BY match_status ORDER BY cnt DESC;
SELECT round_stage, COUNT(*) AS cnt FROM Matches GROUP BY round_stage ORDER BY cnt DESC;
SELECT MIN(home_score), MAX(home_score), ROUND(AVG(home_score), 2), ROUND(STDDEV_POP(home_score), 2),
       MIN(away_score), MAX(away_score), ROUND(AVG(away_score), 2), ROUND(STDDEV_POP(away_score), 2)
FROM Matches;
SELECT match_date, COUNT(*) AS cnt FROM Matches GROUP BY match_date ORDER BY cnt DESC LIMIT 10;

-- repeated head-to-head matchups (same pair of teams playing more than once)
SELECT LEAST(home_team_id, away_team_id)    AS team_a,
       GREATEST(home_team_id, away_team_id) AS team_b,
       COUNT(*) AS matchup_cnt
FROM Matches
GROUP BY team_a, team_b
HAVING matchup_cnt > 1;
