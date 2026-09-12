-- 001: Ensure the canonical users schema has is_active.
-- The application treats a missing/NULL is_active as active (1); this migration
-- makes the column explicit so deactivation works without application fallbacks.
--
-- Check first (MySQL has no ADD COLUMN IF NOT EXISTS before 8.0.29 on all forks):
--   SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
--   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'is_active';
-- If the query returns no row, run:

ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;

-- Canonical users schema used by the application (do not reintroduce
-- password_hash/business_name variants - login, register, and seeding all
-- read/write these columns):
--   id          VARCHAR(36) PK
--   email       VARCHAR(255) UNIQUE
--   password    VARCHAR(255)  -- bcrypt hash
--   name        VARCHAR(255)
--   role        VARCHAR(32)   -- SUPER_ADMIN | OPERATIONS | SUPPORT | READ_ONLY
--   is_active   TINYINT(1) DEFAULT 1
--   created_at  DATETIME
