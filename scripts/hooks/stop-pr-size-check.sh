#!/bin/bash
# scripts/hooks/stop-pr-size-check.sh
# Stop Hook: PR サイズチェック
CHANGED=$(git diff --stat HEAD~1 2>/dev/null | tail -1 | grep -oP '\d+ insertion' | grep -oP '\d+')
if [ "${CHANGED:-0}" -gt 300 ]; then
  echo "WARNING: 変更が300行を超えています (${CHANGED}行)。PRの分割を検討してください。"
fi
