#!/usr/bin/env bash

EXPECTED_WORKTREE_BRANCH="feature/PBI3270_Audit_Log"

git_common_dir="$(git rev-parse --git-common-dir 2>/dev/null)"
current_toplevel="$(git rev-parse --show-toplevel 2>/dev/null)"

if [[ -z "$git_common_dir" || -z "$current_toplevel" ]]; then
  echo "WARNING: No git repository detected!"
  exit 2
fi

resolved_common="$(cd "$current_toplevel" && realpath "$git_common_dir")"
resolved_local="$(realpath "$current_toplevel/.git" 2>/dev/null)"

if [[ "$resolved_common" == "$resolved_local" ]]; then
  echo "WARNING: Working in the main repo, NOT in a worktree!"
  echo ""
  git worktree list
  echo ""
  echo "Expected worktree branch: $EXPECTED_WORKTREE_BRANCH"
  exit 2
fi

current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

if [[ "$current_branch" != "$EXPECTED_WORKTREE_BRANCH" ]]; then
  echo "WARNING: In a worktree but on the wrong branch!"
  echo "  Expected: $EXPECTED_WORKTREE_BRANCH"
  echo "  Current:  $current_branch (in $current_toplevel)"
  echo ""
  git worktree list
  exit 2
fi
