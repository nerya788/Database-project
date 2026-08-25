-- ============================================================================
-- Procedure 2: sp_settle_round
-- ----------------------------------------------------------------------------
-- Purpose:
--   Administrative/analytical round-settlement process. For every player
--   held in a fantasy squad, recompute their market price from real-world
--   match performance, archive the new price into PRICE_HISTORY for the
--   round, and transition the round lifecycle (Active -> Completed, and the
--   next round Upcoming -> Active).
--
-- Business logic:
--   - The target round must exist and currently be 'Active'.
--   - Each player is revalued independently using
--     fn_calculate_player_market_value(); a failure for one player is
--     logged and skipped rather than aborting the whole settlement
--     (error recovery), so a single bad record cannot block the round.
--   - After processing, the round is marked 'Completed' and, if a
--     subsequent round exists and is 'Upcoming', it is activated
--     (conditional handling).
--
-- Parameters:
--   p_round_id           - round being settled
--   p_players_processed  - OUT: number of players successfully revalued
--   p_errors_encountered - OUT: number of players skipped due to errors
-- ============================================================================

CREATE OR REPLACE PROCEDURE sp_settle_round(
    IN  p_round_id           INT,
    OUT p_players_processed  INT,
    OUT p_errors_encountered INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_round_number    INT;
    v_status          VARCHAR(50);
    v_player          RECORD;
    v_new_price       NUMERIC(10, 2);
    v_next_history_id INT;
    v_activated_next  INT := 0;
BEGIN
    p_players_processed := 0;
    p_errors_encountered := 0;

    -- 1. Validate the round exists and is ready to be settled
    SELECT round_number, status INTO v_round_number, v_status
    FROM ROUNDS
    WHERE round_id = p_round_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Round with ID % does not exist.', p_round_id;
    END IF;

    IF v_status <> 'Active' THEN
        RAISE EXCEPTION 'Round % cannot be settled: current status is "%" (must be "Active").',
            p_round_id, v_status;
    END IF;

    -- 2. Prime the PRICE_HISTORY sequence value once, then increment locally
    SELECT COALESCE(MAX(history_id), 0) INTO v_next_history_id FROM PRICE_HISTORY;

    -- 3. Revalue every distinct player currently held in a fantasy squad
    FOR v_player IN
        SELECT DISTINCT player_id FROM USER_SQUADS
    LOOP
        BEGIN
            v_new_price := fn_calculate_player_market_value(v_player.player_id);

            IF v_new_price IS NULL THEN
                RAISE EXCEPTION 'Valuation returned NULL for player %.', v_player.player_id;
            END IF;

            UPDATE Students
            SET current_price = v_new_price
            WHERE student_id = v_player.player_id;

            v_next_history_id := v_next_history_id + 1;

            INSERT INTO PRICE_HISTORY (history_id, recorded_price, player_id, round_id)
            VALUES (v_next_history_id, v_new_price, v_player.player_id, p_round_id);

            p_players_processed := p_players_processed + 1;

        EXCEPTION
            WHEN OTHERS THEN
                -- Error recovery: skip this player, keep settling the rest
                p_errors_encountered := p_errors_encountered + 1;
                RAISE NOTICE 'Skipping player % during settlement of round %: %',
                    v_player.player_id, p_round_id, SQLERRM;
        END;
    END LOOP;

    -- 4. Close out the round
    UPDATE ROUNDS
    SET status = 'Completed'
    WHERE round_id = p_round_id;

    -- 5. Conditionally activate the next round, if one is waiting
    UPDATE ROUNDS
    SET status = 'Active'
    WHERE round_number = v_round_number + 1
      AND status = 'Upcoming';

    GET DIAGNOSTICS v_activated_next = ROW_COUNT;

    RAISE NOTICE 'Round % settled: % players processed, % errors, next round activated: %',
        p_round_id, p_players_processed, p_errors_encountered, (v_activated_next > 0);
END;
$$;

-- ----------------------------------------------------------------------------
-- Test execution
-- ----------------------------------------------------------------------------

-- Settle the currently active round (psql displays the OUT parameters)
CALL sp_settle_round(503, NULL, NULL);

-- Attempt to settle it again: rejected because it is now 'Completed'
CALL sp_settle_round(503, NULL, NULL);

-- Inspect the resulting price history entries for the settled round
SELECT * FROM PRICE_HISTORY WHERE round_id = 503 ORDER BY history_id DESC LIMIT 10;

-- Confirm the round lifecycle transition
SELECT round_id, round_number, status FROM ROUNDS WHERE round_id IN (503, 504);
