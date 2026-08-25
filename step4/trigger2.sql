-- ============================================================================
-- Trigger 2: trg_users_budget_audit
-- ----------------------------------------------------------------------------
-- Purpose:
--   Enforce a cascading business constraint on USERS.current_budget (it may
--   never go negative) and maintain a permanent audit trail of every
--   budget change, regardless of which routine caused it (e.g. the transfer
--   logic in sp_process_player_transfer).
--
-- Business logic:
--   - BEFORE UPDATE: if the incoming budget is negative, the update is
--     rejected with an exception (state validation), so no code path can
--     ever leave a user with a negative balance.
--   - If the budget actually changed, an audit row is written recording
--     the old value, the new value and the delta.
-- ============================================================================

CREATE TABLE IF NOT EXISTS Budget_Audit_Log (
    audit_id      SERIAL PRIMARY KEY,
    user_id       INT NOT NULL,
    old_budget    DECIMAL(12, 2) NOT NULL,
    new_budget    DECIMAL(12, 2) NOT NULL,
    change_amount DECIMAL(12, 2) NOT NULL,
    changed_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_budget_audit_user
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE OR REPLACE FUNCTION trg_fn_users_budget_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- State validation: budget can never go negative
    IF NEW.current_budget < 0 THEN
        RAISE EXCEPTION 'Update rejected: User % budget cannot go negative (attempted %).',
            OLD.user_id, NEW.current_budget;
    END IF;

    -- Auditing: only log meaningful budget changes
    IF NEW.current_budget IS DISTINCT FROM OLD.current_budget THEN
        INSERT INTO Budget_Audit_Log (user_id, old_budget, new_budget, change_amount)
        VALUES (OLD.user_id, OLD.current_budget, NEW.current_budget, NEW.current_budget - OLD.current_budget);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_budget_audit ON USERS;

CREATE TRIGGER trg_users_budget_audit
BEFORE UPDATE ON USERS
FOR EACH ROW
EXECUTE FUNCTION trg_fn_users_budget_audit();

-- ----------------------------------------------------------------------------
-- Test execution
-- ----------------------------------------------------------------------------

-- Valid update: reduce a user's budget (e.g. after a purchase)
UPDATE USERS SET current_budget = current_budget - 50 WHERE user_id = 1;

SELECT * FROM Budget_Audit_Log WHERE user_id = 1 ORDER BY changed_at DESC LIMIT 5;

-- Invalid update: attempt to drive the budget negative, rejected by the trigger
UPDATE USERS SET current_budget = -100 WHERE user_id = 1;
