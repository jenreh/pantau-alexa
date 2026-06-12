#!/usr/bin/env bash
#
# Start the "tiberio" ngrok tunnel, then publish the S3 endpoint beacon with the
# tunnel's public URL so the AWS edge learns the home server's current address.
#
# Usage:
#   scripts/start-ngrok-beacon.sh
#
# The script keeps ngrok in the foreground; press Ctrl-C to stop it.

set -euo pipefail

TUNNEL_NAME="tiberio"
NGROK_API="http://127.0.0.1:4040/api/tunnels"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${NGROK_PID:-}" ]] && kill -0 "$NGROK_PID" 2>/dev/null; then
    echo "🛑 Stopping ngrok (pid $NGROK_PID)..."
    kill "$NGROK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "🚀 Starting ngrok tunnel '$TUNNEL_NAME'..."
ngrok start "$TUNNEL_NAME" --log=stdout >/tmp/ngrok-"$TUNNEL_NAME".log 2>&1 &
NGROK_PID=$!

echo "⏳ Waiting for the ngrok API to report the public URL..."
PUBLIC_URL=""
for _ in $(seq 1 30); do
  if ! kill -0 "$NGROK_PID" 2>/dev/null; then
    echo "❌ ngrok exited early. Log:" >&2
    cat /tmp/ngrok-"$TUNNEL_NAME".log >&2
    exit 1
  fi
  PUBLIC_URL="$(curl -fsS "$NGROK_API" 2>/dev/null \
    | jq -r --arg name "$TUNNEL_NAME" \
        '.tunnels[] | select(.name == $name and (.public_url | startswith("https"))) | .public_url' \
    | head -n1 || true)"
  [[ -n "$PUBLIC_URL" && "$PUBLIC_URL" != "null" ]] && break
  sleep 1
done

if [[ -z "$PUBLIC_URL" || "$PUBLIC_URL" == "null" ]]; then
  echo "❌ Could not determine the ngrok public URL for '$TUNNEL_NAME'." >&2
  exit 1
fi

echo "🌐 Public URL: $PUBLIC_URL"
echo "📡 Publishing beacon..."
uv run tiberio-beacon publish --base-url "$PUBLIC_URL"

echo "✅ Beacon published. ngrok is running — press Ctrl-C to stop."
wait "$NGROK_PID"
