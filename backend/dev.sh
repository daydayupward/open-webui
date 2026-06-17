export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
PORT="${PORT:-8080}"

# Load or generate WEBUI_SECRET_KEY to satisfy authentication requirements
KEY_FILE="${WEBUI_SECRET_KEY_FILE:-.webui_secret_key}"
if [ -z "${WEBUI_SECRET_KEY:-}" ] && [ -z "${WEBUI_JWT_SECRET_KEY:-}" ]; then
  if [ ! -f "$KEY_FILE" ]; then
    echo "Generating new WEBUI_SECRET_KEY..."
    head -c 12 /dev/random | base64 > "$KEY_FILE" 2>/dev/null || openssl rand -base64 12 > "$KEY_FILE" 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(12))" > "$KEY_FILE"
  fi
  export WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" --reload

