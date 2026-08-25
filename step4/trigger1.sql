-- ============================================================================
-- Trigger 1: trg_students_price_autocalc
-- ----------------------------------------------------------------------------
-- Purpose:
--   Automatically derive a student's baseline market price from their
--   technical and mental ratings, so the price column is never left
--   inconsistent with a player's rated ability.
--
-- Business logic:
--   - On INSERT: the baseline price is always calculated for the new row.
--   - On UPDATE: the baseline price is recalculated only when
--     technical_rating or mental_rating actually changes, leaving manual
--     round-settlement adjustments (see sp_settle_round /
--     fn_calculate_player_market_value) untouched otherwise.
--   - Formula: 30.00 + technical_rating * 0.70 + mental_rating * 0.30
-- ============================================================================

CREATE OR REPLACE FUNCTION trg_fn_students_recalculate_price()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.current_price := ROUND(30.00 + (NEW.technical_rating * 0.70) + (NEW.mental_rating * 0.30), 2);

    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.technical_rating IS DISTINCT FROM OLD.technical_rating
           OR NEW.mental_rating IS DISTINCT FROM OLD.mental_rating THEN

            NEW.current_price := ROUND(30.00 + (NEW.technical_rating * 0.70) + (NEW.mental_rating * 0.30), 2);
        END IF;
    END IF;

    RETURN NEW;

EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to auto-calculate price for student %: %', NEW.student_id, SQLERRM;
        RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_students_price_autocalc ON Students;

CREATE TRIGGER trg_students_price_autocalc
BEFORE INSERT OR UPDATE ON Students
FOR EACH ROW
EXECUTE FUNCTION trg_fn_students_recalculate_price();

-- ----------------------------------------------------------------------------
-- Test execution
-- ----------------------------------------------------------------------------

-- Insert a new student and observe the auto-calculated baseline price
INSERT INTO Students (
    student_id, first_name, last_name, birth_date, school_id,
    preferred_position, strong_foot, join_date, technical_rating, mental_rating
) VALUES (
    '900000001', 'Test', 'Player', '2012-01-01', 1,
    'Midfielder', 'Right', CURRENT_DATE, 85, 70
);

SELECT student_id, technical_rating, mental_rating, current_price
FROM Students WHERE student_id = '900000001';

-- Update the technical rating: the price is automatically recalculated
UPDATE Students SET technical_rating = 95 WHERE student_id = '900000001';

SELECT student_id, technical_rating, mental_rating, current_price
FROM Students WHERE student_id = '900000001';

-- Update an unrelated column: the price is left untouched
UPDATE Students SET strong_foot = 'Left' WHERE student_id = '900000001';

SELECT student_id, technical_rating, mental_rating, current_price
FROM Students WHERE student_id = '900000001';

-- Cleanup test row
DELETE FROM Students WHERE student_id = '900000001';
