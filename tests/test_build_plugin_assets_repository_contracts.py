"""Real-repository contract tests for generated plugin assets."""

from __future__ import annotations

from pathlib import Path
import unittest

from build_plugin_assets_test_support import (
    AGENT_NAMES,
    CLAUDE_MODEL_PROFILES,
    CLAUDE_PROFILE_PATH,
    CODEX_MODEL_PROFILES,
    GENERATED_SKILL_PATHS,
    REPOSITORY_ROOT,
    RepositoryContractSupport,
    SHARED_SKILL_PATH,
)


class BuildPluginAssetsRepositoryContractsTest(
    RepositoryContractSupport,
    unittest.TestCase,
):
    def test_repository_codex_skill_waits_for_each_worker_response(self) -> None:
        """Keep Codex workers alive and waiting until each delegated task responds."""
        skills = self._repository_skill_texts()
        required_instructions = (
            "対象 worker ごとに `wait_agent` を繰り返し使い、完了通知または返答が返るまで待機する。",
            "数分間の無応答を理由に worker を `shutdown` または `interrupt_agent` しない。",
        )

        for instruction in required_instructions:
            self.assertIn(instruction, skills.source)
            self.assertIn(instruction, skills.codex)
            self.assertNotIn(instruction, skills.claude)

    def test_repository_skills_start_a_fresh_implementer_context_per_branch(
        self,
    ) -> None:
        """Align each implementation branch with one fresh Implementer context."""
        skills = self._repository_skill_texts()
        shared_contract = (
            "1実装枝 = 1つの新規 Implementer context",
            "別の実装枝に同じ Implementer を再利用しない。",
            "同一実装枝を完成させるための段階ゲートと差し戻し",
        )

        for instruction in shared_contract:
            for skill in skills.all_texts():
                self.assertIn(instruction, skill)

        codex_context_boundary = (
            '新規 Implementer の生成時は必ず `fork_turns: "none"` を指定する。'
        )
        self.assertIn(codex_context_boundary, skills.source)
        self.assertIn(codex_context_boundary, skills.codex)
        self.assertNotIn(codex_context_boundary, skills.claude)

    def test_repository_skills_require_self_contained_implementation_branch_data(
        self,
    ) -> None:
        """Give a fresh Implementer all data needed to finish one branch."""
        skills = self._repository_skill_texts()
        required_data = (
            "実装枝の目的",
            "Acceptance Criteria",
            "対象範囲と変更禁止範囲",
            "最新の基準コミット",
            "worktree path と branch 名",
            "コードから読み取れない確定済みの設計判断や制約",
            "委譲 mode と TDD 要件",
            "検証 command",
            "完了条件",
            "commit と返却報告の形式",
        )

        for item in required_data:
            for skill in skills.all_texts():
                self.assertIn(item, skill)

    def test_repository_codex_agents_use_role_appropriate_model_profiles(
        self,
    ) -> None:
        """Assign each Codex agent the model and effort suited to its role."""
        for name, expected in CODEX_MODEL_PROFILES.items():
            with self.subTest(name=name):
                source_metadata = self._agent_source_metadata(name)
                artifact_metadata = self._codex_agent_artifact_metadata(name)

                self.assertEqual(expected.model, source_metadata["codex"]["model"])
                self.assertEqual(expected.model, artifact_metadata["model"])
                self.assertEqual(
                    expected.reasoning_effort,
                    source_metadata["codex"]["model_reasoning_effort"],
                )
                self.assertEqual(
                    expected.reasoning_effort,
                    artifact_metadata["model_reasoning_effort"],
                )

    def test_repository_claude_agents_use_role_appropriate_model_profiles(
        self,
    ) -> None:
        """Assign each Claude agent the model and effort suited to its role."""
        for name, expected in CLAUDE_MODEL_PROFILES.items():
            with self.subTest(name=name):
                source_metadata = self._agent_source_metadata(name)
                artifact = self._repository_text(CLAUDE_PROFILE_PATH / f"{name}.md")

                self.assertEqual(expected.model, source_metadata["claude"]["model"])
                self.assertEqual(
                    expected.reasoning_effort, source_metadata["claude"]["effort"]
                )
                self.assertIn(f"model: {expected.model}\n", artifact)
                self.assertIn(f"effort: {expected.reasoning_effort}\n", artifact)

    def test_repository_workflows_gate_expert_implementation_with_selection_review(
        self,
    ) -> None:
        """Use expert only after an independent review approves its concrete rationale."""
        workflows = self._repository_workflow_texts()
        required_contract = (
            "`expert-selection-reviewer`",
            "`APPROVE_EXPERT`",
            "`REJECT_USE_SENIOR`",
            "`REJECT_USE_IMPLEMENTER`",
            "`REJECT_REPLAN`",
            "親相当の能力が必要な判断",
            "senior では不足すると判断した具体的根拠",
            "独立 context へ隔離する理由",
            "自動 fallback しない",
            "プランを練り直す",
        )

        for path, workflow in workflows.items():
            with self.subTest(path=path):
                normalized_workflow = "".join(workflow.split())
                for instruction in required_contract:
                    self.assertIn("".join(instruction.split()), normalized_workflow)

        codex_only_rule = (
            "登録または agent 名の指定ができない場合は role profile へ代替せず"
        )
        self.assertIn(codex_only_rule, workflows[SHARED_SKILL_PATH])
        self.assertIn(codex_only_rule, workflows[GENERATED_SKILL_PATHS["codex"]])
        self.assertNotIn(codex_only_rule, workflows[GENERATED_SKILL_PATHS["claude"]])

    def test_repository_expert_agents_define_selection_and_side_effect_contracts(
        self,
    ) -> None:
        """Keep expert selection costly, explicit, and bounded by observable contracts."""
        expert = self._repository_text(Path("shared/agents/expert-implementer.md"))
        reviewer = self._repository_text(
            Path("shared/agents/expert-selection-reviewer.md")
        )
        reviewer_metadata = self._agent_source_metadata("expert-selection-reviewer")

        for instruction in (
            "Action → Data → Calculation → Data → Action",
            "避けられない副作用",
            "副作用を配置した境界",
            "実行順序とトランザクション境界",
            "重複実行、再試行、部分失敗時の振る舞い",
            "これ以上副作用を狭められない理由",
        ):
            self.assertIn(instruction, expert)

        for verdict in (
            "APPROVE_EXPERT",
            "REJECT_USE_SENIOR",
            "REJECT_USE_IMPLEMENTER",
            "REJECT_REPLAN",
        ):
            self.assertIn(verdict, reviewer)
        self.assertEqual("read-only", reviewer_metadata["codex"]["sandbox_mode"])
        self.assertIn("ファイル編集", reviewer)
        self.assertIn("最終判断", reviewer)

    def test_repository_specialized_reviewers_define_their_review_contracts(self) -> None:
        """Expose each review focus, common verdicts, and a read-only Codex role."""
        expected_focus = {
            "test-quality-reviewer": ("観測可能な振る舞い", "境界値", "異常系"),
            "security-side-effect-reviewer": ("認証", "冪等", "path traversal"),
        }

        for name, focus_terms in expected_focus.items():
            with self.subTest(name=name):
                source = self._repository_text(Path("shared/agents") / f"{name}.md")
                metadata = self._agent_source_metadata(name)

                self.assertEqual("read-only", metadata["codex"]["sandbox_mode"])
                for verdict in ("Pass", "Needs attention", "Blocker"):
                    self.assertIn(verdict, source)
                for term in focus_terms:
                    self.assertIn(term, source)

    def test_repository_refactorers_define_writable_narrow_contracts(self) -> None:
        """Allow only the two refactorers to apply their explicitly bounded patches."""
        expected_contracts = {
            "writing-principles-refactorer": (
                "How / What / Why / Why Not",
                "自明または重複したコメントの削除",
                "テストの期待値変更",
                "既存コミットの rewrite は行いません",
            ),
            "review-patch-refactorer": (
                "専門 reviewer の具体的な指摘",
                "Acceptance Criteria",
                "指摘されていない箇所のついで修正",
                "追加した修正コミット SHA",
            ),
        }

        for name, contracts in expected_contracts.items():
            with self.subTest(name=name):
                source = self._repository_text(Path("shared/agents") / f"{name}.md")
                metadata = self._agent_source_metadata(name)
                artifact = self._codex_agent_artifact_metadata(name)

                self.assertNotIn("sandbox_mode", metadata["codex"])
                self.assertNotIn("sandbox_mode", artifact)
                for contract in contracts:
                    self.assertIn(contract, source)

    def test_security_reviewer_is_defensive_and_detection_only(self) -> None:
        """Keep security review defensive, actionable, and inside its assigned scope."""
        paths = (
            REPOSITORY_ROOT / "shared/agents/security-side-effect-reviewer.md",
            REPOSITORY_ROOT / "plugins/claude/agents/security-side-effect-reviewer.md",
            REPOSITORY_ROOT
            / "plugins/codex/install/agents/security-side-effect-reviewer.toml",
        )
        required_contracts = (
            "攻撃コードや悪用手順の作成は一切行いません",
            "あなたは検出役です",
            "コードの修正は専門 agent が担当します",
            "指摘は修正担当がそのまま着手できる粒度・形式で出力してください",
            "レビュー範囲外の改善提案（命名、責務分離など）は行いません",
        )

        for path in paths:
            content = path.read_text(encoding="utf-8")
            for contract in required_contracts:
                self.assertIn(contract, content, path)

    def test_repository_workflows_route_specialists_and_run_final_writing_refactor(
        self,
    ) -> None:
        """Route reviewers and refactorers without blurring their responsibilities."""
        workflows = self._repository_workflow_texts()
        risk_routes = {
            "responsibility-boundary-reviewer": "責務混在、設計境界、分散した副作用",
            "test-quality-reviewer": "弱いテスト、欠けているケース、実装詳細に依存したテスト",
            "security-side-effect-reviewer": (
                "外部 I/O、破壊的操作、機密データ、セキュリティ影響"
            ),
        }
        required_rules = (
            "ユーザーが専門 reviewer を明示的に要求した場合。",
            "親が reviewer の責務と一致する具体的なリスクを特定した場合。",
            "専門 reviewer を汎用コードレビューの代替にしない。",
            "専門 reviewer は mode 名だけを理由に一律起動しない。",
            "対象リスクがない専門 reviewer を無条件で起動しない。",
            "対象リスクと review 範囲を明示する。",
            (
                "`writing-principles-refactorer` は `lite` / `standard` / `strict` の"
                "すべてで、実行しない明確な理由がない限り、最終成果物の統合前または"
                "完了直前に起動する。"
            ),
            (
                "差分に対象となるコード、テスト、コメント、DocBlock が存在しない場合は"
                "省略できる。"
            ),
            (
                "`review-patch-refactorer` による指摘修正後に"
                "`writing-principles-refactorer` が最終成果物を確認・修正する。"
            ),
            "両 refactorer の担当範囲は排他的ではない。",
            "refactorer がファイルを変更した後は、対象 test を再実行する。",
            "親が変更後の diff と検証結果を確認してから受け入れる。",
            "reviewer は最終的な受け入れ判断を行わない。",
            "親が diff、テスト、検証結果を確認し、最終的な受け入れを判断する。",
        )

        for path, workflow in workflows.items():
            with self.subTest(path=path):
                normalized_workflow = "".join(workflow.split())

                for name, risk in risk_routes.items():
                    self.assertIn(f"| `{name}` | {risk} |", workflow)
                for rule in required_rules:
                    self.assertIn("".join(rule.split()), normalized_workflow)

    def test_repository_workflow_defines_review_patch_routing_boundary(self) -> None:
        """Patch only green implementations with concrete, behavior-preserving findings."""
        workflows = self._repository_workflow_texts()
        startup_conditions = (
            "専門 reviewer の具体的な指摘が存在する。",
            "Acceptance Criteria は満たされている。",
            "機能的なテストは green である。",
            "修正範囲が局所的である。",
            "仕様の再解釈を必要としない。",
            "新機能追加ではない。",
            "振る舞いを維持したまま修正できる。",
            "reviewer が修正方針または問題箇所を明示している。",
        )
        implementer_routes = (
            "Acceptance Criteria 未達",
            "仕様誤解",
            "機能欠落",
            "テスト失敗",
            "正常系・異常系・境界値不足",
            "振る舞い変更が必要",
            "ケース追加や期待値の再検討が必要",
            "`strict` mode の Red / Green / Refactor 継続",
        )

        for path, workflow in workflows.items():
            with self.subTest(path=path):
                normalized_workflow = "".join(workflow.split())

                for condition in startup_conditions:
                    self.assertIn("".join(condition.split()), normalized_workflow)
                for route in implementer_routes:
                    self.assertIn("".join(route.split()), normalized_workflow)

    def test_repository_distribution_does_not_reference_retired_agent_names(self) -> None:
        """Remove retired names from every distributed source and generated surface."""
        paths = (
            REPOSITORY_ROOT / "shared",
            REPOSITORY_ROOT / "plugins",
            REPOSITORY_ROOT / "scripts",
            REPOSITORY_ROOT / "tests",
        )
        retired_names = (
            "writing-principles-" + "reviewer",
            "refactor-patch-" + "agent",
        )

        for path in paths:
            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue
                content = file_path.read_text(encoding="utf-8")
                for name in retired_names:
                    self.assertNotIn(name, content, file_path)

    def test_repository_workflows_select_delegation_modes_without_crossing_direct_boundary(
        self,
    ) -> None:
        """Select delegation modes while keeping direct work outside the skill."""
        workflows = self._repository_workflow_texts()
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

        for path, workflow in workflows.items():
            with self.subTest(path=path):
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
        workflows = self._repository_workflow_texts()
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

        for path, workflow in workflows.items():
            with self.subTest(path=path):
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


if __name__ == "__main__":
    unittest.main()
