#!/bin/sh
# Runs automatically on startup (nginx image executes /docker-entrypoint.d/*.sh).
# Writes config.js from the API_URL environment variable.
API_URL="${API_URL}"
cat > /usr/share/nginx/html/config.js <<EOF
window.APP_CONFIG = { API_URL: "${API_URL}" };
EOF
