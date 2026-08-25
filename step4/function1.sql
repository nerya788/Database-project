CREATE OR REPLACE FUNCTION fn_calculate_player_market_value(
    p_student_id VARCHAR(10)
)
RETURNS NUMERIC(10, 2) AS $$
DECLARE
    v_base_price NUMERIC(10, 2);
    v_total_goals INT := 0;
    v_total_assists INT := 0;
    v_yellow_cards INT := 0;
    v_red_cards INT := 0;
    v_match_count INT := 0;
    v_performance_score NUMERIC(10, 2) := 0.00;
    v_new_price NUMERIC(10, 2) := 0.00;

    -- Record variable for event iteration
    v_event RECORD;
BEGIN
    -- 1. Validate player existence and fetch current price
    SELECT current_price INTO v_base_price
    FROM Students
    WHERE student_id = p_student_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Player with ID % does not exist.', p_student_id;
    END IF;

    -- If price is uninitialized, assign base value
    IF v_base_price IS NULL OR v_base_price <= 0 THEN
        v_base_price := 10.00;
    END IF;

    -- 2. Count distinct matches played (derived from recorded match events)
    SELECT COUNT(DISTINCT match_id) INTO v_match_count
    FROM Match_Events
    WHERE student_id = p_student_id;

    -- 3. Iterate over player match events using a cursor loop
    FOR v_event IN
        SELECT event_type::TEXT AS event_name
        FROM Match_Events
        WHERE student_id = p_student_id
    LOOP
        CASE v_event.event_name
            WHEN 'Goal' THEN
                v_total_goals := v_total_goals + 1;
            WHEN 'Assist' THEN
                v_total_assists := v_total_assists + 1;
            WHEN 'Yellow Card' THEN
                v_yellow_cards := v_yellow_cards + 1;
            WHEN 'Red Card' THEN
                v_red_cards := v_red_cards + 1;
            ELSE
                NULL;
        END CASE;
    END LOOP;

    -- 4. Calculate performance score
    -- Goals: +5.0, Assists: +3.0, Matches: +1.0, Yellow: -1.5, Red: -4.0
    v_performance_score := (v_total_goals * 5.0)
                         + (v_total_assists * 3.0)
                         + (v_match_count * 1.0)
                         - (v_yellow_cards * 1.5)
                         - (v_red_cards * 4.0);

    -- Ensure non-negative performance adjustment
    IF v_performance_score < 0 THEN
        v_performance_score := 0;
    END IF;

    -- 5. Calculate new adjusted price
    v_new_price := ROUND(v_base_price * (1.0 + (v_performance_score / 100.0)), 2);

    RAISE NOTICE 'Player ID: %, Matches: %, Goals: %, Assists: %, Current Price: %, Adjusted Price: %',
        p_student_id, v_match_count, v_total_goals, v_total_assists, v_base_price, v_new_price;

    RETURN v_new_price;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error calculating market value for Student %: %', p_student_id, SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Calculate market value for a specific player
SELECT fn_calculate_player_market_value('100000001');
