#!/bin/sh
# History scrub: every author and committer address in the reachable history
# must be a noreply address. Run before publishing history; not part of make
# test because rewriting history is a separate, deliberate step.
set -e
cd "$(dirname "$0")/.."

bad=$(git log --all --format='%ae%n%ce' | sort -u | grep -vE '@users\.noreply\.github\.com$|^noreply@anthropic\.com$' || true)
if [ -n "$bad" ]; then
  echo "HISTORY_IDENTITY_FOUND: $(echo "$bad" | wc -l | tr -d ' ') non-noreply address(es) in git log --all"
  exit 1
fi
echo "HISTORY_CLEAN"
