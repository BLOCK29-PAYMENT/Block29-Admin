-- 004: Persisted Payment Hub mappings (references only - no duplicated profile data).
-- Links canonical Block29 Admin merchant/terminal records to their Payment Hub
-- (AsterPOSPaymentHub) identifiers. Written by the admin's Hub linking endpoints;
-- read by readiness checks and Hub panels.

CREATE TABLE IF NOT EXISTS hub_merchant_links (
    merchant_id     VARCHAR(36)  NOT NULL PRIMARY KEY,   -- FK -> merchants.id
    hub_merchant_id VARCHAR(64)  NOT NULL,
    environment     VARCHAR(16)  NOT NULL DEFAULT 'production',
    created_by      VARCHAR(36)  NOT NULL,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NULL,
    UNIQUE KEY uq_hub_merchant (hub_merchant_id, environment)
);

CREATE TABLE IF NOT EXISTS hub_terminal_links (
    terminal_id     VARCHAR(36)  NOT NULL PRIMARY KEY,   -- FK -> terminal_profiles.id
    hub_terminal_id VARCHAR(64)  NOT NULL,
    terminal_serial VARCHAR(64)  NULL,
    environment     VARCHAR(16)  NOT NULL DEFAULT 'production',
    created_by      VARCHAR(36)  NOT NULL,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NULL,
    UNIQUE KEY uq_hub_terminal (hub_terminal_id, environment)
);
