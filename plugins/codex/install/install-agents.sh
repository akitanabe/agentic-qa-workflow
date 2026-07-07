#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  install-agents.sh --user
  install-agents.sh --repo <repo-path>

Copy agentic-qa-workflow Codex custom agents into the selected custom agent directory.

Options:
  --user             Copy to $HOME/.codex/agents
  --repo <path>      Copy to <path>/.codex/agents
  -h, --help         Show this help
USAGE
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
agent_source_dir="$script_dir/agents"

case "${1:-}" in
  --user)
    if [[ $# -ne 1 ]]; then
      usage >&2
      exit 2
    fi
    agent_dir="$HOME/.codex/agents"
    ;;
  --repo)
    if [[ $# -ne 2 ]]; then
      usage >&2
      exit 2
    fi
    agent_dir="$2/.codex/agents"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

required_agents=(
  implementer.toml
  senior-implementer.toml
  responsibility-boundary-reviewer.toml
  refactor-patch-agent.toml
)

for agent in "${required_agents[@]}"; do
  if [[ ! -f "$agent_source_dir/$agent" ]]; then
    echo "Missing bundled agent definition: $agent_source_dir/$agent" >&2
    exit 1
  fi
done

mkdir -p "$agent_dir"

for agent in "${required_agents[@]}"; do
  cp "$agent_source_dir/$agent" "$agent_dir/"
done

cat <<EOF
Copied agentic-qa-workflow custom agents to:
  $agent_dir

Installed agents:
  implementer
  senior-implementer
  responsibility-boundary-reviewer
  refactor-patch-agent

IMPORTANT:
  Restart the Codex session before using these custom agents.
  Do not continue into delegated planning or implementation in this session.
  After restarting, ask again and re-check the custom agent list first.
EOF
