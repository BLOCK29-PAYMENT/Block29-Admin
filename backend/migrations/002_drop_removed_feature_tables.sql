-- 002: Drop orphan tables left behind by removed fake/stub features.
-- These features were deleted from the admin (see ADMIN_AUDIT.md):
--   - pos_terminal_links: pairing tokens with no consumer anywhere (nothing ever
--     read or redeemed a token; security-sensitive values should not sit unused)
--   - block29_provisions: gateway provisioning stub (rows only ever said 'submitted')
--   - agent_merchants: half-built affiliates feature (commission rates never used)
--
-- SAFETY: verify no OTHER application (AsterPOS, Chain29, Agent9 backends) reads
-- these tables before dropping. If unsure, rename instead of dropping:
--   RENAME TABLE pos_terminal_links TO _retired_pos_terminal_links;

DROP TABLE IF EXISTS pos_terminal_links;
DROP TABLE IF EXISTS block29_provisions;
DROP TABLE IF EXISTS agent_merchants;
