-- ============================================================================
-- Procedure 1: sp_process_player_transfer
-- ----------------------------------------------------------------------------
-- Purpose:
--   Process a fantasy market transfer (BUY or SELL) between a user and the
--   player market, keeping USERS, USER_SQUADS and TRANSACTIONS consistent
--   in a single atomic operation.
--
-- Business logic:
--   BUY:
--     - Player must not already be owned by the user.
--     - Squad must not exceed the 15-player roster limit.
--     - User must have sufficient budget to cover the player's current price.
--     - On success: budget is debited, the player is added to the squad
--       (as 'Bench'), and a BUY transaction is recorded.
--   SELL:
--     - Player must currently be owned by the user.
--     - A 5% resale fee is applied to the player's current market price.
--     - On success: the player is removed from the squad, the budget is
--       credited with the net sale price, and a SELL transaction is
--       recorded.
--
-- Transaction safety:
--   The entire body executes inside an implicit sub-transaction created by
--   the EXCEPTION block. Any validation failure raises an exception, which
--   rolls back every change already made within this call (budget update,
--   squad insert/delete, transaction log) so partial transfers can never be
--   committed.
--
-- Parameters:
--   p_user_id     - fantasy user performing the transfer
--   p_player_id   - target player (student_id)
--   p_action_type - 'BUY' or 'SELL'
--   p_success     - OUT: TRUE if the transfer was completed
--   p_message     - OUT: human-readable outcome description
-- ============================================================================

CREATE OR REPLACE PROCEDURE sp_process_player_transfer(
    IN  p_user_id     INT,
    IN  p_player_id   VARCHAR(10),
    IN  p_action_type VARCHAR(10),
    OUT p_success     BOOLEAN,
    OUT p_message     VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_budget          NUMERIC(12, 2);
    v_price           NUMERIC(10, 2);
    v_squad_count     INT;
    v_squad_record_id INT;
    v_next_squad_id   INT;
    v_next_tx_id      INT;
    v_sell_price      NUMERIC(10, 2);

    c_max_squad_size  CONSTANT INT := 15;
    c_resale_fee_rate CONSTANT NUMERIC(4, 2) := 0.05;
BEGIN
    p_success := FALSE;
    p_message := NULL;

    -- 1. Validate the requested action
    IF p_action_type NOT IN ('BUY', 'SELL') THEN
        RAISE EXCEPTION 'Invalid action type "%": must be BUY or SELL.', p_action_type;
    END IF;

    -- 2. Validate the user exists and lock their budget row for this transfer
    SELECT current_budget INTO v_budget
    FROM USERS
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with ID % does not exist.', p_user_id;
    END IF;

    -- 3. Validate the player exists and fetch the current market price
    SELECT current_price INTO v_price
    FROM Students
    WHERE student_id = p_player_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Player with ID % does not exist.', p_player_id;
    END IF;

    IF p_action_type = 'BUY' THEN
        -- 4a. A player cannot be bought twice by the same user
        SELECT COUNT(*) INTO v_squad_count
        FROM USER_SQUADS
        WHERE user_id = p_user_id AND player_id = p_player_id;

        IF v_squad_count > 0 THEN
            RAISE EXCEPTION 'Player % is already in the squad of User %.', p_player_id, p_user_id;
        END IF;

        -- 4b. Enforce the maximum roster size
        SELECT COUNT(*) INTO v_squad_count
        FROM USER_SQUADS
        WHERE user_id = p_user_id;

        IF v_squad_count >= c_max_squad_size THEN
            RAISE EXCEPTION 'User % squad is full (max % players).', p_user_id, c_max_squad_size;
        END IF;

        -- 4c. Enforce sufficient budget
        IF v_budget < v_price THEN
            RAISE EXCEPTION 'Insufficient budget for User % (budget %, price %).',
                p_user_id, v_budget, v_price;
        END IF;

        -- 4d. Debit the budget
        UPDATE USERS
        SET current_budget = current_budget - v_price
        WHERE user_id = p_user_id;

        -- 4e. Add the player to the squad
        SELECT COALESCE(MAX(squad_record_id), 0) + 1 INTO v_next_squad_id FROM USER_SQUADS;

        INSERT INTO USER_SQUADS (squad_record_id, lineup_status, user_id, player_id)
        VALUES (v_next_squad_id, 'Bench', p_user_id, p_player_id);

        -- 4f. Record the transaction
        SELECT COALESCE(MAX(transaction_id), 0) + 1 INTO v_next_tx_id FROM TRANSACTIONS;

        INSERT INTO TRANSACTIONS (transaction_id, transaction_time, action_type, transaction_price, user_id, player_id)
        VALUES (v_next_tx_id, CURRENT_TIMESTAMP, 'BUY', v_price, p_user_id, p_player_id);

        p_success := TRUE;
        p_message := FORMAT('User %s bought player %s for %s.', p_user_id, p_player_id, v_price);

    ELSE -- SELL
        -- 5a. The player must currently be owned by the user
        SELECT squad_record_id INTO v_squad_record_id
        FROM USER_SQUADS
        WHERE user_id = p_user_id AND player_id = p_player_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Player % is not owned by User %.', p_player_id, p_user_id;
        END IF;

        -- 5b. Apply the resale fee
        v_sell_price := ROUND(v_price * (1 - c_resale_fee_rate), 2);

        -- 5c. Remove the player from the squad
        DELETE FROM USER_SQUADS WHERE squad_record_id = v_squad_record_id;

        -- 5d. Credit the budget
        UPDATE USERS
        SET current_budget = current_budget + v_sell_price
        WHERE user_id = p_user_id;

        -- 5e. Record the transaction
        SELECT COALESCE(MAX(transaction_id), 0) + 1 INTO v_next_tx_id FROM TRANSACTIONS;

        INSERT INTO TRANSACTIONS (transaction_id, transaction_time, action_type, transaction_price, user_id, player_id)
        VALUES (v_next_tx_id, CURRENT_TIMESTAMP, 'SELL', v_sell_price, p_user_id, p_player_id);

        p_success := TRUE;
        p_message := FORMAT('User %s sold player %s for %s (after %s%% fee).',
            p_user_id, p_player_id, v_sell_price, c_resale_fee_rate * 100);
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        p_success := FALSE;
        p_message := SQLERRM;
        RAISE NOTICE 'Transfer failed for User % / Player % (%): %',
            p_user_id, p_player_id, p_action_type, SQLERRM;
END;
$$;

-- ----------------------------------------------------------------------------
-- Test execution
-- ----------------------------------------------------------------------------

-- Buy a player for User 1 (psql displays the OUT parameters as a result row)
CALL sp_process_player_transfer(1, '100000005', 'BUY', NULL, NULL);

-- Attempt to buy the same player again: rejected by the ownership check
CALL sp_process_player_transfer(1, '100000005', 'BUY', NULL, NULL);

-- Sell the player back to the market
CALL sp_process_player_transfer(1, '100000005', 'SELL', NULL, NULL);

-- Verify the resulting state
SELECT user_id, current_budget FROM USERS WHERE user_id = 1;
SELECT * FROM TRANSACTIONS WHERE user_id = 1 ORDER BY transaction_id DESC LIMIT 5;
