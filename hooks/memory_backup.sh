#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# You Decide: before a compaction, runs the memory script's PreCompact entry point with the first Python 3.8+ found.
# It does nothing unless the project has docs/memory/config.json. No network access, no package install.
for interpreter in python3 "py -3" python; do
  if $interpreter -c "import sys; sys.exit(sys.version_info < (3, 8))" </dev/null >/dev/null 2>&1; then
    exec $interpreter "${CLAUDE_PLUGIN_ROOT}/skills/memory/scripts/yd_memory.py" hook-precompact
  fi
done
exit 0
