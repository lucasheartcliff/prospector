#!/usr/bin/env bash
# Export n8n workflows via CLI and commit to git.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXPORT_DIR="$PROJECT_DIR/n8n/workflows"

echo "[$(date -Iseconds)] Exporting n8n workflows..."

# Export all workflows
n8n export:workflow --all --output="$EXPORT_DIR/"

echo "[$(date -Iseconds)] Exported workflows to $EXPORT_DIR"

# Commit if there are changes
cd "$PROJECT_DIR"
if ! git diff --quiet -- n8n/workflows/; then
    git add n8n/workflows/
    git commit -m "chore: update n8n workflow exports"
    echo "[$(date -Iseconds)] Committed workflow changes"
else
    echo "[$(date -Iseconds)] No workflow changes to commit"
fi
