#!/bin/sh
# Publish scrub: no user-specific paths, personal addresses or key material in
# tracked files.
#
# Generic patterns live here: user home paths, personal notes folders
# (~/vault, ~/memory), personal mail addresses and key shapes. Private tokens
# (client and employer names, hostnames) belong in .scrub-private (gitignored,
# one ERE per line) so the scanner never publishes what it scans for. This
# file is the one tracked file excluded from the scan, so review it by hand.
set -e
cd "$(dirname "$0")/.."

SECRETS='BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-|hf_[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,}'
PATHS='/Users/[a-z]+/|~/vault|~/memory|vault-vps'
MAIL='[A-Za-z0-9._%+-]+@(gmail|googlemail|outlook|hotmail|icloud|me|yahoo|proton|protonmail)\.[a-z]+'
GENERIC="$SECRETS|$PATHS|$MAIL"
PATTERN="$GENERIC"
if [ -f .scrub-private ]; then
  PRIVATE=$(grep -vE '^[[:space:]]*(#|$)' .scrub-private | paste -sd'|' -)
  [ -n "$PRIVATE" ] && PATTERN="$GENERIC|$PRIVATE"
fi

# Placeholders that stay: /Users/you/, /Users/example/, example.com addresses.
strip() { sed -E 's#/Users/(you|example|name)/##g; s#[A-Za-z0-9._%+-]+@example\.(com|org)##g' "$1"; }

scan() { for f in "$@"; do strip "$f" | grep -E "$PATTERN" | sed "s#^#$f:#" || true; done; }

control=$(mktemp)
printf '/Users/nobody/leak\n' > "$control"
if [ -z "$(scan "$control")" ]; then
  echo "SCRUB_SELFTEST_FAILED"; rm -f "$control"; exit 1
fi
printf 'person@gmail.com\n' > "$control"
if [ -z "$(scan "$control")" ]; then
  echo "SCRUB_SELFTEST_FAILED"; rm -f "$control"; exit 1
fi
rm -f "$control"

hits=$(git ls-files | grep -v '^tests/scrub\.sh$' | while IFS= read -r f; do
  [ -n "$(scan "$f")" ] && echo "$f"
done || true)
if [ -n "$hits" ]; then
  echo "PRIVATE CONTENT FOUND:"
  echo "$hits"
  exit 1
fi
echo "SCRUB_CLEAN"
