USE school_football_db;

SELECT 'Schools' AS table_name, COUNT(*) AS total_rows FROM Schools
UNION ALL
SELECT 'Fields', COUNT(*) FROM Fields
UNION ALL
SELECT 'Students', COUNT(*) FROM Students
UNION ALL
SELECT 'Teams', COUNT(*) FROM Teams
UNION ALL
SELECT 'Global_Equipment', COUNT(*) FROM Global_Equipment
UNION ALL
SELECT 'Training_Gear', COUNT(*) FROM Training_Gear
UNION ALL
SELECT 'Medical_Kits', COUNT(*) FROM Medical_Kits
UNION ALL
SELECT 'Practices', COUNT(*) FROM Practices
UNION ALL
SELECT 'Matches', COUNT(*) FROM Matches
UNION ALL
SELECT 'Maintenance_Logs', COUNT(*) FROM Maintenance_Logs
UNION ALL
SELECT 'Match_Events', COUNT(*) FROM Match_Events;


USE school_football_db;

-- 1. בדיקת מגוון שמות ייחודיים בטבלת התלמידים (25,000 רשומות)
SELECT 
    COUNT(DISTINCT first_name) AS unique_first_names,
    COUNT(DISTINCT last_name) AS unique_last_names,
    COUNT(DISTINCT CONCAT(first_name, ' ', last_name)) AS unique_full_names,
    MIN(birth_date) AS oldest_student_birth,
    MAX(birth_date) AS youngest_student_birth,
    ROUND(AVG(technical_rating), 2) AS avg_technical_rating,
    ROUND(AVG(mental_rating), 2) AS avg_mental_rating
FROM Students;

-- 2. בדיקת התפלגות עמדות השחקנים (מוודא פיזור סטטיסטי טבעי)
SELECT preferred_position, COUNT(*) AS total_players,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Students), 2) AS percentage
FROM Students
GROUP BY preferred_position;

-- 3. בדיקת פיזור פריטי הציוד לפי יצרנים ועלויות (טבלה גדולה #2)
SELECT 
    COUNT(DISTINCT item_barcode) AS unique_barcodes,
    COUNT(DISTINCT brand_model) AS unique_models,
    MIN(unit_cost_usd) AS min_price,
    MAX(unit_cost_usd) AS max_price,
    ROUND(AVG(unit_cost_usd), 2) AS avg_price
FROM Global_Equipment;

-- 4. בדיקת התפלגות סטטוס הציוד (מחסן ראשי מול שימוש בבתי ספר)
SELECT current_status, COUNT(*) AS items_count
FROM Global_Equipment
GROUP BY current_status;

-- 5. בדיקת קשרים תקינים במשחקים (מוודא שערים ותוצאות מגוונות)
SELECT 
    COUNT(DISTINCT referee_name) AS unique_referees,
    ROUND(AVG(home_score + away_score), 2) AS avg_goals_per_match,
    MAX(home_score) AS max_home_score,
    MAX(away_score) AS max_away_score
FROM Matches;