#!/usr/bin/env bash
# Block29 Admin - migration runner.
# Run from a machine that can reach the MySQL server (the admin host itself).
# Reads connection settings from backend/.env or the environment.
#
# NOTE: 001/004/005 also run AUTOMATICALLY at backend startup on every deploy
# (server.py run_startup_migrations), so this script is only strictly needed
# for the gated destructive steps below - or to apply 001/004/005 ahead of a
# deploy.
#
# Behavior:
#   001 (users.is_active)        - applied automatically if the column is missing
#   004 (hub link tables)        - applied automatically (CREATE IF NOT EXISTS)
#   005 (disable legacy admin)   - applied automatically (deactivates admin@salonbookin.com)
#   003 (fake VT transactions)   - COUNT shown; archive+delete only with --cleanup-fake-tx
#   002 (drop orphan tables)     - only with --drop-orphans (verify no other app uses them!)
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f backend/.env ] && set -a && . backend/.env && set +a
: "${MYSQL_HOST:?set MYSQL_HOST}" "${MYSQL_USER:?set MYSQL_USER}" "${MYSQL_PASSWORD:?set MYSQL_PASSWORD}" "${MYSQL_DATABASE:?set MYSQL_DATABASE}"
MYSQL_PORT="${MYSQL_PORT:-3306}"

q() { MYSQL_PWD="$MYSQL_PASSWORD" mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -D "$MYSQL_DATABASE" -N -B -e "$1"; }

echo "== 001: users.is_active =="
HAS_COL=$(q "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$MYSQL_DATABASE' AND TABLE_NAME='users' AND COLUMN_NAME='is_active'")
if [ "$HAS_COL" = "0" ]; then
  q "ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1"
  echo "   added is_active column"
else
  echo "   already present - skipped"
fi

echo "== 004: hub link tables =="
q "CREATE TABLE IF NOT EXISTS hub_merchant_links (merchant_id VARCHAR(36) NOT NULL PRIMARY KEY, hub_merchant_id VARCHAR(64) NOT NULL, environment VARCHAR(16) NOT NULL DEFAULT 'production', created_by VARCHAR(36) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NULL, UNIQUE KEY uq_hub_merchant (hub_merchant_id, environment))"
q "CREATE TABLE IF NOT EXISTS hub_terminal_links (terminal_id VARCHAR(36) NOT NULL PRIMARY KEY, hub_terminal_id VARCHAR(64) NOT NULL, terminal_serial VARCHAR(64) NULL, environment VARCHAR(16) NOT NULL DEFAULT 'production', created_by VARCHAR(36) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NULL, UNIQUE KEY uq_hub_terminal (hub_terminal_id, environment))"
echo "   ensured"

echo "== 005: disable legacy publicly-exposed admin account =="
q "UPDATE users SET is_active = 0 WHERE email = 'admin@salonbookin.com'"
echo "   admin@salonbookin.com deactivated (if it existed)"

echo "== 003: fake Virtual Terminal transactions =="
FAKE=$(q "SELECT COUNT(*) FROM transactions WHERE terminal_id='VIRTUAL'")
echo "   $FAKE fake row(s) found (terminal_id='VIRTUAL')"
if [ "${1:-}" = "--cleanup-fake-tx" ] && [ "$FAKE" != "0" ]; then
  q "CREATE TABLE IF NOT EXISTS _archived_virtual_terminal_tx AS SELECT * FROM transactions WHERE terminal_id='VIRTUAL'"
  q "DELETE FROM transactions WHERE terminal_id='VIRTUAL'"
  echo "   archived to _archived_virtual_terminal_tx and deleted"
else
  echo "   NOT deleted (re-run with --cleanup-fake-tx after reviewing)"
fi

if [ "${1:-}" = "--drop-orphans" ] || [ "${2:-}" = "--drop-orphans" ]; then
  echo "== 002: dropping orphan tables (pos_terminal_links, block29_provisions, agent_merchants) =="
  q "DROP TABLE IF EXISTS pos_terminal_links"
  q "DROP TABLE IF EXISTS block29_provisions"
  q "DROP TABLE IF EXISTS agent_merchants"
  echo "   dropped"
else
  echo "== 002: orphan tables NOT dropped (verify no other app reads them, then re-run with --drop-orphans) =="
fi

echo "All done."
