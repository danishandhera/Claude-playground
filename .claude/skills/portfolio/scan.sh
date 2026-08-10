#!/usr/bin/env bash
# Portfolio freshness scan — deterministic, ~0 tokens.
# One line per top-level project folder in the Claude-playground repo:
#   PROJECT | LAST_COMMIT | days_ago | LAST_EDIT | days_ago | DIRTY(#uncommitted)
# Used by the /portfolio skill to flag stale + drifted projects.
set -euo pipefail

# --- locate the repo (works on laptop cwd=Claude-home and mobile cwd=repo) ---
if [ $# -ge 1 ]; then
  REPO="$1"
elif git rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO="$(git rev-parse --show-toplevel)"
elif [ -d "./Claude-playground/.git" ]; then
  REPO="$(cd ./Claude-playground && pwd)"
else
  echo "Cannot locate Claude-playground repo; pass its path as arg 1" >&2
  exit 1
fi
cd "$REPO"

now=$(date +%s)

printf "%-16s | %-11s | %6s | %-11s | %6s | %s\n" "PROJECT" "LAST_COMMIT" "d_ago" "LAST_EDIT" "d_ago" "DIRTY"
printf -- "---------------------------------------------------------------------------------\n"

for d in */ ; do
  name="${d%/}"
  [ "$name" = ".git" ] && continue

  # last commit touching this path
  cdate=$(git log -1 --format=%cs -- "$name" 2>/dev/null || echo "")
  if [ -n "$cdate" ]; then
    csecs=$(date -j -f "%Y-%m-%d" "$cdate" +%s 2>/dev/null || echo "$now")
    cdays=$(( (now - csecs) / 86400 ))
  else
    cdate="—"; cdays="—"
  fi

  # newest file mtime under the folder (exclude .git)
  mepoch=$(find "$name" -type f -not -path '*/.git/*' -exec stat -f '%m' {} + 2>/dev/null | sort -rn | head -1 || true)
  if [ -n "${mepoch:-}" ]; then
    medate=$(date -r "$mepoch" +%Y-%m-%d)
    medays=$(( (now - mepoch) / 86400 ))
  else
    medate="—"; medays="—"
  fi

  # uncommitted changes scoped to this path
  dirty=$(git status --porcelain -- "$name" 2>/dev/null | grep -c . || true)

  printf "%-16s | %-11s | %6s | %-11s | %6s | %s\n" "$name" "$cdate" "$cdays" "$medate" "$medays" "$dirty"
done
