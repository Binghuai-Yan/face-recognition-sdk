#!/usr/bin/env bash
set -euo pipefail
api_url="${FACESDK_API_URL:-http://localhost:8000}"
# The consistence endpoint checks API -> PostgreSQL and API -> Core.
curl --fail --silent --show-error --max-time 15 \
  "${api_url%/}/api/v1/consistence/status" |
  python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if data.get("status") == "OK" else 1)'
echo 'CompreFace API, database and core are healthy.'
