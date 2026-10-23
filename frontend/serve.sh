#!/bin/sh
# Local dev: reads API_URL from .env, writes config.js, serves the site on port 8200.
cd "$(dirname "$0")" || exit 1

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
API_URL="${API_URL}"

printf 'window.APP_CONFIG = { API_URL: "%s" };\n' "$API_URL" > config.js
echo "API_URL=$API_URL"
exec python3 -m http.server 8200
