#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$repo_root/plugins/codex/install/install-agents.sh"
expected_version="$(cat "$repo_root/plugins/codex/install/VERSION")"
plugin_version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$repo_root/plugins/codex/.codex-plugin/plugin.json")"
required_agents=(
  implementer
  senior-implementer
  responsibility-boundary-reviewer
  test-quality-reviewer
  writing-principles-refactorer
  security-side-effect-reviewer
  review-patch-refactorer
)

# Fail the test with a concise diagnostic.
fail() {
  echo "FAIL: $*" >&2
  exit 1
}

# Assert that two files have identical content.
assert_same() {
  cmp -s "$1" "$2" || fail "$1 and $2 differ"
}

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
target_repo="$tmp_dir/repo"
mkdir -p "$target_repo/.codex/agents"
printf '%s\n' 'name = "unrelated"' > "$target_repo/.codex/agents/unrelated.toml"

[[ "$plugin_version" == "$expected_version" ]] || fail "plugin and custom-agent versions differ"

install_output="$("$installer" --repo "$target_repo")"
agent_dir="$target_repo/.codex/agents"
[[ -f "$agent_dir/unrelated.toml" ]] || fail "unrelated agent was removed"
[[ "$(cat "$agent_dir/.agentic-qa-workflow-version")" == "$expected_version" ]] || fail "version was not recorded"
for agent in "${required_agents[@]}"; do
  assert_same "$repo_root/plugins/codex/install/agents/$agent.toml" "$agent_dir/$agent.toml"
  [[ "$install_output" == *"  $agent"* ]] || fail "install output did not list $agent"
done

same_output="$("$installer" --check --repo "$target_repo")"
[[ "$same_output" == *"up to date"* ]] || fail "check did not report up-to-date installation"

printf '%s\n' 'local customization' > "$agent_dir/implementer.toml"
printf '%s\n' '0.9.0' > "$agent_dir/.agentic-qa-workflow-version"
before_hash="$(sha256sum "$agent_dir/implementer.toml")"

set +e
refusal_output="$("$installer" --repo "$target_repo" 2>&1)"
refusal_status=$?
set -e
[[ $refusal_status -eq 3 ]] || fail "update without --force should exit 3"
[[ "$refusal_output" == *"--force"* ]] || fail "refusal did not explain explicit overwrite"
[[ "$(sha256sum "$agent_dir/implementer.toml")" == "$before_hash" ]] || fail "refused update changed an agent"

"$installer" --force --repo "$target_repo"
[[ "$(cat "$agent_dir/.agentic-qa-workflow-version")" == "$expected_version" ]] || fail "forced update did not record version"
assert_same "$repo_root/plugins/codex/install/agents/implementer.toml" "$agent_dir/implementer.toml"

echo "PASS: install-agents"
