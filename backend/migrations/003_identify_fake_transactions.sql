-- 003: Identify (NOT auto-delete) fake transactions created by the removed
-- Virtual Terminal simulator.
--
-- How fake rows are identified: the simulator always wrote terminal_id = 'VIRTUAL'
-- and entry_mode = 'KEYED', with random auth codes. No real feature ever wrote
-- terminal_id = 'VIRTUAL'.
--
-- Step 1 - count them:
SELECT COUNT(*) AS fake_rows, MIN(created_at) AS first, MAX(created_at) AS last
FROM transactions
WHERE terminal_id = 'VIRTUAL';

-- Step 2 - review them:
--   SELECT * FROM transactions WHERE terminal_id = 'VIRTUAL' ORDER BY created_at DESC;

-- Step 3 - after owner review, archive then delete (run manually, NOT automated):
--   CREATE TABLE _archived_virtual_terminal_tx AS
--     SELECT * FROM transactions WHERE terminal_id = 'VIRTUAL';
--   DELETE FROM transactions WHERE terminal_id = 'VIRTUAL';
--
-- Until this cleanup runs, dashboard/report numbers include these simulator rows.
