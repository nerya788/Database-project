-- ============================================================================
-- Function 2: fn_evaluate_squad_compliance
-- ----------------------------------------------------------------------------
-- Purpose:
--   Evaluate whether a fantasy user's current squad complies with the
--   league's roster rules (maximum squad size, required starting-lineup
--   size) and report the underlying totals (player counts, market value,
--   remaining budget).
--
-- Business logic:
--   - A squad may hold at most 15 players.
--   - Exactly 11 of those players must be marked 'Starting XI'.
--   - Any other player is considered 'Bench'.
--
-- Returns:
--   A composite type (squad_compliance_result) summarizing the evaluation.
--   Demonstrates control flow (IF/CASE), a cursor loop over the user's
--   squad, and exception handling.
-- ============================================================================

DROP TYPE IF EXISTS squad_compliance_result CASCADE;

CREATE TYPE squad_compliance_result AS (
    user_id           INT,
    total_players     INT,
    starting_count    INT,
    bench_count       INT,
    squad_value       NUMERIC(12, 2),
    current_budget    NUMERIC(12, 2),
    is_compliant      BOOLEAN,
    status_message    VARCHAR(255)
);

CREATE OR REPLACE FUNCTION fn_evaluate_squad_compliance(
    p_user_id INT
)
RETURNS squad_compliance_result AS $$
DECLARE
    v_result             squad_compliance_result;
    v_budget             NUMERIC(12, 2);
    v_squad_row          RECORD;
    v_total_players      INT := 0;
    v_starting           INT := 0;
    v_bench              INT := 0;
    v_squad_value        NUMERIC(12, 2) := 0.00;

    c_max_squad_size     CONSTANT INT := 15;
    c_required_starters  CONSTANT INT := 11;
BEGIN
    -- 1. Validate that the fantasy user exists and fetch their budget
    SELECT current_budget INTO v_budget
    FROM USERS
    WHERE user_id = p_user_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with ID % does not exist.', p_user_id;
    END IF;

    -- 2. Walk the user's squad with a cursor loop, classifying each player
    --    by lineup status and accumulating total market value
    FOR v_squad_row IN
        SELECT us.lineup_status, s.current_price
        FROM USER_SQUADS us
        JOIN Students s ON s.student_id = us.player_id
        WHERE us.user_id = p_user_id
    LOOP
        v_total_players := v_total_players + 1;
        v_squad_value := v_squad_value + COALESCE(v_squad_row.current_price, 0);

        CASE v_squad_row.lineup_status
            WHEN 'Starting XI' THEN
                v_starting := v_starting + 1;
            WHEN 'Bench' THEN
                v_bench := v_bench + 1;
            ELSE
                NULL;
        END CASE;
    END LOOP;

    -- 3. Populate the result and apply league compliance rules
    v_result.user_id := p_user_id;
    v_result.total_players := v_total_players;
    v_result.starting_count := v_starting;
    v_result.bench_count := v_bench;
    v_result.squad_value := v_squad_value;
    v_result.current_budget := v_budget;

    IF v_total_players = 0 THEN
        v_result.is_compliant := FALSE;
        v_result.status_message := 'No players registered in squad.';
    ELSIF v_total_players > c_max_squad_size THEN
        v_result.is_compliant := FALSE;
        v_result.status_message := FORMAT('Squad exceeds maximum size of %s players.', c_max_squad_size);
    ELSIF v_starting <> c_required_starters THEN
        v_result.is_compliant := FALSE;
        v_result.status_message := FORMAT(
            'Starting lineup must contain exactly %s players (found %s).',
            c_required_starters, v_starting
        );
    ELSE
        v_result.is_compliant := TRUE;
        v_result.status_message := 'Squad meets all roster requirements.';
    END IF;

    RETURN v_result;

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error evaluating squad compliance for User %: %', p_user_id, SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- Test execution
-- ----------------------------------------------------------------------------

-- Evaluate squad compliance for a sample fantasy user
SELECT * FROM fn_evaluate_squad_compliance(1);

-- Non-existent user: exercises the validation / error-handling path
SELECT * FROM fn_evaluate_squad_compliance(999999);
