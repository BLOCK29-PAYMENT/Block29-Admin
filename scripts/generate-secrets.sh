#!/usr/bin/env bash
# Generate strong random secrets for Block29 Admin deployment.
# Run locally; paste the values into your deployment env / secret manager.
# NEVER commit the output.
set -euo pipefail

rand() { openssl rand -base64 48 | tr -d '/+=' | cut -c1-"$1"; }

echo "# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) - store in your secret manager, do not commit"
echo "JWT_SECRET=$(rand 64)"
echo "ADMIN_PASSWORD=$(rand 24)"
echo "# Hub ADMIN_API_KEY - set the SAME value on the Hub (ADMIN_API_KEY) and here:"
echo "PAYMENT_HUB_ADMIN_KEY=$(rand 48)"
echo "# Suggested new MySQL password (apply via ALTER USER on the DB, then set here):"
echo "MYSQL_PASSWORD=$(rand 32)"
