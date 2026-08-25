-- ============================================================================
-- Stage D - Main Program 1
-- ----------------------------------------------------------------------------
-- Purpose:
--   Standalone anonymous PL/pgSQL block that combines Function 1
--   (fn_calculate_player_market_value) and Procedure 1
--   (sp_process_player_transfer) into a single business scenario.
--
-- Business Scenario:
--   For a target fantasy user (user_id = 1), scan the pool of players NOT
--   yet in that user's squad, starting with the cheapest listed price.
--   For every candidate:
--     1. Compute a performance-adjusted market value with
--        fn_calculate_player_market_value().
--     2. Check whether the user can currently afford that value.
--     3. If affordable, execute the purchase with
--        CALL sp_process_player_transfer(..., 'BUY', ...).
--   The scan stops once a fixed number of players have been purchased
--   (loop control), and every candidate is guarded by conditionals and a
--   nested EXCEPTION handler so a single bad record cannot abort the run.
--
-- Prerequisites (must already be created in the target database):
--   step4/function1.sql   -> fn_calculate_player_market_value
--   step4/procedure1.sql  -> sp_process_player_transfer
-- ============================================================================

DO $$
DECLARE
    v_target_user_id     CONSTANT INT := 1;
    c_max_purchases      CONSTANT INT := 3;

    v_current_budget     NUMERIC(12, 2);
    v_market_value       NUMERIC(10, 2);
    v_success            BOOLEAN;
    v_message            VARCHAR(255);
    v_purchases_made     INT := 0;
    v_candidates_skipped INT := 0;
    v_candidate          RECORD;

    -- Cursor of candidate players: everyone not already owned by the
    -- target user, cheapest listed price first.
    c_candidates CURSOR FOR
        SELECT student_id, first_name, last_name, current_price
        FROM Students
        WHERE student_id NOT IN (
            SELECT player_id FROM USER_SQUADS WHERE user_id = v_target_user_id
        )
        ORDER BY current_price ASC
        LIMIT 20;
BEGIN
    -- 1. Validate the target user exists before scanning any candidates
    SELECT current_budget INTO v_current_budget
    FROM USERS
    WHERE user_id = v_target_user_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Target user % does not exist.', v_target_user_id;
    END IF;

    RAISE NOTICE 'Starting player acquisition scan for user % (budget %). Target: % purchases.',
        v_target_user_id, v_current_budget, c_max_purchases;

    -- 2. Walk the candidate cursor
    OPEN c_candidates;
    LOOP
        FETCH c_candidates INTO v_candidate;
        EXIT WHEN NOT FOUND;

        -- Loop control: stop once the acquisition target has been reached
        EXIT WHEN v_purchases_made >= c_max_purchases;

        -- Nested block: an error on one candidate must not abort the scan
        BEGIN
            -- 2a. Compute the performance-adjusted market value
            v_market_value := fn_calculate_player_market_value(v_candidate.student_id);

            IF v_market_value IS NULL THEN
                v_candidates_skipped := v_candidates_skipped + 1;
                RAISE NOTICE 'Skipping %: market value could not be computed.', v_candidate.student_id;
                CONTINUE;
            END IF;

            -- 2b. Re-check the user's live budget (it changes after every purchase)
            SELECT current_budget INTO v_current_budget
            FROM USERS
            WHERE user_id = v_target_user_id;

            -- 2c. Conditional: only attempt the transfer if it is affordable
            IF v_current_budget >= v_market_value THEN
                CALL sp_process_player_transfer(
                    v_target_user_id,
                    v_candidate.student_id,
                    'BUY',
                    v_success,
                    v_message
                );

                IF v_success THEN
                    v_purchases_made := v_purchases_made + 1;
                    RAISE NOTICE 'Purchase #%: %', v_purchases_made, v_message;
                ELSE
                    v_candidates_skipped := v_candidates_skipped + 1;
                    RAISE NOTICE 'Transfer rejected for %: %', v_candidate.student_id, v_message;
                END IF;
            ELSE
                v_candidates_skipped := v_candidates_skipped + 1;
                RAISE NOTICE 'Cannot afford % (% % vs. current price %, market value %).',
                    v_candidate.first_name, v_candidate.last_name,
                    v_candidate.student_id, v_candidate.current_price, v_market_value;
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                v_candidates_skipped := v_candidates_skipped + 1;
                RAISE NOTICE 'Error evaluating candidate %: %', v_candidate.student_id, SQLERRM;
        END;
    END LOOP;
    CLOSE c_candidates;

    RAISE NOTICE 'Acquisition scan complete for user %: % purchased, % skipped.',
        v_target_user_id, v_purchases_made, v_candidates_skipped;

EXCEPTION
    WHEN OTHERS THEN
        IF c_candidates%ISOPEN THEN
            CLOSE c_candidates;
        END IF;
        RAISE NOTICE 'Main1 aborted for user %: %', v_target_user_id, SQLERRM;
END $$;

-- ============================================================================
-- Inline test / verification queries
-- ============================================================================

-- Current budget after the acquisition scan
SELECT user_id, user_name, current_budget
FROM USERS
WHERE user_id = 1;

-- Most recently added squad entries for the target user
SELECT squad_record_id, lineup_status, player_id
FROM USER_SQUADS
WHERE user_id = 1
ORDER BY squad_record_id DESC
LIMIT 10;

-- Most recent BUY transactions recorded for the target user
SELECT transaction_id, transaction_time, action_type, transaction_price, player_id
FROM TRANSACTIONS
WHERE user_id = 1 AND action_type = 'BUY'
ORDER BY transaction_id DESC
LIMIT 10;

-- Spot-check the adjusted market value for one of the newly bought players
-- (replace '100000005' with a player_id printed by the NOTICE messages above)
-- SELECT fn_calculate_player_market_value('100000005');
