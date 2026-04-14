#!/usr/bin/env bash
set -euo pipefail
# SHOULD BE DONE INSIDE OF THE test_mirrulations-search ec2 INSTANCE
# Safe helper for test EC2 deployment flow.
# - Linux-safe DB bootstrap (avoids Homebrew-only script)
# - Ensures postgres localhost password auth
# - Runs production deploy and quick verification

PROJECT_DIR="${1:-$HOME/SEARCHTEST_mirrulations}"
DOMAIN="${2:-test.mirrulations.org}"

echo "Using project: ${PROJECT_DIR}"
echo "Using domain:  ${DOMAIN}"

if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Project directory not found: ${PROJECT_DIR}"
  exit 1
fi

cd "${PROJECT_DIR}"

if [[ ! -f "prod_deploy.sh" ]]; then
  echo "prod_deploy.sh not found in ${PROJECT_DIR}"
  exit 1
fi

echo "Checking domain references..."
if grep -q "dev.mirrulations.org" prod_deploy.sh mirrsearch.service 2>/dev/null; then
  echo "Replacing dev.mirrulations.org -> ${DOMAIN}"
  sed -i "s/dev\.mirrulations\.org/${DOMAIN}/g" prod_deploy.sh || true
  sed -i "s/dev\.mirrulations\.org/${DOMAIN}/g" mirrsearch.service || true
fi

echo "Preparing DB SQL files in /tmp..."
cp db/schema-postgres.sql /tmp/schema-postgres.sql
cp db/sample-data.sql /tmp/sample-data.sql
chmod 644 /tmp/schema-postgres.sql /tmp/sample-data.sql

echo "Creating and loading database..."
sudo -u postgres createdb mirrulations 2>/dev/null || true
sudo -u postgres psql -d mirrulations -f /tmp/schema-postgres.sql
sudo -u postgres psql -d mirrulations -f /tmp/sample-data.sql

echo "Configuring postgres localhost auth..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" >/dev/null
PGDATA=$(sudo -u postgres psql -t -A -c "SHOW data_directory" | tr -d '[:space:]')
sudo sed -i.bak -E 's#^(host[[:space:]]+all[[:space:]]+all[[:space:]]+127\.0\.0\.1/32[[:space:]]+).*$#\1md5#' "$PGDATA/pg_hba.conf"
sudo sed -i.bak -E 's#^(host[[:space:]]+all[[:space:]]+all[[:space:]]+::1/128[[:space:]]+).*$#\1md5#' "$PGDATA/pg_hba.conf"
sudo systemctl restart postgresql || true

echo "Validating DB visibility..."
PGPASSWORD=postgres psql -h localhost -U postgres -lqt postgres | grep -w mirrulations >/dev/null

echo "Running deployment..."
chmod +x prod_deploy.sh
./prod_deploy.sh

echo "Verifying service..."
sudo systemctl status mirrsearch --no-pager || true
curl -Ik "https://${DOMAIN}" || true

echo "Done."
