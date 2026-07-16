#!/usr/bin/env bash
set -euo pipefail

# Show supported scopes and overwrite-control options.
usage() {
  cat <<'USAGE'
Usage:
  install-agents.sh [--check | --force] --user
  install-agents.sh [--check | --force] --repo <repo-path>

Copy agentic-qa-workflow Codex custom agents into the selected custom agent directory.

Options:
  --check            Report installation and version status without changing files
  --force            Explicitly overwrite an existing or outdated installation
  --user             Copy to $HOME/.codex/agents
  --repo <path>      Copy to <path>/.codex/agents
  -h, --help         Show this help
USAGE
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
agent_source_dir="$script_dir/agents"
version_file="$script_dir/VERSION"
installed_version_file_name=".agentic-qa-workflow-version"
mode="install"
scope=""
repo_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      [[ "$mode" == "install" ]] || { usage >&2; exit 2; }
      mode="check"
      shift
      ;;
    --force)
      [[ "$mode" == "install" ]] || { usage >&2; exit 2; }
      mode="force"
      shift
      ;;
    --user)
      [[ -z "$scope" ]] || { usage >&2; exit 2; }
      scope="user"
      shift
      ;;
    --repo)
      [[ -z "$scope" && $# -ge 2 ]] || { usage >&2; exit 2; }
      scope="repo"
      repo_path="$2"
      shift 2
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
done

[[ -n "$scope" ]] || { usage >&2; exit 2; }
if [[ "$scope" == "user" ]]; then
  agent_dir="$HOME/.codex/agents"
else
  agent_dir="$repo_path/.codex/agents"
fi

required_agents=(
  implementer.toml
  senior-implementer.toml
  responsibility-boundary-reviewer.toml
  test-quality-reviewer.toml
  writing-principles-refactorer.toml
  security-side-effect-reviewer.toml
  review-patch-refactorer.toml
)

if [[ ! -f "$version_file" ]]; then
  echo "Missing bundled version: $version_file" >&2
  exit 1
fi

bundled_version="$(<"$version_file")"

for agent in "${required_agents[@]}"; do
  if [[ ! -f "$agent_source_dir/$agent" ]]; then
    echo "Missing bundled agent definition: $agent_source_dir/$agent" >&2
    exit 1
  fi
done

installed_version="not installed"
if [[ -f "$agent_dir/$installed_version_file_name" ]]; then
  installed_version="$(<"$agent_dir/$installed_version_file_name")"
else
  for agent in "${required_agents[@]}"; do
    if [[ -e "$agent_dir/$agent" ]]; then
      installed_version="unknown"
      break
    fi
  done
fi

is_up_to_date=true
if [[ "$installed_version" != "$bundled_version" ]]; then
  is_up_to_date=false
fi
for agent in "${required_agents[@]}"; do
  if [[ ! -f "$agent_dir/$agent" ]] || ! cmp -s "$agent_source_dir/$agent" "$agent_dir/$agent"; then
    is_up_to_date=false
  fi
done

if [[ "$is_up_to_date" == true ]]; then
  echo "Custom agents are up to date (version $bundled_version): $agent_dir"
  exit 0
fi

cat <<EOF
Custom agent update status:
  installed version: $installed_version
  bundled version:   $bundled_version
  target:            $agent_dir
EOF

if [[ "$mode" == "check" ]]; then
  exit 3
fi

if [[ "$installed_version" != "not installed" && "$mode" != "force" ]]; then
  echo "Existing custom agents were not changed. Confirm the overwrite explicitly, then rerun with --force." >&2
  exit 3
fi

mkdir -p "$agent_dir"

for agent in "${required_agents[@]}"; do
  cp "$agent_source_dir/$agent" "$agent_dir/"
done
printf '%s\n' "$bundled_version" > "$agent_dir/$installed_version_file_name"

cat <<EOF
Installed agentic-qa-workflow custom agents version $bundled_version to:
  $agent_dir

Installed agents:
  implementer
  senior-implementer
  responsibility-boundary-reviewer
  test-quality-reviewer
  writing-principles-refactorer
  security-side-effect-reviewer
  review-patch-refactorer

IMPORTANT:
  Restart the Codex session before using these custom agents.
  Do not continue into delegated planning or implementation in this session.
  After restarting, ask again and re-check the custom agent list first.
EOF
