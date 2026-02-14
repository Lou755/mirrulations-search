#!/bin/bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIRRSEARCH_SERVICE="mirrsearch.service"
MIRRSEARCH_SERVICE_PATH="/etc/systemd/system/${MIRRSEARCH_SERVICE}"

DOMAIN="dev.mirrulations.org"

cd "${PROJECT_ROOT}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ./.venv/bin/pip install -e .
    ./.venv/bin/pip install -r requirements.txt
fi

sudo ln -sf "${PROJECT_ROOT}/.venv/bin/certbot" /usr/bin/certbot

sudo systemctl stop mirrsearch 2>/dev/null || true

sudo .venv/bin/certbot certonly --standalone -d "${DOMAIN}"

sudo cp "${PROJECT_ROOT}/${MIRRSEARCH_SERVICE}" "${MIRRSEARCH_SERVICE_PATH}"
sudo systemctl daemon-reload
sudo systemctl enable mirrsearch
sudo systemctl restart mirrsearch

sudo systemctl status mirrsearch --no-pager