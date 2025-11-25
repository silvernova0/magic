#!/usr/bin/env bash
# Quick helper to get raw output from local model
# Usage: ./scripts/debug_model_response.sh [url] [payload]
URL=${1:-http://localhost:8000/api/deck/generate}
PAYLOAD=${2:-scripts/sample_payload.json}

if [ ! -f "$PAYLOAD" ]; then
  echo "Payload file not found: $PAYLOAD"
  exit 1
fi

echo "Posting to $URL with payload $PAYLOAD..."
curl -s -X POST "$URL" -H "Content-Type: application/json" --data-binary "@$PAYLOAD" | head -c 8192; echo "\n"
