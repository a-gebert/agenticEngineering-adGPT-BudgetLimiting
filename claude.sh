#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ROOT="$SCRIPT_DIR/configs"

show_help() {
  echo "Usage: $(basename "$0") <scope> [--hub] [claude args...]"
  echo ""
  echo "Startet Claude Code mit feature-scope-spezifischer Konfiguration."
  echo "Der Layer (Backend/Frontend) wird aus dem aktuellen Verzeichnisnamen abgeleitet."
  echo ""
  echo "Optionen:"
  echo "  --hub    adesso AI Hub als LLM-Backend verwenden (statt Anthropic direkt)"
  echo ""
  echo "Verfügbare Scopes:"
  for dir in "$CONFIG_ROOT"/*/; do
    scope_name="$(basename "$dir")"
    [[ "$scope_name" == "_shared" ]] && continue
    desc=""
    guard="$dir/Backend/hooks/worktree_guard.sh"
    if [[ -f "$guard" ]]; then
      branch=$(grep -oP 'EXPECTED_WORKTREE_BRANCH="\K[^"]+' "$guard" 2>/dev/null)
      [[ -n "$branch" ]] && desc=" ($branch)"
    fi
    echo "  $scope_name$desc"
  done
  echo ""
  echo "Beispiele:"
  echo "  $0 budget-limiting"
  echo "  $0 budget-limiting --hub"
}

SCOPE="$1"

if [[ -z "$SCOPE" || "$SCOPE" == "--help" || "$SCOPE" == "-h" ]]; then
  show_help
  exit 0
fi

shift

USE_HUB=false
if [[ "$1" == "--hub" ]]; then
  USE_HUB=true
  shift
fi

PROJECT_DIR="$PWD"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

CLAUDE_CONFIG_DIR="$CONFIG_ROOT/$SCOPE/$PROJECT_NAME"

if [[ ! -d "$CLAUDE_CONFIG_DIR" ]]; then
  echo "Fehler: Konfiguration nicht gefunden: $CLAUDE_CONFIG_DIR"
  echo ""
  echo "Scope '$SCOPE' existiert nicht oder Layer '$PROJECT_NAME' fehlt."
  echo "Nutze --help für verfügbare Scopes."
  exit 1
fi

export CLAUDE_CONFIG_DIR
export AGPT_ENGINEERING_DIR="$SCRIPT_DIR"

if [[ "$USE_HUB" == true ]]; then
  ENV_FILE="$SCRIPT_DIR/.env.hub"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Fehler: $ENV_FILE nicht gefunden."
    echo "Erstelle die Datei mit den Hub-Credentials (siehe .env.hub.example)."
    exit 1
  fi
  set -a
  source "$ENV_FILE"
  set +a
  echo "→ adesso AI Hub aktiv ($ANTHROPIC_BASE_URL)"
fi

ensure_symlink() {
  local target="$1" link="$2"
  if [[ ! -e "$link" ]]; then
    ln -s "$target" "$link"
  fi
}

SHARED="$CONFIG_ROOT/_shared/$PROJECT_NAME"
if [[ -d "$SHARED" ]]; then
  ensure_symlink "../../_shared/$PROJECT_NAME/CLAUDE.md" "$CLAUDE_CONFIG_DIR/CLAUDE.md"
  ensure_symlink "../../_shared/$PROJECT_NAME/policy-limits.json" "$CLAUDE_CONFIG_DIR/policy-limits.json"
  ensure_symlink "../../_shared/$PROJECT_NAME/skills" "$CLAUDE_CONFIG_DIR/skills"
else
  mkdir -p "$CLAUDE_CONFIG_DIR/skills"
fi

CLAUDE_EXTRA_ARGS=()

SYSTEM_PROMPT_FILE="$CONFIG_ROOT/_shared/system-prompt.md"
if [[ -f "$SYSTEM_PROMPT_FILE" ]]; then
  RENDERED_PROMPT=$(SCOPE="$SCOPE" AGPT_ENGINEERING_DIR="$SCRIPT_DIR" envsubst < "$SYSTEM_PROMPT_FILE")
  CLAUDE_EXTRA_ARGS+=(--append-system-prompt "$RENDERED_PROMPT")
fi

exec claude "${CLAUDE_EXTRA_ARGS[@]}" "$@"
