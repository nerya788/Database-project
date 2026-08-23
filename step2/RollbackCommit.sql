USE school_football_db;


-- ============================================================================
-- PART 1: ROLLBACK SCENARIO
-- Business Scenario: A coordinator mistakenly attempts to give every
-- Midfielder at school_id = 1 a maximum technical_rating of 99. The change
-- is caught before it is finalized and is undone with ROLLBACK, proving that
-- an open transaction's writes are not visible/permanent until COMMIT.
-- ============================================================================

START TRANSACTION;

-- Step 1.1: BASELINE STATE
-- Capture the original technical_rating values for every Midfielder at
-- school_id = 1 before any change is made. Keep this result for comparison.
SELECT
    student_id,
    first_name,
    last_name,
    preferred_position,
    technical_rating
FROM Students
WHERE school_id = 1
  AND preferred_position = 'Midfielder'
ORDER BY student_id;

-- Step 1.2: NON-TRIVIAL UPDATE (inside the open transaction)
-- Set technical_rating to 99 for every Midfielder belonging to school_id = 1.
UPDATE Students
SET technical_rating = 99
WHERE school_id = 1
  AND preferred_position = 'Midfielder';

-- Step 1.3: MODIFIED STATE (still inside the same open transaction)
-- Re-run the identical query: every row should now show technical_rating = 99,
-- proving the UPDATE was applied within this transaction's session.
SELECT
    student_id,
    first_name,
    last_name,
    preferred_position,
    technical_rating
FROM Students
WHERE school_id = 1
  AND preferred_position = 'Midfielder'
ORDER BY student_id;

-- Step 1.4: ROLLBACK
-- Discard all changes made since START TRANSACTION. Nothing written in
-- Step 1.2 is persisted to the database.
ROLLBACK;

-- Step 1.5: POST-ROLLBACK VERIFICATION
-- Re-run the identical query one more time (now outside any open write):
-- results must match the Step 1.1 baseline exactly, confirming ROLLBACK
-- fully reverted the transaction's effects.
SELECT
    student_id,
    first_name,
    last_name,
    preferred_position,
    technical_rating
FROM Students
WHERE school_id = 1
  AND preferred_position = 'Midfielder'
ORDER BY student_id;


-- ============================================================================
-- PART 2: COMMIT SCENARIO
-- Business Scenario: School #1 reports a new sports director and an updated
-- contact phone number. The change is validated and permanently saved with
-- COMMIT, proving that a committed transaction's writes survive and become
-- visible to all future sessions.
-- ============================================================================

START TRANSACTION;

-- Step 2.1: BASELINE STATE
-- Capture the original contact details for school_id = 1 before any change.
SELECT
    school_id,
    school_name,
    sports_director_name,
    contact_phone
FROM Schools
WHERE school_id = 1;

-- Step 2.2: VALID UPDATE (inside the open transaction)
-- Update the sports director name and contact phone number for school_id = 1.
UPDATE Schools
SET sports_director_name = 'Noa Peretz',
    contact_phone = '053-7719042'
WHERE school_id = 1;

-- Step 2.3: UPDATED STATE (still inside the same open transaction)
-- Re-run the identical query: the new director name and phone number should
-- already be visible within this transaction's session.
SELECT
    school_id,
    school_name,
    sports_director_name,
    contact_phone
FROM Schools
WHERE school_id = 1;

-- Step 2.4: COMMIT
-- Permanently persist all changes made since START TRANSACTION.
COMMIT;

-- Step 2.5: POST-COMMIT VERIFICATION
-- Re-run the identical query after COMMIT: the new values must still be
-- present, confirming the change is now durable and permanent.
SELECT
    school_id,
    school_name,
    sports_director_name,
    contact_phone
FROM Schools
WHERE school_id = 1;
