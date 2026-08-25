-- ============================================================================
-- Stage C: Views and Analytical Queries (Views.sql)
-- Depends on step3/Integrate.sql having already been run (Team_Players,
-- current_price, and the 5 partner tables must exist and be populated).
-- Author: Nerya Cohen (ID: 316482801)
-- ============================================================================
USE school_football_db;

-- -------------------------------------------------------------------------
-- View 1 (League Perspective): Player Performance & Market Valuation
-- Links a student to their school and team (via the Team_Players roster
-- junction), their real match performance (goals/cards from Match_Events),
-- their fantasy market price, and how many fantasy users have drafted them.
-- -------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_school_player_market_performance AS
SELECT
    s.student_id,
    CONCAT(s.first_name, ' ', s.last_name) AS full_name,
    sc.school_name,
    t.team_name,
    s.preferred_position,
    s.technical_rating,
    s.mental_rating,
    s.current_price,
    COALESCE(SUM(CASE WHEN me.event_type = 'Goal' THEN 1 ELSE 0 END), 0) AS total_goals,
    COALESCE(SUM(CASE WHEN me.event_type = 'Yellow Card' THEN 1 ELSE 0 END), 0) AS yellow_cards,
    COALESCE(SUM(CASE WHEN me.event_type = 'Red Card' THEN 1 ELSE 0 END), 0) AS red_cards,
    COUNT(DISTINCT us.user_id) AS fantasy_team_selections
FROM Students s
JOIN Schools sc ON s.school_id = sc.school_id
JOIN Team_Players tp ON s.student_id = tp.student_id
JOIN Teams t ON tp.team_id = t.team_id
LEFT JOIN Match_Events me ON s.student_id = me.student_id
LEFT JOIN USER_SQUADS us ON s.student_id = us.player_id
GROUP BY
    s.student_id, s.first_name, s.last_name, sc.school_name,
    t.team_name, s.preferred_position, s.technical_rating,
    s.mental_rating, s.current_price;

SELECT * FROM v_school_player_market_performance LIMIT 10;
-- -------------------------------------------------------------------------
-- View 2 (Fantasy Perspective): User Portfolio & Real-World Team Distribution
-- Links a fantasy user to their squad selections, the market value of that
-- squad, how many distinct real schools are represented in it, and their
-- overall trading activity.
-- -------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_fantasy_user_portfolio_summary AS
SELECT
    u.user_id,
    u.user_name,
    u.current_budget,
    COUNT(DISTINCT us.squad_record_id) AS total_squad_players,
    COUNT(DISTINCT CASE WHEN us.lineup_status = 'Starting XI' THEN us.squad_record_id END) AS starting_players,
    COALESCE(SUM(s.current_price), 0) AS squad_market_value,
    COUNT(DISTINCT s.school_id) AS distinct_schools_represented,
    COUNT(DISTINCT tx.transaction_id) AS total_market_transactions
FROM USERS u
LEFT JOIN USER_SQUADS us ON u.user_id = us.user_id
LEFT JOIN Students s ON us.player_id = s.student_id
LEFT JOIN TRANSACTIONS tx ON u.user_id = tx.user_id
GROUP BY u.user_id, u.user_name, u.current_budget;

SELECT * FROM v_fantasy_user_portfolio_summary LIMIT 10;
-- ============================================================================
-- Queries on View 1 (League Perspective)
-- ============================================================================

-- Query 1.1: Most valuable players / top real-world performers
SELECT
    full_name,
    school_name,
    team_name,
    preferred_position,
    total_goals,
    current_price,
    fantasy_team_selections
FROM v_school_player_market_performance
ORDER BY total_goals DESC, current_price DESC
LIMIT 10;

-- Query 1.2: High-potential undervalued prospects (best rating-per-price)
SELECT
    full_name,
    school_name,
    preferred_position,
    technical_rating,
    current_price,
    ROUND(technical_rating / current_price, 2) AS rating_to_price_ratio
FROM v_school_player_market_performance
WHERE technical_rating >= 80
ORDER BY rating_to_price_ratio DESC
LIMIT 10;


-- ============================================================================
-- Queries on View 2 (Fantasy Perspective)
-- ============================================================================

-- Query 2.1: Top diversified fantasy managers by total net worth
SELECT
    user_name,
    current_budget,
    squad_market_value,
    (current_budget + squad_market_value) AS total_club_net_worth,
    distinct_schools_represented
FROM v_fantasy_user_portfolio_summary
WHERE total_squad_players > 0
ORDER BY total_club_net_worth DESC
LIMIT 10;

-- Query 2.2: Most active trading users
SELECT
    user_name,
    current_budget,
    total_market_transactions,
    squad_market_value
FROM v_fantasy_user_portfolio_summary
WHERE total_market_transactions > 0
ORDER BY total_market_transactions DESC, current_budget DESC
LIMIT 10;


----------------------------------------------------------------------------
-- Quick sanity check: Count rows in each table and view
----------------------------------------------------------------------------
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
SELECT 'Price_History', COUNT(*) FROM PRICE_HISTORY
UNION ALL
SELECT 'View 1 Rows', COUNT(*) FROM v_school_player_market_performance
UNION ALL
SELECT 'View 2 Rows', COUNT(*) FROM v_fantasy_user_portfolio_summary;