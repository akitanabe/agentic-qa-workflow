"""CLI behavior tests for the plugin asset generator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUILDER_SOURCE = REPOSITORY_ROOT / "scripts" / "build_plugin_assets.py"
AGENT_NAMES = (
    "implementer",
    "senior-implementer",
    "responsibility-boundary-reviewer",
    "test-quality-reviewer",
    "writing-principles-reviewer",
    "security-side-effect-reviewer",
    "refactor-patch-agent",
)
REVIEWER_NAMES = (
    "responsibility-boundary-reviewer",
    "test-quality-reviewer",
    "writing-principles-reviewer",
    "security-side-effect-reviewer",
)
GENERATED_MARKDOWN_WARNING = "<!-- Generated from shared/. Do not edit directly. -->"
GENERATED_TOML_WARNING = "# Generated from shared/. Do not edit directly."


class BuildPluginAssetsCliTest(unittest.TestCase):
    """Verify the generator only through its documented command-line interface."""

    def test_repository_codex_skill_waits_for_each_worker_response(self) -> None:
        """Keep Codex workers alive and waiting until each delegated task responds."""
        source = (
            REPOSITORY_ROOT / "shared" / "skill" / "delegate-implementation.md"
        ).read_text(encoding="utf-8")
        codex_skill = (
            REPOSITORY_ROOT
            / "plugins"
            / "codex"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        claude_skill = (
            REPOSITORY_ROOT
            / "plugins"
            / "claude"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        required_instructions = (
            "対象 worker ごとに `wait_agent` を繰り返し使い、完了通知または返答が返るまで待機する。",
            "数分間の無応答を理由に worker を `shutdown` または `interrupt_agent` しない。",
        )

        for instruction in required_instructions:
            self.assertIn(instruction, source)
            self.assertIn(instruction, codex_skill)
            self.assertNotIn(instruction, claude_skill)

    def test_repository_codex_agents_use_role_appropriate_model_profiles(
        self,
    ) -> None:
        """Assign each Codex agent the model and effort suited to its role."""
        expected_profiles = {
            "implementer": ("gpt-5.6-luna", "xhigh"),
            "senior-implementer": ("gpt-5.6-terra", "high"),
            "responsibility-boundary-reviewer": ("gpt-5.6-terra", "xhigh"),
            "test-quality-reviewer": ("gpt-5.6-terra", "high"),
            "writing-principles-reviewer": ("gpt-5.6-luna", "xhigh"),
            "security-side-effect-reviewer": ("gpt-5.6-sol", "high"),
            "refactor-patch-agent": ("gpt-5.6-luna", "high"),
        }
        for name, (expected_model, expected_effort) in expected_profiles.items():
            with self.subTest(name=name):
                source = (
                    REPOSITORY_ROOT / "shared" / "agents" / f"{name}.md"
                ).read_text(encoding="utf-8")
                source_metadata = tomllib.loads(source.split("+++", 2)[1])
                artifact_metadata = tomllib.loads(
                    (
                        REPOSITORY_ROOT
                        / "plugins"
                        / "codex"
                        / "install"
                        / "agents"
                        / f"{name}.toml"
                    ).read_text(encoding="utf-8")
                )

                self.assertEqual(expected_model, source_metadata["codex"]["model"])
                self.assertEqual(expected_model, artifact_metadata["model"])
                self.assertEqual(
                    expected_effort,
                    source_metadata["codex"]["model_reasoning_effort"],
                )
                self.assertEqual(
                    expected_effort,
                    artifact_metadata["model_reasoning_effort"],
                )

    def test_repository_specialized_reviewers_define_their_review_contracts(self) -> None:
        """Expose each review focus, common verdicts, and a read-only Codex role."""
        expected_focus = {
            "test-quality-reviewer": ("観測可能な振る舞い", "境界値", "異常系"),
            "writing-principles-reviewer": ("How", "What", "Why", "Why Not"),
            "security-side-effect-reviewer": ("認証", "冪等", "path traversal"),
        }

        for name, focus_terms in expected_focus.items():
            with self.subTest(name=name):
                source = (
                    REPOSITORY_ROOT / "shared" / "agents" / f"{name}.md"
                ).read_text(encoding="utf-8")
                metadata = tomllib.loads(source.split("+++", 2)[1])

                self.assertEqual("read-only", metadata["codex"]["sandbox_mode"])
                for verdict in ("Pass", "Needs attention", "Blocker"):
                    self.assertIn(verdict, source)
                for term in focus_terms:
                    self.assertIn(term, source)

    def test_repository_workflows_route_specialists_and_require_final_writing_review(
        self,
    ) -> None:
        """Route specialists selectively and require a final writing review."""
        workflows = (
            REPOSITORY_ROOT / "shared" / "skill" / "delegate-implementation.md",
            REPOSITORY_ROOT
            / "plugins"
            / "claude"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md",
            REPOSITORY_ROOT
            / "plugins"
            / "codex"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md",
        )
        risk_routes = {
            "responsibility-boundary-reviewer": "責務混在、設計境界、分散した副作用",
            "test-quality-reviewer": "弱いテスト、欠けているケース、実装詳細に依存したテスト",
            "writing-principles-reviewer": (
                "コメント、命名、テスト名、コミットメッセージにおける "
                "`How / What / Why / Why Not` の配置不備"
            ),
            "security-side-effect-reviewer": (
                "外部 I/O、破壊的操作、機密データ、セキュリティ影響"
            ),
        }
        required_rules = (
            "ユーザーが専門 reviewer を明示的に要求した場合。",
            "親が reviewer の責務と一致する具体的なリスクを特定した場合。",
            "専門 reviewer を汎用コードレビューの代替にしない。",
            "専門 reviewer は mode 名だけを理由に一律起動しない。",
            (
                "`writing-principles-reviewer` の完了ゲートを除き、対象リスクがない"
                "専門 reviewer を無条件で起動しない。"
            ),
            "対象リスクと review 範囲を明示する。",
            (
                "`writing-principles-reviewer` は、実行しない明確な理由がない限り、"
                "最終的な受け入れ判断の直前に必ず起動する。"
            ),
            "受け入れ対象の最終 diff を review 範囲として渡す。",
            (
                "親は完了直前に限らず、記述原則のリスクを特定した時点でも"
                "適宜起動してよい。"
            ),
            (
                "指摘を受けて差分を変更した場合は、更新後の最終 diff を"
                "再度確認させる。"
            ),
            "具体的な理由と親が行った代替確認を最終報告に含める。",
            "reviewer は最終的な受け入れ判断を行わない。",
            "親が diff、テスト、検証結果を確認し、最終的な受け入れを判断する。",
        )

        for path in workflows:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                workflow = path.read_text(encoding="utf-8")
                normalized_workflow = "".join(workflow.split())

                for name, risk in risk_routes.items():
                    self.assertIn(f"| `{name}` | {risk} |", workflow)
                for rule in required_rules:
                    self.assertIn("".join(rule.split()), normalized_workflow)

    def test_repository_workflows_select_delegation_modes_without_crossing_direct_boundary(
        self,
    ) -> None:
        """Select delegation modes while keeping direct work outside the skill."""
        workflows = (
            REPOSITORY_ROOT / "shared" / "skill" / "delegate-implementation.md",
            REPOSITORY_ROOT
            / "plugins"
            / "claude"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md",
            REPOSITORY_ROOT
            / "plugins"
            / "codex"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md",
        )
        required_rules = (
            "`direct` は親が実装する、この skill の外にある経路である。",
            "タスク規模だけでこの skill を発火しない。",
            "`direct` が明示された場合も、この skill を発火しない。",
            "`lite` / `standard` / `strict` の明示は委譲要求を兼ねる。",
            "委譲だけが明示され mode が指定されていない場合は `standard` を選ぶ。",
            "`lite` を自動選択しない。",
            "`direct` と委譲が同時に指定された場合は、実装前にユーザーへ確認する。",
            "委譲 mode の強度は `lite < standard < strict` とする。",
            "mode を引き上げた場合は、その具体的なリスクをユーザーへ報告する。",
            "ユーザーが明示した mode を親都合で引き下げない。",
            "`direct` から委譲へ変更する場合は、ユーザーへ確認する。",
            "仕様が曖昧な場合は mode を選ぶ前に実装を止め、ユーザーへ確認する。",
            "`lite` の選択条件を満たさなくなった場合は `standard` 以上へ引き上げる。",
            "`standard` では扱えないリスクが判明した場合は `strict` へ引き上げる。",
        )
        route_contracts = (
            (
                "| `direct` |",
                "委譲要求がなく、仕様が明確で影響範囲が閉じ、親が直接処理する変更。",
            ),
            (
                "| `lite` |",
                "ユーザーが明示し、仕様が明確で影響範囲が局所的、容易に戻せる変更。",
            ),
            (
                "| `standard` |",
                "通常の実装委譲、または mode 未指定の明示的な委譲。",
            ),
            (
                "| `strict` |",
                "`strict` が明示された変更、または高リスク、影響範囲が広い、"
                "誤実装の代償が大きい変更。",
            ),
        )
        obsolete_classifications = (
            "枝の種別",
            "軽い修正・明確な仕様",
            "通常実装（既定）",
            "重要・高リスク実装",
        )

        for path in workflows:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                workflow = path.read_text(encoding="utf-8")
                normalized_workflow = "".join(workflow.split())

                for rule in required_rules:
                    self.assertIn("".join(rule.split()), normalized_workflow)
                for route, contract in route_contracts:
                    self.assertIn(route, workflow)
                    self.assertIn("".join(contract.split()), normalized_workflow)
                for classification in obsolete_classifications:
                    self.assertNotIn(classification, workflow)

    def test_repository_workflows_apply_mode_specific_qa_and_parent_verification(
        self,
    ) -> None:
        """Apply each delegation mode's QA strength and retain parent verification."""
        workflows = (
            REPOSITORY_ROOT / "shared" / "skill" / "delegate-implementation.md",
            REPOSITORY_ROOT
            / "plugins"
            / "claude"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md",
            REPOSITORY_ROOT
            / "plugins"
            / "codex"
            / "skills"
            / "delegate-implementation"
            / "SKILL.md",
        )
        mode_contracts = (
            (
                "| `lite` |",
                "親は返却の diff とテストを確認し、focused test で green を確認する。",
            ),
            (
                "| `standard` |",
                "AC→テスト対応表、境界値、異常系、Red 時点の失敗出力を要求する。",
            ),
            (
                "| `strict` |",
                "テスト計画→失敗テスト→実装の段階ゲートに分ける。",
            ),
        )
        required_rules = (
            "- 委譲 mode: <lite / standard / strict>",
            "`standard` と `strict` では、返却時に「AC-n → それを検証するテスト名 → "
            "期待値の根拠（仕様のどこから導いたか）」の対応表を必ず付けること。",
            "`lite` では、親が明示した場合だけ対応表と Red 時点の失敗出力を付けること。",
            "`standard` と `strict` では全観点を手を動かして確認する。",
            "`lite` では観点0（diff を読む）と観点5（自分で green を確認）に絞ってよい。",
            "全ての委譲 mode で、親による統合後の検証と最終的な受け入れ判断を省略しない。",
            "`direct` でも、親は必要なテストと検証を実行し、diff review と最終報告を行う。",
        )

        for path in workflows:
            with self.subTest(path=path.relative_to(REPOSITORY_ROOT)):
                workflow = path.read_text(encoding="utf-8")
                normalized_workflow = "".join(workflow.split())

                for mode, contract in mode_contracts:
                    self.assertIn(mode, workflow)
                    self.assertIn("".join(contract.split()), normalized_workflow)
                for rule in required_rules:
                    self.assertIn("".join(rule.split()), normalized_workflow)

    def test_repository_readmes_list_all_distributed_agents(self) -> None:
        """Make every bundled agent discoverable from both platform READMEs."""
        claude_readme = (REPOSITORY_ROOT / "plugins" / "claude" / "README.md").read_text(
            encoding="utf-8"
        )
        codex_readme = (REPOSITORY_ROOT / "plugins" / "codex" / "README.md").read_text(
            encoding="utf-8"
        )

        for name in AGENT_NAMES:
            with self.subTest(name=name):
                self.assertIn(f"agents/{name}.md", claude_readme)
                self.assertIn(f"`{name}`", codex_readme)

    def setUp(self) -> None:
        """Require the production CLI before constructing an isolated repository."""
        self.assertTrue(
            BUILDER_SOURCE.is_file(),
            f"generator is not implemented yet: {BUILDER_SOURCE}",
        )

    def _write(self, root: Path, relative_path: str, content: str) -> None:
        """Write one UTF-8 fixture file below the isolated repository root."""
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")

    def _agent_source(self, name: str, *, sandbox_mode: str | None = None) -> str:
        """Return a hand-written common agent source with platform metadata."""
        sandbox_line = (
            f'sandbox_mode = "{sandbox_mode}"\n' if sandbox_mode is not None else ""
        )
        return (
            "+++\n"
            f'name = "{name}"\n'
            "\n"
            "[claude]\n"
            f'description = "Claude {name}"\n'
            'model = "sonnet"\n'
            'effort = "medium"\n'
            "\n"
            "[codex]\n"
            f'description = "Codex {name}"\n'
            'model = "gpt-5.5"\n'
            'model_reasoning_effort = "medium"\n'
            f"{sandbox_line}"
            'nickname_candidates = ["Builder", "TDD Worker"]\n'
            "+++\n"
            "\n"
            "# {{parent_name}}\n"
            "\n"
            "Use **{{followup_tool}}** for the next turn.\n"
            "\n"
            "- Keep the Markdown body.\n"
            'Path C:\\workspace has "double quotes".\n'
            'Keep """three consecutive quotes""" intact.\n'
            "\n"
            "<!-- claude-only:start -->\n"
            "Claude agent only.\n"
            "<!-- claude-only:end -->\n"
            "<!-- codex-only:start -->\n"
            "Codex agent only.\n"
            "<!-- codex-only:end -->\n"
        )

    def _skill_source(self) -> str:
        """Return a common skill source covering frontmatter and body markers."""
        return (
            "<!-- claude-only:start -->\n"
            "---\n"
            "name: delegate-implementation\n"
            "description: Claude fixture skill\n"
            "---\n"
            "<!-- claude-only:end -->\n"
            "<!-- codex-only:start -->\n"
            "---\n"
            "name: delegate-implementation\n"
            "description: Codex fixture skill\n"
            "---\n"
            "<!-- codex-only:end -->\n"
            "\n"
            "# Delegation\n"
            "\n"
            "{{parent_name}} uses {{followup_tool}}.\n"
            "\n"
            "<!-- claude-only:start -->\n"
            "Claude-only instruction.\n"
            "<!-- claude-only:end -->\n"
            "<!-- codex-only:start -->\n"
            "Codex-only instruction.\n"
            "<!-- codex-only:end -->\n"
        )

    def _make_repository(self, root: Path) -> None:
        """Create a complete minimal repository fixture with stale generated files."""
        self._write(root, "shared/VERSION", "1.2.3\n")
        self._write(
            root,
            "shared/terms.toml",
            "[terms.parent_name]\n"
            'claude = "Parent Claude agent"\n'
            'codex = "Parent Codex agent"\n'
            "\n"
            "[terms.followup_tool]\n"
            'claude = "SendMessage"\n'
            'codex = "followup_task"\n',
        )
        self._write(
            root,
            "shared/skill/delegate-implementation.md",
            self._skill_source(),
        )
        for name in AGENT_NAMES:
            sandbox_mode = "read-only" if name in REVIEWER_NAMES else None
            self._write(
                root,
                f"shared/agents/{name}.md",
                self._agent_source(name, sandbox_mode=sandbox_mode),
            )

        manifests = (
            "plugins/claude/.claude-plugin/plugin.json",
            "plugins/codex/.codex-plugin/plugin.json",
        )
        for manifest in manifests:
            self._write(
                root,
                manifest,
                json.dumps(
                    {
                        "name": "agentic-qa-workflow",
                        "version": "0.9.0",
                        "description": f"fixture for {manifest}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )
        self._write(root, "plugins/codex/install/VERSION", "0.9.0\n")

        self._write(
            root,
            "plugins/claude/skills/delegate-implementation/SKILL.md",
            "stale claude skill\n",
        )
        self._write(
            root,
            "plugins/codex/skills/delegate-implementation/SKILL.md",
            "stale codex skill\n",
        )
        for name in AGENT_NAMES:
            self._write(root, f"plugins/claude/agents/{name}.md", "stale claude agent\n")
            self._write(
                root,
                f"plugins/codex/install/agents/{name}.toml",
                "stale codex agent\n",
            )

        self._write(root, "README.md", "outside README\n")
        self._write(root, "docs/plan.md", "outside docs\n")
        self._write(
            root,
            "plugins/codex/install/install-agents.sh",
            "#!/usr/bin/env bash\necho outside installer\n",
        )
        self._write(
            root,
            "plugins/codex/skills/delegate-implementation/agents/openai.yaml",
            "interface: outside\n",
        )
        self._write(
            root,
            "plugins/claude/agents/local-agent.md",
            "outside Claude agent\n",
        )
        self._write(
            root,
            "plugins/codex/install/agents/local-agent.toml",
            "outside Codex agent\n",
        )

        script = root / "scripts" / "build_plugin_assets.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BUILDER_SOURCE, script)

    def _run(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run the copied generator exactly as a user-facing Python CLI."""
        return subprocess.run(
            [sys.executable, str(root / "scripts" / "build_plugin_assets.py"), *arguments],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def _generated_paths(self, root: Path) -> list[Path]:
        """List every file whose content is owned by the generator."""
        paths = [
            root / "plugins/claude/skills/delegate-implementation/SKILL.md",
            root / "plugins/codex/skills/delegate-implementation/SKILL.md",
            root / "plugins/claude/.claude-plugin/plugin.json",
            root / "plugins/codex/.codex-plugin/plugin.json",
            root / "plugins/codex/install/VERSION",
        ]
        for name in AGENT_NAMES:
            paths.extend(
                (
                    root / f"plugins/claude/agents/{name}.md",
                    root / f"plugins/codex/install/agents/{name}.toml",
                )
            )
        return paths

    def _snapshot(self, paths: list[Path]) -> dict[Path, bytes | None]:
        """Capture bytes, including absence, for later non-mutation assertions."""
        return {path: path.read_bytes() if path.exists() else None for path in paths}

    def _assert_validation_error(
        self,
        root: Path,
        expected_paths: tuple[str, ...],
        before: dict[Path, bytes | None],
    ) -> str:
        """Assert the documented validation-error channel, code, and atomicity."""
        result = self._run(root)
        self.assertEqual(1, result.returncode, result)
        self.assertEqual("", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        for expected_path in expected_paths:
            self.assertIn(expected_path, result.stderr)
        self.assertEqual(before, self._snapshot(list(before)))
        return result.stderr

    def _frontmatter_warning_index(self, content: str) -> int:
        """Locate the first line after a generated Markdown frontmatter block."""
        lines = content.splitlines()
        self.assertEqual("---", lines[0])
        return lines.index("---", 1) + 1

    def test_build_generates_all_assets_and_syncs_versions(self) -> None:
        """Generate two skills, fourteen agents, and three synchronized versions."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)

            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            self.assertEqual("", result.stderr)
            self.assertTrue(result.stdout.strip())
            for path in self._generated_paths(root):
                self.assertTrue(path.is_file(), path)

            for manifest_path in (
                "plugins/claude/.claude-plugin/plugin.json",
                "plugins/codex/.codex-plugin/plugin.json",
            ):
                manifest = json.loads((root / manifest_path).read_text(encoding="utf-8"))
                self.assertEqual("1.2.3", manifest["version"])
                self.assertEqual(f"fixture for {manifest_path}", manifest["description"])
            self.assertEqual(
                "1.2.3\n",
                (root / "plugins/codex/install/VERSION").read_text(encoding="utf-8"),
            )

    def test_build_filters_markers_before_replacing_terms(self) -> None:
        """Select one platform branch, then replace terms without leaking markers."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            result = self._run(root)
            self.assertEqual(0, result.returncode, result)

            claude = (
                root / "plugins/claude/skills/delegate-implementation/SKILL.md"
            ).read_text(encoding="utf-8")
            codex = (
                root / "plugins/codex/skills/delegate-implementation/SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertTrue(claude.startswith("---\nname: delegate-implementation\n"))
            self.assertTrue(codex.startswith("---\nname: delegate-implementation\n"))
            self.assertIn("Parent Claude agent uses SendMessage.", claude)
            self.assertIn("Claude-only instruction.", claude)
            self.assertNotIn("Codex-only instruction.", claude)
            self.assertIn("Parent Codex agent uses followup_task.", codex)
            self.assertIn("Codex-only instruction.", codex)
            self.assertNotIn("Claude-only instruction.", codex)
            self.assertNotIn("<!-- claude-only", claude + codex)
            self.assertNotIn("<!-- codex-only", claude + codex)

    def test_build_accepts_whitespace_around_marker_lines(self) -> None:
        """Treat a marker as valid after stripping leading and trailing whitespace."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            source = root / "shared/skill/delegate-implementation.md"
            content = source.read_text(encoding="utf-8")
            content = content.replace("<!-- claude-only", "  <!-- claude-only")
            content = content.replace("<!-- codex-only", "\t<!-- codex-only")
            content = content.replace(" -->\n", " -->  \n")
            source.write_text(content, encoding="utf-8", newline="")

            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            self.assertEqual("", result.stderr)

    def test_build_rejects_invalid_markers_without_writing_outputs(self) -> None:
        """Reject malformed marker structure with line diagnostics and no writes."""
        invalid_sources = {
            "not independent": "prefix <!-- claude-only:start -->\n",
            "nested": (
                "<!-- claude-only:start -->\n"
                "<!-- codex-only:start -->\n"
                "text\n"
                "<!-- codex-only:end -->\n"
                "<!-- claude-only:end -->\n"
            ),
            "unknown platform": (
                "<!-- other-only:start -->\ntext\n<!-- other-only:end -->\n"
            ),
            "stray end": "<!-- claude-only:end -->\n",
            "mismatched end": (
                "<!-- claude-only:start -->\ntext\n<!-- codex-only:end -->\n"
            ),
            "unclosed": "<!-- claude-only:start -->\ntext\n",
            "unknown action": "<!-- claude-only:begin -->\n",
            "missing action": "<!-- claude-only -->\n",
        }
        for label, invalid in invalid_sources.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                source = root / "shared/skill/delegate-implementation.md"
                source.write_text(
                    source.read_text(encoding="utf-8").replace(
                        "# Delegation\n",
                        f"# Delegation\n{invalid}",
                        1,
                    ),
                    encoding="utf-8",
                    newline="",
                )
                before = self._snapshot(self._generated_paths(root))

                stderr = self._assert_validation_error(
                    root,
                    ("shared/skill/delegate-implementation.md",),
                    before,
                )

                self.assertRegex(
                    stderr,
                    r"shared/skill/delegate-implementation\.md:\d+",
                )
                self.assertIn("marker", stderr.lower())

    def test_build_preserves_unrelated_html_comments(self) -> None:
        """Keep ordinary HTML comments that are not platform marker syntax."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            source = root / "shared/skill/delegate-implementation.md"
            comment = "<!-- ordinary documentation note -->"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "# Delegation\n",
                    f"# Delegation\n{comment}\n",
                    1,
                ),
                encoding="utf-8",
                newline="",
            )

            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            for platform in ("claude", "codex"):
                generated = (
                    root / f"plugins/{platform}/skills/delegate-implementation/SKILL.md"
                ).read_text(encoding="utf-8")
                self.assertIn(comment, generated)

    def test_build_validates_each_rendered_skill_frontmatter_and_body(self) -> None:
        """Reject missing YAML frontmatter and empty bodies for both rendered skills."""
        def rendered_validation_source(platform: str, problem: str) -> str:
            """Build one source whose selected platform render has one boundary error."""
            claude_frontmatter = (
                "not Claude frontmatter\n"
                if platform == "claude" and problem == "frontmatter"
                else "---\nname: delegate-implementation\ndescription: Claude skill\n---\n"
            )
            codex_frontmatter = (
                "not Codex frontmatter\n"
                if platform == "codex" and problem == "frontmatter"
                else "---\nname: delegate-implementation\ndescription: Codex skill\n---\n"
            )
            if problem == "frontmatter":
                body = "\n{{parent_name}} uses {{followup_tool}}.\n"
            else:
                claude_body = (
                    ""
                    if platform == "claude"
                    else "{{parent_name}} uses {{followup_tool}}.\n"
                )
                codex_body = (
                    ""
                    if platform == "codex"
                    else "{{parent_name}} uses {{followup_tool}}.\n"
                )
                body = (
                    "\n<!-- claude-only:start -->\n"
                    f"{claude_body}"
                    "<!-- claude-only:end -->\n"
                    "<!-- codex-only:start -->\n"
                    f"{codex_body}"
                    "<!-- codex-only:end -->\n"
                )
            return (
                "<!-- claude-only:start -->\n"
                f"{claude_frontmatter}"
                "<!-- claude-only:end -->\n"
                "<!-- codex-only:start -->\n"
                f"{codex_frontmatter}"
                "<!-- codex-only:end -->\n"
                f"{body}"
            )

        for platform in ("claude", "codex"):
            for problem in ("frontmatter", "body"):
                with (
                    self.subTest(platform=platform, problem=problem),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = Path(directory)
                    self._make_repository(root)
                    source = root / "shared/skill/delegate-implementation.md"
                    source.write_text(
                        rendered_validation_source(platform, problem),
                        encoding="utf-8",
                        newline="",
                    )
                    before = self._snapshot(self._generated_paths(root))

                    stderr = self._assert_validation_error(
                        root,
                        ("shared/skill/delegate-implementation.md",),
                        before,
                    )

                    self.assertIn(platform, stderr.lower())

    def test_build_renders_agent_metadata_and_markdown_body(self) -> None:
        """Render ordered platform metadata while preserving the Markdown body."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            result = self._run(root)
            self.assertEqual(0, result.returncode, result)

            claude_path = root / "plugins/claude/agents/implementer.md"
            claude = claude_path.read_text(encoding="utf-8")
            claude_lines = claude.splitlines()
            expected_claude_prefix = [
                "---",
                'name: "implementer"',
                'description: "Claude implementer"',
                "model: sonnet",
                "effort: medium",
                "---",
                GENERATED_MARKDOWN_WARNING,
            ]
            self.assertEqual(expected_claude_prefix, claude_lines[:7])
            self.assertIn(
                "# Parent Claude agent\n\nUse **SendMessage** for the next turn.\n\n"
                "- Keep the Markdown body.\n"
                'Path C:\\workspace has "double quotes".\n'
                'Keep """three consecutive quotes""" intact.\n\n'
                "Claude agent only.\n",
                claude,
            )
            self.assertNotIn("Codex agent only.", claude)

            codex_path = root / "plugins/codex/install/agents/implementer.toml"
            codex = codex_path.read_text(encoding="utf-8")
            codex_lines = codex.splitlines()
            expected_key_order = [
                "name",
                "description",
                "model",
                "model_reasoning_effort",
                "nickname_candidates",
                "developer_instructions",
            ]
            actual_key_order = [
                line.split("=", 1)[0].strip()
                for line in codex_lines
                if "=" in line and not line.startswith("#")
            ]
            self.assertEqual(expected_key_order, actual_key_order)
            metadata = tomllib.loads(codex)
            self.assertEqual("implementer", metadata["name"])
            self.assertEqual("Codex implementer", metadata["description"])
            self.assertEqual(["Builder", "TDD Worker"], metadata["nickname_candidates"])
            self.assertEqual(
                "# Parent Codex agent\n\n"
                "Use **followup_task** for the next turn.\n\n"
                "- Keep the Markdown body.\n"
                'Path C:\\workspace has "double quotes".\n'
                'Keep """three consecutive quotes""" intact.\n\n'
                "Codex agent only.\n",
                metadata["developer_instructions"],
            )

    def test_codex_agent_body_round_trips_toml_special_characters(self) -> None:
        """Preserve quotes, backslashes, and triple quotes through Codex TOML."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            result = self._run(root)
            self.assertEqual(0, result.returncode, result)

            metadata = tomllib.loads(
                (root / "plugins/codex/install/agents/implementer.toml").read_text(
                    encoding="utf-8"
                )
            )
            expected_body = (
                "# Parent Codex agent\n\n"
                "Use **followup_task** for the next turn.\n\n"
                "- Keep the Markdown body.\n"
                'Path C:\\workspace has "double quotes".\n'
                'Keep """three consecutive quotes""" intact.\n\n'
                "Codex agent only.\n"
            )
            self.assertEqual(expected_body, metadata["developer_instructions"])

    def test_build_handles_optional_codex_sandbox_mode(self) -> None:
        """Emit sandbox_mode for reviewers and omit it for an implementation agent."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            result = self._run(root)
            self.assertEqual(0, result.returncode, result)

            implementer = tomllib.loads(
                (root / "plugins/codex/install/agents/implementer.toml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("sandbox_mode", implementer)

            for name in REVIEWER_NAMES:
                with self.subTest(name=name):
                    reviewer_text = (
                        root / f"plugins/codex/install/agents/{name}.toml"
                    ).read_text(encoding="utf-8")
                    reviewer = tomllib.loads(reviewer_text)

                    self.assertEqual("read-only", reviewer["sandbox_mode"])
                    self.assertLess(
                        reviewer_text.index("model_reasoning_effort ="),
                        reviewer_text.index("sandbox_mode ="),
                    )
                    self.assertLess(
                        reviewer_text.index("sandbox_mode ="),
                        reviewer_text.index("nickname_candidates ="),
                    )

    def test_build_rejects_invalid_agent_frontmatter_without_writing(self) -> None:
        """Reject schema, type, name, delimiter, and placeholder violations atomically."""
        mutations = {
            "unknown top-level key": lambda text: text.replace(
                'name = "implementer"\n',
                'name = "implementer"\nunknown = "value"\n',
                1,
            ),
            "unknown Claude key": lambda text: text.replace(
                'effort = "medium"\n',
                'effort = "medium"\ntemperature = 1\n',
                1,
            ),
            "unknown Codex key": lambda text: text.replace(
                'nickname_candidates = ["Builder", "TDD Worker"]\n',
                'nickname_candidates = ["Builder", "TDD Worker"]\nunknown = true\n',
                1,
            ),
            "missing Claude description": lambda text: text.replace(
                'description = "Claude implementer"\n', "", 1
            ),
            "missing Claude model": lambda text: text.replace(
                'model = "sonnet"\n', "", 1
            ),
            "missing Claude effort": lambda text: text.replace(
                'effort = "medium"\n', "", 1
            ),
            "missing Codex description": lambda text: text.replace(
                'description = "Codex implementer"\n', "", 1
            ),
            "missing Codex model": lambda text: text.replace(
                'model = "gpt-5.5"\n', "", 1
            ),
            "missing Codex reasoning effort": lambda text: text.replace(
                'model_reasoning_effort = "medium"\n', "", 1
            ),
            "missing Codex nickname candidates": lambda text: text.replace(
                'nickname_candidates = ["Builder", "TDD Worker"]\n', "", 1
            ),
            "missing common name": lambda text: text.replace(
                'name = "implementer"\n', "", 1
            ),
            "missing Claude table": lambda text: text.replace("[claude]\n", "", 1),
            "missing Codex table": lambda text: text.replace("[codex]\n", "", 1),
            "duplicate key": lambda text: text.replace(
                'description = "Claude implementer"\n',
                'description = "Claude implementer"\n'
                'description = "duplicate"\n',
                1,
            ),
            "wrong scalar type": lambda text: text.replace(
                'name = "implementer"\n', "name = 1\n", 1
            ),
            "wrong list type": lambda text: text.replace(
                'nickname_candidates = ["Builder", "TDD Worker"]\n',
                'nickname_candidates = "Builder"\n',
                1,
            ),
            "wrong list element type": lambda text: text.replace(
                'nickname_candidates = ["Builder", "TDD Worker"]\n',
                'nickname_candidates = ["Builder", 1]\n',
                1,
            ),
            "wrong sandbox type": lambda text: text.replace(
                'model_reasoning_effort = "medium"\n',
                'model_reasoning_effort = "medium"\nsandbox_mode = true\n',
                1,
            ),
            "name does not match filename": lambda text: text.replace(
                'name = "implementer"\n', 'name = "other-agent"\n', 1
            ),
            "placeholder in frontmatter": lambda text: text.replace(
                'description = "Claude implementer"\n',
                'description = "{{parent_name}}"\n',
                1,
            ),
            "unclosed frontmatter": lambda text: text.replace("+++\n\n#", "\n#", 1),
            "missing opening frontmatter": lambda text: text.removeprefix("+++\n"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                source = root / "shared/agents/implementer.md"
                source.write_text(
                    mutate(source.read_text(encoding="utf-8")),
                    encoding="utf-8",
                    newline="",
                )
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(
                    root,
                    ("shared/agents/implementer.md",),
                    before,
                )

    def test_build_rejects_empty_agent_markdown_bodies_without_writing(self) -> None:
        """Reject absent and whitespace-only common agent bodies atomically."""
        for label, body in (("absent", ""), ("whitespace", " \n\t\n")):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                source = root / "shared/agents/implementer.md"
                frontmatter = source.read_text(encoding="utf-8").rsplit("+++\n", 1)[0]
                source.write_text(
                    f"{frontmatter}+++\n{body}",
                    encoding="utf-8",
                    newline="",
                )
                before = self._snapshot(self._generated_paths(root))

                self._assert_validation_error(
                    root,
                    ("shared/agents/implementer.md",),
                    before,
                )

    def test_build_validates_terms_and_placeholders(self) -> None:
        """Reject invalid term definitions, names, usage, and unresolved placeholders."""
        def undefined_placeholder(root: Path) -> None:
            """Replace one known skill placeholder with an undefined name."""
            source = root / "shared/skill/delegate-implementation.md"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "{{parent_name}} uses", "{{missing_term}} uses", 1
                ),
                encoding="utf-8",
                newline="",
            )

        def mutate_terms(root: Path, old: str, new: str) -> None:
            """Apply one deliberate mutation to the isolated term table."""
            terms = root / "shared/terms.toml"
            terms.write_text(
                terms.read_text(encoding="utf-8").replace(old, new, 1),
                encoding="utf-8",
                newline="",
            )

        mutations = {
            "undefined placeholder": undefined_placeholder,
            "missing platform value": lambda root: mutate_terms(
                root, 'codex = "Parent Codex agent"\n', ""
            ),
            "empty value": lambda root: mutate_terms(
                root, 'claude = "Parent Claude agent"', 'claude = ""'
            ),
            "multiline value": lambda root: mutate_terms(
                root,
                'claude = "Parent Claude agent"',
                'claude = """Parent\nClaude agent"""',
            ),
            "unused term": lambda root: mutate_terms(
                root,
                "[terms.parent_name]",
                "[terms.unused_name]\n"
                'claude = "unused"\n'
                'codex = "unused"\n\n'
                "[terms.parent_name]",
            ),
            "invalid term name": lambda root: mutate_terms(
                root, "[terms.parent_name]", "[terms.Parent_Name]"
            ),
            "leading digit term name": lambda root: mutate_terms(
                root, "[terms.parent_name]", "[terms.1parent_name]"
            ),
            "double underscore term name": lambda root: mutate_terms(
                root, "[terms.parent_name]", "[terms.parent__name]"
            ),
            "trailing underscore term name": lambda root: mutate_terms(
                root, "[terms.parent_name]", "[terms.parent_name_]"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                mutate(root)
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(root, ("shared/",), before)

    def test_build_does_not_recursively_expand_term_values(self) -> None:
        """Leave placeholder-shaped text introduced by a term value untouched."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            terms = root / "shared/terms.toml"
            terms.write_text(
                terms.read_text(encoding="utf-8")
                .replace(
                    'claude = "Parent Claude agent"',
                    'claude = "Parent {{literal_name}} agent"',
                    1,
                )
                .replace(
                    'codex = "Parent Codex agent"',
                    'codex = "Parent {{literal_name}} agent"',
                    1,
                ),
                encoding="utf-8",
                newline="",
            )

            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            self.assertIn(
                "Parent {{literal_name}} agent uses SendMessage.",
                (root / "plugins/claude/skills/delegate-implementation/SKILL.md").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertIn(
                "Parent {{literal_name}} agent uses followup_task.",
                (root / "plugins/codex/skills/delegate-implementation/SKILL.md").read_text(
                    encoding="utf-8"
                ),
            )

    def test_build_requires_fixed_sources_and_rejects_unknown_agent_markdown(self) -> None:
        """Require every canonical input and reject unknown shared agent Markdown."""
        required_sources = (
            "shared/VERSION",
            "shared/terms.toml",
            "shared/skill/delegate-implementation.md",
            *(f"shared/agents/{name}.md" for name in AGENT_NAMES),
        )
        for missing in required_sources:
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                (root / missing).unlink()
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(root, (missing,), before)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            self._write(root, "shared/agents/unknown-agent.md", self._agent_source("unknown-agent"))
            before = self._snapshot(self._generated_paths(root))
            self._assert_validation_error(
                root,
                ("shared/agents/unknown-agent.md",),
                before,
            )

    def test_build_rejects_invalid_bundle_versions(self) -> None:
        """Accept only three-part decimal versions without leading zeroes."""
        invalid_versions = (
            "",
            "01.2.3",
            "1.02.3",
            "1.2.03",
            "1.2",
            "v1.2.3",
            "1.2.3.4",
            "1.2.3\nextra",
        )
        for version in invalid_versions:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                (root / "shared/VERSION").write_text(
                    f"{version}\n", encoding="utf-8", newline=""
                )
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(root, ("shared/VERSION",), before)

    def test_build_accepts_zero_and_multi_digit_version_components(self) -> None:
        """Accept zero and nonzero multi-digit components allowed by the version regex."""
        for version in ("0.0.0", "10.20.30"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                (root / "shared/VERSION").write_text(
                    f"{version}\n", encoding="utf-8", newline=""
                )

                result = self._run(root)

                self.assertEqual(0, result.returncode, result)
                self.assertEqual(
                    f"{version}\n",
                    (root / "plugins/codex/install/VERSION").read_text(encoding="utf-8"),
                )

    def test_build_validates_version_target_manifests_atomically(self) -> None:
        """Reject malformed or incomplete manifests and aggregate independent errors."""
        def apply_manifest_problem(path: Path, problem: str) -> None:
            """Apply one invalid manifest shape without touching other fixture inputs."""
            if problem == "missing file":
                path.unlink()
            elif problem == "invalid JSON":
                path.write_text("{ invalid\n", encoding="utf-8", newline="")
            elif problem == "top-level non-object":
                path.write_text("[]\n", encoding="utf-8", newline="")
            elif problem == "missing version":
                path.write_text(
                    '{"name": "agentic-qa-workflow"}\n',
                    encoding="utf-8",
                    newline="",
                )
            elif problem == "non-string version":
                path.write_text(
                    '{"name": "agentic-qa-workflow", "version": 1}\n',
                    encoding="utf-8",
                    newline="",
                )
            else:
                self.fail(f"unknown manifest fixture problem: {problem}")

        manifests = (
            "plugins/claude/.claude-plugin/plugin.json",
            "plugins/codex/.codex-plugin/plugin.json",
        )
        problems = (
            "missing file",
            "invalid JSON",
            "top-level non-object",
            "missing version",
            "non-string version",
        )
        for manifest in manifests:
            for problem in problems:
                with (
                    self.subTest(manifest=manifest, problem=problem),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    root = Path(directory)
                    self._make_repository(root)
                    apply_manifest_problem(root / manifest, problem)
                    before = self._snapshot(self._generated_paths(root))
                    self._assert_validation_error(root, (manifest,), before)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            apply_manifest_problem(root / manifests[0], "invalid JSON")
            apply_manifest_problem(root / manifests[1], "top-level non-object")
            before = self._snapshot(self._generated_paths(root))

            self._assert_validation_error(root, manifests, before)

    def test_build_places_generated_warnings_only_on_markdown_and_agent_toml(self) -> None:
        """Place exact warnings at generated frontmatter boundaries and nowhere else."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            result = self._run(root)
            self.assertEqual(0, result.returncode, result)

            markdown_paths = [
                root / "plugins/claude/skills/delegate-implementation/SKILL.md",
                root / "plugins/codex/skills/delegate-implementation/SKILL.md",
                *(root / f"plugins/claude/agents/{name}.md" for name in AGENT_NAMES),
            ]
            for path in markdown_paths:
                content = path.read_text(encoding="utf-8")
                lines = content.splitlines()
                self.assertEqual(
                    GENERATED_MARKDOWN_WARNING,
                    lines[self._frontmatter_warning_index(content)],
                    path,
                )
                self.assertEqual(1, content.count(GENERATED_MARKDOWN_WARNING), path)

            for name in AGENT_NAMES:
                content = (
                    root / f"plugins/codex/install/agents/{name}.toml"
                ).read_text(encoding="utf-8")
                self.assertEqual(GENERATED_TOML_WARNING, content.splitlines()[0])
                self.assertEqual(1, content.count(GENERATED_TOML_WARNING))

            for path in (
                root / "plugins/claude/.claude-plugin/plugin.json",
                root / "plugins/codex/.codex-plugin/plugin.json",
                root / "plugins/codex/install/VERSION",
            ):
                self.assertNotIn("Generated from shared/", path.read_text(encoding="utf-8"))

    def test_check_succeeds_without_modifying_matching_outputs(self) -> None:
        """Return zero from --check and leave matching generated files untouched."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            build = self._run(root)
            self.assertEqual(0, build.returncode, build)
            paths = self._generated_paths(root)
            known_mtime = 1_700_000_000_000_000_000
            for path in paths:
                os.utime(path, ns=(known_mtime, known_mtime))
            before = self._snapshot(paths)

            result = self._run(root, "--check")

            self.assertEqual(0, result.returncode, result)
            self.assertEqual("", result.stderr)
            self.assertTrue(result.stdout.strip())
            self.assertEqual(before, self._snapshot(paths))
            self.assertTrue(all(path.stat().st_mtime_ns == known_mtime for path in paths))

    def test_check_reports_all_stale_and_missing_outputs_without_writing(self) -> None:
        """List every mismatch on stderr with exit one and never repair it in --check."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            build = self._run(root)
            self.assertEqual(0, build.returncode, build)

            stale_skill = root / "plugins/claude/skills/delegate-implementation/SKILL.md"
            missing_agent = root / "plugins/codex/install/agents/implementer.toml"
            stale_manifest = root / "plugins/codex/.codex-plugin/plugin.json"
            stale_skill.write_text("stale\n", encoding="utf-8", newline="")
            missing_agent.unlink()
            manifest = json.loads(stale_manifest.read_text(encoding="utf-8"))
            manifest["version"] = "9.9.9"
            stale_manifest.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline=""
            )
            paths = self._generated_paths(root)
            before = self._snapshot(paths)

            result = self._run(root, "--check")

            self.assertEqual(1, result.returncode, result)
            self.assertEqual("", result.stdout)
            for relative_path in (
                "plugins/claude/skills/delegate-implementation/SKILL.md",
                "plugins/codex/install/agents/implementer.toml",
                "plugins/codex/.codex-plugin/plugin.json",
            ):
                self.assertIn(relative_path, result.stderr)
            self.assertEqual(before, self._snapshot(paths))

    def test_check_reports_input_errors_without_writing(self) -> None:
        """Return validation exit one on --check and preserve every stale output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            (root / "shared/VERSION").write_text(
                "01.0.0\n", encoding="utf-8", newline=""
            )
            paths = self._generated_paths(root)
            before = self._snapshot(paths)

            result = self._run(root, "--check")

            self.assertEqual(1, result.returncode, result)
            self.assertEqual("", result.stdout)
            self.assertIn("shared/VERSION", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(before, self._snapshot(paths))

    def test_cli_rejects_unknown_and_positional_arguments(self) -> None:
        """Return argparse-style usage errors without changing generated files."""
        for arguments in (("--unknown",), ("positional",), ("--check", "extra")):
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._make_repository(root)
                paths = self._generated_paths(root)
                before = self._snapshot(paths)

                result = self._run(root, *arguments)

                self.assertEqual(2, result.returncode, result)
                self.assertEqual("", result.stdout)
                self.assertIn("usage:", result.stderr.lower())
                self.assertEqual(before, self._snapshot(paths))

    def test_independent_input_errors_are_aggregated_without_partial_updates(self) -> None:
        """Report independent source errors together before changing any output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            skill = root / "shared/skill/delegate-implementation.md"
            skill.write_text(
                "<!-- claude-only:start -->\nunclosed\n",
                encoding="utf-8",
                newline="",
            )
            agent = root / "shared/agents/implementer.md"
            agent.write_text(
                agent.read_text(encoding="utf-8").replace(
                    'description = "Claude implementer"\n', "", 1
                ),
                encoding="utf-8",
                newline="",
            )
            before = self._snapshot(self._generated_paths(root))

            self._assert_validation_error(
                root,
                (
                    "shared/skill/delegate-implementation.md",
                    "shared/agents/implementer.md",
                ),
                before,
            )

    def test_build_updates_only_files_with_changed_content(self) -> None:
        """Avoid rewriting equal files and repair only one deliberately stale output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            first = self._run(root)
            self.assertEqual(0, first.returncode, first)
            paths = self._generated_paths(root)
            expected = self._snapshot(paths)
            known_mtime = 1_700_000_000_000_000_000
            stale_mtime = 1_600_000_000_000_000_000
            for path in paths:
                os.utime(path, ns=(known_mtime, known_mtime))

            unchanged = self._run(root)
            self.assertEqual(0, unchanged.returncode, unchanged)
            self.assertTrue(all(path.stat().st_mtime_ns == known_mtime for path in paths))

            stale_path = root / "plugins/codex/install/agents/implementer.toml"
            stale_path.write_text("stale\n", encoding="utf-8", newline="")
            os.utime(stale_path, ns=(stale_mtime, stale_mtime))
            repaired = self._run(root)

            self.assertEqual(0, repaired.returncode, repaired)
            self.assertEqual(expected, self._snapshot(paths))
            self.assertNotEqual(stale_mtime, stale_path.stat().st_mtime_ns)
            for path in paths:
                if path != stale_path:
                    self.assertEqual(known_mtime, path.stat().st_mtime_ns, path)

    def test_build_is_deterministic_utf8_lf_with_trailing_newlines(self) -> None:
        """Produce identical UTF-8 bytes with LF endings from identical inputs."""
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            roots = (Path(first_dir), Path(second_dir))
            snapshots = []
            for root in roots:
                self._make_repository(root)
                result = self._run(root)
                self.assertEqual(0, result.returncode, result)
                paths = self._generated_paths(root)
                relative_bytes = {}
                for path in paths:
                    content = path.read_bytes()
                    content.decode("utf-8")
                    self.assertNotIn(b"\r\n", content, path)
                    self.assertTrue(content.endswith(b"\n"), path)
                    relative_bytes[path.relative_to(root)] = content
                snapshots.append(relative_bytes)

            self.assertEqual(snapshots[0], snapshots[1])

    def test_build_and_check_preserve_out_of_scope_files(self) -> None:
        """Leave interface metadata, docs, installer, and unrelated agents unchanged."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root)
            outside_paths = [
                root / "README.md",
                root / "docs/plan.md",
                root / "plugins/codex/install/install-agents.sh",
                root / "plugins/codex/skills/delegate-implementation/agents/openai.yaml",
                root / "plugins/claude/agents/local-agent.md",
                root / "plugins/codex/install/agents/local-agent.toml",
            ]
            before = self._snapshot(outside_paths)

            build = self._run(root)
            check = self._run(root, "--check")

            self.assertEqual(0, build.returncode, build)
            self.assertEqual(0, check.returncode, check)
            self.assertEqual(before, self._snapshot(outside_paths))


if __name__ == "__main__":
    unittest.main()
