#!/bin/bash
# Claude Code Learning Guide — Mac Launcher
# Usage: ./launch.sh  (or double-click in Finder)

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILE="$DIR/index.html"

if [ ! -f "$FILE" ]; then
  echo "Error: index.html not found at $FILE"
  exit 1
fi

echo "Opening Claude Code Learning Guide..."
open "$FILE"
