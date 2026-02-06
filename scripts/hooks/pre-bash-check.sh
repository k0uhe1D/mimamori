#!/bin/bash
# scripts/hooks/pre-bash-check.sh
# PreToolUse Hook: 危険コマンドブロック
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 危険なコマンドをブロック
if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/|git\s+push.*--force|git\s+push.*-f'; then
  echo '{"decision": "block", "reason": "危険なコマンドがブロックされました"}'
  exit 0
fi
