#!/usr/bin/env bash
# One-command entry point: creates (or reuses) a Pink sandbox workspace, then
# runs the promptfoo red team against it. See README.md.
#
#   OPENAI_API_KEY=sk-... ./starter/promptfoo/run.sh
#
set -euo pipefail
cd "$(dirname "$0")"

eval "$(python3 setup_workspace.py)"
export PINK_WORKSPACE_ID PINK_AGENT_KEY

GENERATED=".promptfooconfig.local.yaml"
trap 'rm -f "$GENERATED"' EXIT
# promptfoo@0.118.0 does not render {{...}} templates inside MCP auth config,
# so we substitute the real agent key into a gitignored local copy ourselves.
sed "s/PINK_AGENT_KEY_PLACEHOLDER/$PINK_AGENT_KEY/" promptfooconfig.yaml > "$GENERATED"

echo "Workspace: $PINK_WORKSPACE_ID" >&2
echo "Running promptfoo redteam against $PINK_WORKSPACE_ID ..." >&2

# CI=true skips promptfoo's one-time interactive "work email" verification
# prompt (promptfoo@0.118.0 src/envars.js isCI() / src/globalConfig/accounts.js);
# only set for this invocation, not exported to the rest of the shell.
CI=true npx --yes promptfoo@0.118.0 redteam run -c "$GENERATED" "$@"
