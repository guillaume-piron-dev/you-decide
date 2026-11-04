#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# You Decide: runs state_context.py with the first Python 3.8+ found (python3, py -3, python).
# The Microsoft Store "python3" shortcut on Windows fails the probe and is skipped.
# No network access, no package install. With no Python available, the hook makes no decision.
for interpreter in python3 "py -3" python; do
  if $interpreter -c "import sys; sys.exit(sys.version_info < (3, 8))" </dev/null >/dev/null 2>&1; then
    exec $interpreter "${CLAUDE_PLUGIN_ROOT}/hooks/state_context.py"
  fi
done
exit 0
