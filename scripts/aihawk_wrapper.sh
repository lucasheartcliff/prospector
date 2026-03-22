#!/usr/bin/env bash
# Wrapper script to run AIHawk with Prospector config and POST results to n8n.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
AIHAWK_DIR="${AIHAWK_DIR:-$HOME/aihawk}"
N8N_WEBHOOK="${N8N_WEBHOOK:-http://localhost:5678/webhook/easy-apply}"
MAX_APPLICATIONS="${MAX_APPLICATIONS:-25}"

# Load environment
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "[$(date -Iseconds)] Starting AIHawk run (max: $MAX_APPLICATIONS)"

cd "$AIHAWK_DIR"

# Run AIHawk and capture output
OUTPUT_FILE=$(mktemp)
python main.py --max-applications "$MAX_APPLICATIONS" 2>&1 | tee "$OUTPUT_FILE"

# Parse applied jobs from AIHawk output and POST to n8n
python3 -c "
import json, re, sys
import urllib.request

lines = open('$OUTPUT_FILE').readlines()
applied = []
for line in lines:
    match = re.search(r'Applied to (.+?) at (.+?) - (.+)', line)
    if match:
        applied.append({
            'title': match.group(1).strip(),
            'company': match.group(2).strip(),
            'url': match.group(3).strip(),
        })

if applied:
    data = json.dumps(applied).encode()
    req = urllib.request.Request('$N8N_WEBHOOK', data=data, headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req)
    print(f'Posted {len(applied)} applications to n8n')
else:
    print('No applications to report')
"

rm -f "$OUTPUT_FILE"
echo "[$(date -Iseconds)] AIHawk run complete"
