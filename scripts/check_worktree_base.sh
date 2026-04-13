#!/usr/bin/env bash
# check_worktree_base.sh -- verify worktree HEAD descends from an expected base commit.
#
# Usage:
#   scripts/check_worktree_base.sh <expected_base_sha>
#
# Exit codes:
#   0 -- HEAD's merge-base with <expected> equals <expected> (worktree is on/after the base)
#   1 -- mismatch; prints remediation hint
#   2 -- bad invocation
#
# This is called by GSD plan executors during parallel wave execution so that each
# worktree agent can confirm it is branched from the orchestrator's expected base
# without pasting raw git plumbing into the shell each time.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <expected_base_sha>" >&2
  exit 2
fi

EXPECTED_BASE="$1"
ACTUAL_BASE="$(git merge-base HEAD "${EXPECTED_BASE}")"

if [[ "${ACTUAL_BASE}" == "${EXPECTED_BASE}" ]]; then
  echo "BASE_OK ${EXPECTED_BASE}"
  exit 0
fi

echo "BASE_MISMATCH" >&2
echo "  expected: ${EXPECTED_BASE}" >&2
echo "  actual:   ${ACTUAL_BASE}" >&2
echo "  remediation: git reset --soft ${EXPECTED_BASE} && git checkout HEAD -- ." >&2
exit 1
