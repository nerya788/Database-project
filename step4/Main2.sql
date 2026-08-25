-- ============================================================================
-- Stage D - Main Program 2
-- ----------------------------------------------------------------------------
-- Purpose:
--   Standalone anonymous PL/pgSQL block that combines Function 2
--   (fn_evaluate_squad_compliance) and Procedure 2 (sp_settle_round) into a
--   single business scenario.
--
-- Business Scenario:
--   Iterate through every active fantasy user (a user who currently holds
--   at least one squad slot), evaluate each squad's roster compliance with
--   fn_evaluate_squad_compliance(), and accumulate summary statistics
--   (total squad market value, compliant vs. non-compliant counts). Once
--   the compliance sweep is done, log the summary and, as the follow-up
--   administrative action, locate the currently 'Active' round and trigger
--   its settlement with CALL sp_settle_round(...).
--
-- Prerequisites (must already be created in the target database):
--   step4/function2.sql   -> squad_compliance_result, fn_evaluate_squad_compliance
--   step4/procedure2.sql  -> sp_settle_round
-- ============================================================================

DO $$
DECLARE
    c_max_users_to_scan  CONSTANT INT := 25;

    v_compliance         squad_compliance_result;
    v_user               RECORD;
    v_users_scanned      INT := 0;
    v_compliant_count    INT := 0;
    v_non_compliant_count INT := 0;
    v_total_squad_value  NUMERIC(14, 2) := 0.00;

    v_round_id           INT;
    v_round_number       INT;
    v_players_processed  INT;
    v_errors_encountered INT;

    -- Cursor of active users: anyone who currently owns at least one player
    c_active_users CURSOR FOR
        SELECT DISTINCT u.user_id, u.user_name
        FROM USERS u
        JOIN USER_SQUADS us ON us.user_id = u.user_id
        ORDER BY u.user_id;
BEGIN
    RAISE NOTICE 'Starting squad compliance sweep (scanning up to % active users).',
        c_max_users_to_scan;

    -- 1. Walk the active-user cursor and evaluate each squad
    OPEN c_active_users;
    LOOP
        FETCH c_active_users INTO v_user;
        EXIT WHEN NOT FOUND;

        -- Loop control: cap the sweep so the demo stays bounded
        EXIT WHEN v_users_scanned >= c_max_users_to_scan;

        -- Nested block: one user's evaluation error must not abort the sweep
        BEGIN
            v_compliance := fn_evaluate_squad_compliance(v_user.user_id);

            IF v_compliance IS NULL THEN
                RAISE NOTICE 'Could not evaluate squad for user % (%).',
                    v_user.user_id, v_user.user_name;
                CONTINUE;
            END IF;

            v_users_scanned := v_users_scanned + 1;
            v_total_squad_value := v_total_squad_value + COALESCE(v_compliance.squad_value, 0);

            -- Conditional: split users into compliant vs. non-compliant buckets
            IF v_compliance.is_compliant THEN
                v_compliant_count := v_compliant_count + 1;
            ELSE
                v_non_compliant_count := v_non_compliant_count + 1;
                RAISE NOTICE 'User % (%) is NON-COMPLIANT: %',
                    v_user.user_id, v_user.user_name, v_compliance.status_message;
            END IF;

        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Error evaluating squad for user %: %', v_user.user_id, SQLERRM;
        END;
    END LOOP;
    CLOSE c_active_users;

    -- 2. Log summary statistics for the sweep
    RAISE NOTICE 'Compliance sweep complete: % users scanned, % compliant, % non-compliant, total squad value %.',
        v_users_scanned, v_compliant_count, v_non_compliant_count, v_total_squad_value;

    -- 3. Locate the currently active round and trigger settlement
    SELECT round_id, round_number INTO v_round_id, v_round_number
    FROM ROUNDS
    WHERE status = 'Active'
    ORDER BY round_number
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE NOTICE 'No active round found - settlement skipped.';
    ELSE
        RAISE NOTICE 'Settling round % (round number %)...', v_round_id, v_round_number;

        CALL sp_settle_round(v_round_id, v_players_processed, v_errors_encountered);

        RAISE NOTICE 'Round % settled: % players processed, % errors encountered.',
            v_round_id, v_players_processed, v_errors_encountered;
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        IF c_active_users%ISOPEN THEN
            CLOSE c_active_users;
        END IF;
        RAISE NOTICE 'Main2 aborted: %', SQLERRM;
END $$;

-- ============================================================================
-- Inline test / verification queries
-- ============================================================================

-- Round lifecycle after settlement (the settled round should be 'Completed'
-- and, if one was waiting, the next round should now be 'Active')
SELECT round_id, round_number, status
FROM ROUNDS
ORDER BY round_number;

-- Count of rounds per status
SELECT status, COUNT(*) AS round_count
FROM ROUNDS
GROUP BY status
ORDER BY status;

-- Most recent price history entries written by the settlement
SELECT history_id, player_id, round_id, recorded_price
FROM PRICE_HISTORY
ORDER BY history_id DESC
LIMIT 10;

-- Re-run the compliance check for a specific user to confirm the function
-- still reflects the current squad state
SELECT * FROM fn_evaluate_squad_compliance(1);
