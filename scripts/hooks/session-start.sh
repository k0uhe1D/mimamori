#!/bin/bash
# scripts/hooks/session-start.sh
# SessionStart Hook: GitHub Issues 読み込み
if command -v gh &> /dev/null; then
  echo "## 現在のオープン Issues"
  gh issue list --limit 10 --state open 2>/dev/null || echo "(gh CLI 未認証)"
fi
