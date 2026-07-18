"""Real-repository contract tests for generated plugin assets."""

from __future__ import annotations

from pathlib import Path
import unittest

from build_plugin_assets_test_support import (
    AGENT_NAMES,
    CLAUDE_MODEL_PROFILES,
    CLAUDE_PROFILE_PATH,
    CODEX_MODEL_PROFILES,
    DELEGATE_SKILL,
    GENERATED_MARKDOWN_WARNING,
    GENERATED_SKILL_REFERENCE_PATHS,
    GENERATED_SKILL_PATHS,
    REPOSITORY_ROOT,
    RepositoryContractSupport,
    SHARED_SKILL_PATH,
    SHARED_SKILL_REFERENCE_PATHS,
    SKILL_REFERENCE_NAMES,
    generated_skill_path,
    generated_skill_reference_path,
    shared_skill_path,
    shared_skill_reference_path,
)


PLAN_SKILL = "plan-implementation-branches"
# 契約が要求する reference 構成をテスト側で明示的に宣言する。生成 mapping への
# 依存を避け、原稿が未整備の状態を「必要ファイルの欠落」として検出させる。
PLAN_REFERENCE_NAMES = (
    "branch-plan-schema.md",
    "branch-splitting.md",
    "plan-review.md",
)


class BuildPluginAssetsRepositoryContractsTest(
    RepositoryContractSupport,
    unittest.TestCase,
):
    def _assert_qa_report_reference_files_exist(self) -> None:
        paths = (
            SHARED_SKILL_REFERENCE_PATHS["qa-report.md"],
            GENERATED_SKILL_REFERENCE_PATHS["claude"]["qa-report.md"],
            GENERATED_SKILL_REFERENCE_PATHS["codex"]["qa-report.md"],
        )
        for path in paths:
            self.assertTrue(
                (REPOSITORY_ROOT / path).is_file(),
                f"missing QA report reference: {path}",
            )

    def _read_qa_report_references(self) -> dict[Path, str]:
        self._assert_qa_report_reference_files_exist()
        return {
            SHARED_SKILL_REFERENCE_PATHS["qa-report.md"]: self._repository_text(
                SHARED_SKILL_REFERENCE_PATHS["qa-report.md"]
            ),
            GENERATED_SKILL_REFERENCE_PATHS["claude"][
                "qa-report.md"
            ]: self._repository_text(
                GENERATED_SKILL_REFERENCE_PATHS["claude"]["qa-report.md"]
            ),
            GENERATED_SKILL_REFERENCE_PATHS["codex"][
                "qa-report.md"
            ]: self._repository_text(
                GENERATED_SKILL_REFERENCE_PATHS["codex"]["qa-report.md"]
            ),
        }

    def _extract_qa_report_template(self, report: str) -> str:
        heading = "## 標準テンプレート"
        opening_fence = "```markdown\n"
        closing_fence = "\n```"
        self.assertEqual(1, report.count(heading))
        template_section = report.split(heading, 1)[1]
        self.assertEqual(1, template_section.count(opening_fence))
        fenced_content = template_section.split(opening_fence, 1)[1]
        self.assertIn(closing_fence, fenced_content)
        return fenced_content.split(closing_fence, 1)[0]

    def _assert_qa_report_template_excludes_raw_fields(self, template: str) -> None:
        forbidden_template_fields = (
            "Conversation:",
            "Prompt:",
            "Raw reviewer output:",
            "Raw command log:",
            "Full command log:",
            "Credential:",
            "Absolute path:",
            "Local checkout path:",
            "Integration checkout / commit",
        )
        for field in forbidden_template_fields:
            self.assertNotIn(field, template)

    def test_repository_skill_uses_progressive_disclosure(self) -> None:
        """Keep the core workflow lean and route each detailed phase explicitly."""
        main_texts = {
            SHARED_SKILL_PATH: self._repository_text(SHARED_SKILL_PATH),
            GENERATED_SKILL_PATHS["claude"]: self._repository_text(
                GENERATED_SKILL_PATHS["claude"]
            ),
            GENERATED_SKILL_PATHS["codex"]: self._repository_text(
                GENERATED_SKILL_PATHS["codex"]
            ),
        }
        reference_headings = {
            "implementation-branches.md": "# 実装枝の準備と委譲",
            "expert-selection.md": "# Expert 選択",
            "qa-and-integration.md": "# QA・修正・統合",
            "qa-report.md": "# 永続 QA レポート",
        }

        for path, main in main_texts.items():
            with self.subTest(path=path):
                self.assertLess(len(main.splitlines()), 300)
                for name in SKILL_REFERENCE_NAMES[DELEGATE_SKILL]:
                    self.assertIn(f"(references/{name})", main)
                for heading in reference_headings.values():
                    self.assertNotIn(heading, main)
                self.assertLess(
                    main.index("(references/implementation-branches.md)"),
                    main.index("(references/expert-selection.md)"),
                )
                self.assertLess(
                    main.index("(references/expert-selection.md)"),
                    main.index("先頭の枝だけを委譲する"),
                )
                self.assertLess(
                    main.index("先頭の枝だけを委譲する"),
                    main.index("(references/qa-and-integration.md)"),
                )
                normalized = "".join(main.split())
                conditional_reference = (
                    "永続QAレポートの出力条件を満たす場合だけ"
                    "[永続QAレポート](references/qa-report.md)を読む"
                )
                self.assertIn(conditional_reference, normalized)
                self.assertEqual(1, main.count("(references/qa-report.md)"))

        self._assert_qa_report_reference_files_exist()
        skills = self._repository_skill_texts()
        for name, heading in reference_headings.items():
            self.assertIn(heading, skills.source_references[name])
            self.assertIn(heading, skills.claude_references[name])
            self.assertIn(heading, skills.codex_references[name])
            self.assertFalse(
                skills.source_references[name].startswith(
                    GENERATED_MARKDOWN_WARNING
                )
            )
            self.assertTrue(
                skills.claude_references[name].startswith(
                    f"{GENERATED_MARKDOWN_WARNING}\n\n"
                )
            )
            self.assertTrue(
                skills.codex_references[name].startswith(
                    f"{GENERATED_MARKDOWN_WARNING}\n\n"
                )
            )

    def test_repository_writes_one_parent_qa_report_only_when_requested(
        self,
    ) -> None:
        """Generate one parent-owned report only after an explicit opt-in."""
        required_contracts = (
            "会話上の最終報告は常に行う。",
            "永続 QA レポートは任意",
            "`lite` / `standard` / `strict`",
            "`direct` は対象外",
            "既定では生成しない",
            "ユーザーの明示的な要求",
            "repository instruction",
            "Acceptance Criteria",
            "いずれかが要求した場合だけ",
            "親の最終判断時に1回",
            "トップレベルの workflow run ごとに report は1つだけ生成",
            "複数の実装枝は同じ report へ列挙",
            "`Accepted`",
            "`Rejected`",
            "`Needs revision`",
            "未実行の検証",
            "未統合の状態",
            "最終判断は親だけが行う",
            "sanitize できない場合は生成しない",
            "生成しなかった理由を会話上の最終報告へ含める",
        )

        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for contract in required_contracts:
                    self.assertIn("".join(contract.split()), normalized)

    def test_repository_qa_report_creation_is_confined_and_non_overwriting(
        self,
    ) -> None:
        """Reject traversal and links, and never overwrite an existing report."""
        required_contracts = (
            "repository root 相対の `.agentic-qa/reports/<slug>.md`",
            "task ID または title",
            "空なら branch",
            "Unicode NFKC",
            "前後の空白を除去",
            "ASCII lowercase",
            "非 `[a-z0-9]` の連続を `-`",
            "連続する `-` と前後の `-` を除去",
            "base は最大64文字",
            "`delegated-implementation`",
            "機密な入力名は使わず fallback",
            "Windows 予約名には `qa-` prefix",
            "`con`, `prn`, `aux`, `nul`, `com1`〜`com9`, `lpt1`〜`lpt9`",
            "path separator を許可しない",
            "`.` または `..` を許可しない",
            "絶対 path を許可しない",
            "reports 直下以外を許可しない",
            "`ＡＢＣ １２３` は `abc-123`",
            "title が `日本語`、branch が `Feature QA` なら `feature-qa`",
            "title と branch が `日本語` なら `delegated-implementation`",
            "`CON` は `qa-con`",
            "既存 file を上書きしない",
            "`<slug>-2.md`, `<slug>-3.md`",
            "最初の空き",
            "suffix 込みの stem は最大80文字",
            "base の末尾を切る",
            "出力先または候補が symlink、directory、非通常 file なら停止",
            "`.agentic-qa` と `reports` の各既存 ancestor component",
            "symlink を追わない `lstat` 相当",
            "symlink または directory 以外なら停止",
            "canonical repository root 外へ解決される場合は停止",
            "生成と削除の両方へ適用",
            "sanitized Markdown Data を先に完成",
            "symlink を追わない exclusive create 相当",
            "1回だけ書く",
            "競合時は書き込まず次の suffix を再選択",
            "安全な create Action を保証できない場合は生成しない",
            "workflow 内では既存 report を更新しない",
        )

        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for contract in required_contracts:
                    self.assertIn("".join(contract.split()), normalized)
                self.assertNotIn(
                    "".join(
                        "既存 report の更新はユーザーが対象 path を明示".split()
                    ),
                    normalized,
                )

    def test_repository_does_not_manage_or_delete_qa_reports_implicitly(
        self,
    ) -> None:
        """Leave Git management, retention, and deletion to explicit policy."""
        required_contracts = (
            "`agentic-qa-workflow` repository の template source と generated asset は tracked 配布物",
            "利用先 repository で生成する report instance",
            "既定では untracked / unstaged / uncommitted",
            "`.gitignore` と `.git/info/exclude` を自動変更しない",
            "`git status` に `??` として表示されてよい",
            "既定では `git add`、stage、commit しない",
            "ユーザーの明示的な要求または既存の repository policy",
            "既存の実装 commit へ黙って amend しない",
            "自動期限または自動 purge を行わない",
            "明示的な削除または repository policy まで保持",
            "reports 配下であることを確認してから削除",
            "通常の削除 commit では Git 履歴から機密情報を消去できない",
            "親の統合 checkout へ保存",
            "削除予定の worker worktree へ保存しない",
        )

        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for contract in required_contracts:
                    self.assertIn("".join(contract.split()), normalized)

    def test_repository_qa_report_persists_only_sanitized_evidence(self) -> None:
        """Persist only minimal reviewed evidence without secrets or raw transcripts."""
        prohibited_content = (
            "会話全文",
            "prompt",
            "reviewer の生出力",
            "command の全 log",
            "token",
            "password",
            "cookie",
            "Authorization",
            "private key",
            "`.env`",
            "credential 付き URL",
            "機密 query",
            "個人情報",
        )
        sanitized_evidence_contracts = (
            "file は repository 相対 path",
            "worktree は論理 ID、branch、cleanup 状態",
            "Implementer は role 名",
            "command は sanitize 済み文字列、status、短い要約",
            "次の機密情報と生の証跡を保存しない",
            "絶対 path と local checkout path を保存しない",
            "branch と file が敏感なら省略または sanitize",
            "保存直前に親が report 全体を確認",
        )

        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for contract in prohibited_content + sanitized_evidence_contracts:
                    self.assertIn("".join(contract.split()), normalized)

    def test_repository_qa_report_normalizes_untrusted_markdown_fields(
        self,
    ) -> None:
        """Render untrusted values as escaped single-line Markdown text."""
        required_contracts = (
            "untrusted field",
            "改行 `\\n` と control 文字を空白へ置換して単一行",
            "Markdown context に応じて metacharacter を escape",
            "HTML、link、image を plain text として escape",
            "`line 1\\nline 2` は `line 1 line 2`",
            "`<b>admin</b>` は `&lt;b&gt;admin&lt;/b&gt;`",
            "`[label](https://example.invalid)` は plain text として escape",
            "`![alt](https://example.invalid/image.png)` は plain text として escape",
        )

        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for contract in required_contracts:
                    self.assertIn("".join(contract.split()), normalized)

    def test_repository_qa_report_template_exposes_complete_parent_qa(self) -> None:
        """Expose every decision and verification gap needed for parent acceptance."""
        required_fields = (
            "Sanitized task ID / title",
            "Mode",
            "Base commit",
            "Logical checkout ID / commit",
            "Implementation branches",
            "Acceptance Criteria → test",
            "Changed files",
            "Verification",
            "`Pass` / `Fail` / `Not run`",
            "`Not run` は理由必須",
            "Red / Green / Refactor",
            "Responsibility boundaries",
            "Test quality",
            "Writing principles",
            "Security / side effects",
            "Integrated diff review",
            "Residual risks",
            "Parent decision",
            "`Accepted` / `Rejected` / `Needs revision`",
            "判断理由",
            "Next action",
            "reviewer を起動しなかった場合も理由を記録",
            "対象 risk がないことは有効な理由",
            "最終判断は親だけが記入",
        )

        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for field in required_fields:
                    self.assertIn("".join(field.split()), normalized)

                template = self._extract_qa_report_template(report)
                required_template_fields = (
                    "Logical checkout ID / commit",
                    "Logical worktree ID",
                    "Branch (sanitized or omitted)",
                    "Implementer role",
                    "Sanitized command",
                    "Status",
                    "Short summary",
                )
                for field in required_template_fields:
                    self.assertIn(field, template)
                self._assert_qa_report_template_excludes_raw_fields(template)

    def test_repository_writes_qa_report_after_cleanup_and_before_chat_report(
        self,
    ) -> None:
        """Persist cleanup outcomes before sending the required chat report."""
        skills = self._repository_skill_texts()
        main_texts = (
            skills.source_main,
            skills.claude_main,
            skills.codex_main,
        )
        cleanup_instruction = "cleanup の実施可否と結果を確定する"
        report_reference = "(references/qa-report.md)"
        final_report = "会話上の最終報告を行う"

        for main in main_texts:
            normalized = " ".join(main.split())
            self.assertIn(cleanup_instruction, normalized)
            self.assertIn(report_reference, normalized)
            self.assertIn(final_report, normalized)
            self.assertLess(
                normalized.index(cleanup_instruction),
                normalized.index(report_reference),
            )
            self.assertLess(
                normalized.index(report_reference),
                normalized.index(final_report),
            )

        required_reference_contracts = (
            "最終 gate 後に cleanup の実施可否と結果を確定してから",
            "出力条件を満たす場合だけ report を生成",
            "`Needs revision` などで worktree を保持する場合も cleanup 状態と理由を記録",
        )
        for path, report in self._read_qa_report_references().items():
            with self.subTest(path=path):
                normalized = "".join(report.split())
                for contract in required_reference_contracts:
                    self.assertIn("".join(contract.split()), normalized)

    def test_repository_continues_revisions_but_finalizes_unintegrated_termination(
        self,
    ) -> None:
        """Continue revisions; finalize only an explicit unintegrated decision."""
        skills = self._repository_skill_texts()
        main = "".join(skills.source_main.split())
        qa_reference = skills.source_references["qa-and-integration.md"]
        qa_and_integration = "".join(qa_reference.split())
        unintegrated_section = qa_reference[
            qa_reference.index("## 未統合で終了する場合") : qa_reference.index(
                "## 責務境界"
            )
        ]
        normalized_unintegrated_section = "".join(unintegrated_section.split())
        revision_continuation = (
            "QA 修正を続ける場合は手順7の修正経路を継続する。"
        )
        unintegrated_termination = (
            "親が未統合の枝について `Rejected` / `Needs revision` を最終判断とし、"
            "top-level workflow を終了する場合は、手順9へ進む。"
        )
        finalization = (
            "全枝を完了した場合、または手順8で未統合のまま終了する場合は、"
            "適用可能な統合済み diff review と最終検証を行い、親の最終判断を確定する。"
        )
        cleanup_decision = (
            "最終 gate 後に、各 worker worktree の cleanup の実施可否と結果を確定する。"
        )
        final_decision_invariant = (
            "全ての委譲 mode で、親の最終判断を省略しない。"
            "受け入れた枝では統合後の検証を省略しない。"
        )
        main_contracts = (
            revision_continuation,
            unintegrated_termination,
            finalization,
            cleanup_decision,
            final_decision_invariant,
        )
        reference_contracts = (
            "通常の `Needs revision` は上の修正先へ差し戻し、top-level workflow を継続する。",
            "親が未統合の枝について `Rejected` / `Needs revision` を最終判断とし、top-level workflow を終了する場合だけ",
            "実行可能な検証を行い",
            "未実行の検証、未統合の理由、worktree を保持する理由",
            "Data として記録",
            "main の手順9へ戻る",
        )

        for contract in main_contracts:
            self.assertIn("".join(contract.split()), main)
        for contract in reference_contracts:
            self.assertIn("".join(contract.split()), qa_and_integration)
        self.assertNotIn("cleanup", normalized_unintegrated_section)
        self.assertNotIn(
            "".join(
                "全ての委譲 mode で、親による統合後の検証と最終的な受け入れ判断を省略しない。".split()
            ),
            main,
        )

        normalized_termination = "".join(unintegrated_termination.split())
        normalized_finalization = "".join(finalization.split())
        normalized_cleanup_decision = "".join(cleanup_decision.split())
        self.assertLess(
            main.index(normalized_termination),
            main.index(normalized_finalization),
        )
        self.assertLess(
            main.index(normalized_finalization),
            main.index(normalized_cleanup_decision),
        )
        self.assertLess(
            main.index(normalized_cleanup_decision),
            main.index("(references/qa-report.md)"),
        )

    def test_repository_workflow_normalizes_implementation_branch_boundaries(
        self,
    ) -> None:
        """Use one isolated branch lifecycle without silent direct fallback."""
        workflows = self._repository_workflow_texts()
        required_contract = (
            "各実装枝は専用 worktree で隔離する。",
            "worktree を用意できない場合は委譲を開始しない。",
            "ユーザーの確認なく親の直接実装へ切り替えない。",
            "共有土台の作成は、実装枝の委譲前に親が行える明示的な例外",
            "返却後の機能修正を親が引き取る根拠にはしない。",
            "4. **Refactor と再検証**",
            "テスト計画では commit を作らない。",
            "Red、Green、Refactor の各段階では、段階の変更を commit する。",
            "最終返却では先頭から末尾までの commit SHA range を返す。",
        )

        for path, workflow in workflows.items():
            with self.subTest(path=path):
                normalized = "".join(workflow.split())
                for contract in required_contract:
                    self.assertIn("".join(contract.split()), normalized)

    def test_repository_expert_availability_rules_are_platform_specific(self) -> None:
        """Keep unavailable expert profile names out of the other platform."""
        source = self._repository_text(
            SHARED_SKILL_REFERENCE_PATHS["expert-selection.md"]
        )
        claude = self._repository_text(
            GENERATED_SKILL_REFERENCE_PATHS["claude"]["expert-selection.md"]
        )
        codex = self._repository_text(
            GENERATED_SKILL_REFERENCE_PATHS["codex"]["expert-selection.md"]
        )

        self.assertIn("Fable", source)
        self.assertIn("`gpt-5.6-sol`", source)
        self.assertIn("Fable", claude)
        self.assertNotIn("`gpt-5.6-sol`", claude)
        self.assertIn("`gpt-5.6-sol`", codex)
        self.assertNotIn("Fable", codex)

    def test_repository_implementers_follow_mode_and_writing_contracts(self) -> None:
        """Align every implementer with delegated stages and Why Not comments."""
        for name in ("implementer", "senior-implementer", "expert-implementer"):
            paths = (
                Path("shared/agents") / f"{name}.md",
                Path("plugins/claude/agents") / f"{name}.md",
                Path("plugins/codex/install/agents") / f"{name}.toml",
            )
            for path in paths:
                with self.subTest(name=name, path=path):
                    content = self._repository_text(path)
                    self.assertIn("委譲 mode", content)
                    self.assertIn("指定された段階を越えない", content)
                    self.assertIn("Why Not", content)
                    self.assertIn("返却 commit SHA range", content)
                    self.assertNotIn(
                        "ロジック・制約・前提・テストの意図を残す",
                        content,
                    )

        for name in ("implementer", "senior-implementer"):
            source = self._repository_text(Path("shared/agents") / f"{name}.md")
            self.assertIn(
                "`lite` では親が求めた場合だけ Red 証跡と AC 対応表を返す",
                source,
            )
            self.assertIn(
                "`standard` では Red 証跡と AC 対応表を必ず返す",
                source,
            )

    def test_repository_implementer_worktree_inputs_use_parent_managed_contract(
        self,
    ) -> None:
        """Give both platforms a parent-managed worktree and start-condition gate."""
        start_condition_contracts = (
            "絶対 worktree path と branch",
            "`pwd -P`",
            "`git status --short` が空",
            "基準 commit",
            "着手せず",
        )
        for name in ("implementer", "senior-implementer", "expert-implementer"):
            claude = self._repository_text(
                Path("plugins/claude/agents") / f"{name}.md"
            )
            codex = self._repository_text(
                Path("plugins/codex/install/agents") / f"{name}.toml"
            )

            for platform, content in (("claude", claude), ("codex", codex)):
                with self.subTest(name=name, platform=platform):
                    normalized = "".join(content.split())
                    for contract in start_condition_contracts:
                        self.assertIn("".join(contract.split()), normalized)

            with self.subTest(name=name, platform="claude", check="no-isolation"):
                self.assertNotIn('isolation: "worktree"', claude)
                self.assertNotIn(
                    "起動後に実際の worktree path と branch を確認",
                    claude,
                )

    def test_repository_reviewers_separate_boundary_and_safety_risks(self) -> None:
        """Route placement concerns separately from security and failure safety."""
        responsibility = self._repository_text(
            Path("shared/agents/responsibility-boundary-reviewer.md")
        )
        security = self._repository_text(
            Path("shared/agents/security-side-effect-reviewer.md")
        )

        self.assertIn("副作用をどの責務境界へ配置したか", responsibility)
        self.assertIn(
            "認可・機密性・破壊安全性の評価は対象外",
            responsibility,
        )
        self.assertIn("認可、機密性、破壊安全性", security)
        self.assertIn(
            "命名や責務配置そのものの再設計は対象外",
            security,
        )
        test_quality = self._repository_text(
            Path("shared/agents/test-quality-reviewer.md")
        )
        self.assertIn(
            "AC と diff から必要な追加 case を導出することは対象内",
            test_quality,
        )

    def test_repository_codex_skill_waits_for_each_worker_response(self) -> None:
        """Keep Codex workers alive and waiting until each delegated task responds."""
        skills = self._repository_skill_texts()
        required_instructions = (
            "対象 worker ごとに `wait_agent` を繰り返し使い、完了通知または返答が返るまで待機する。",
            "数分間の無応答を理由に worker を `shutdown` または `interrupt_agent` しない。",
            "ユーザーが明示的に取り消した場合、または tool が回復不能な異常を報告した場合は例外",
        )

        for instruction in required_instructions:
            self.assertIn(instruction, skills.source)
            self.assertIn(instruction, skills.codex)
            self.assertNotIn(instruction, skills.claude)

    def test_repository_codex_runs_the_integrated_review_gate(self) -> None:
        """Prefer Codex /review before cleanup when the environment provides it."""
        skills = self._repository_skill_texts()
        instruction = (
            "環境が提供する場合は `/review` を実行し、利用できない場合は"
            "同等の統合済み diff review を親が行う。"
        )

        self.assertIn(instruction, skills.source_references["qa-and-integration.md"])
        self.assertIn(instruction, skills.codex_references["qa-and-integration.md"])
        self.assertNotIn(instruction, skills.claude_references["qa-and-integration.md"])

    def test_repository_skills_clean_up_only_after_the_final_gate(self) -> None:
        """Clean up platform resources only after every final gate has passed."""
        skills = self._repository_skill_texts()

        self.assertIn("## 後始末", skills.source)
        self.assertIn("最終ゲートをすべて通過した後", skills.claude)
        self.assertIn("親がこのタスク用に作成した", skills.claude)
        self.assertIn("`git worktree remove <worktree path>`", skills.claude)
        self.assertIn("最終ゲートをすべて通過した後", skills.codex)
        self.assertIn("親がこのタスク用に作成した", skills.codex)
        self.assertIn("`git worktree remove <worktree path>`", skills.codex)
        self.assertIn("親がこのワークフローで起動した agent を停止する。", skills.codex)
        self.assertNotIn("親がこのワークフローで起動した agent を停止する。", skills.claude)
        self.assertNotIn('isolation: "worktree"', skills.claude)

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
            "コードから読み取れない確定済みの設計判断や制約",
            "委譲 mode と TDD 要件",
            "検証 command",
            "完了条件",
            "commit と返却報告の形式",
        )

        for item in required_data:
            for skill in skills.all_texts():
                self.assertIn(item, skill)

        self.assertIn("絶対 worktree path と branch 名", skills.source)
        self.assertIn("絶対 worktree path と branch 名", skills.claude)
        self.assertIn("絶対 worktree path と branch 名", skills.codex)
        self.assertNotIn("worktree の隔離条件", skills.claude)

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
                "テスト計画→失敗テスト→実装→Refactor の段階ゲートに分ける。",
            ),
        )
        required_rules = (
            "- 委譲 mode: <lite / standard / strict>",
            "`lite` では、親が明示した場合だけ AC 対応表と Red 時点の失敗出力を付けること。",
            "`standard` では、Red 時点の失敗出力と",
            "「AC-n → それを検証するテスト名 → 期待値の根拠（仕様のどこから導いたか）」"
            "の対応表を必ず付けること。",
            "最終返却には `standard` と同じ AC 対応表と Red 証跡を含める。",
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

    def test_repository_workflows_limit_green_red_evidence_to_regression_tests(
        self,
    ) -> None:
        skills = self._repository_skill_texts()
        implementation_contracts = (
            "新機能または未実装仕様を検証する test は Red 必須",
            "既存挙動を固定する regression test",
            "追加時点で Green",
            "既存挙動を固定する追補 test であること",
            "対応する AC",
            "期待値の根拠",
            "既存実装がすでに仕様を満たしていたこと",
            "形式的な Red を作るために本番 code を一時変更してはならない",
            "mutation は親が明示した一時検証に限定",
            "mutation を commit してはならない",
            "変更禁止範囲や本番 code を mutation の対象にしてはならない",
            "regression Green 例外の Red 段階では passing test を commit",
            "変更がない Green / Refactor 段階に空 commit を作らない",
        )
        qa_contracts = (
            "AC、test、期待値の根拠、既存挙動の対応",
            "新機能または未実装仕様なら Red",
            "regression test が追加時点で Green",
        )
        intake_contracts = (
            "新機能または未実装仕様",
            "既存挙動を固定する regression test",
            "分類できない場合は Green 例外を適用せず判断点として返す",
        )

        reference_sets = (
            skills.source_references,
            skills.claude_references,
            skills.codex_references,
        )
        for references in reference_sets:
            for reference, contracts in (
                ("implementation-branches.md", implementation_contracts),
                ("qa-and-integration.md", qa_contracts),
                ("branch-plan-intake.md", intake_contracts),
            ):
                with self.subTest(reference=reference):
                    normalized = "".join(references[reference].split())
                    for contract in contracts:
                        self.assertIn("".join(contract.split()), normalized)

    def test_repository_implementers_return_regression_green_evidence(
        self,
    ) -> None:
        required_contracts = (
            "新機能または未実装仕様では Red を必須",
            "既存挙動を固定する regression test に限り追加時点の Green を許可",
            "既存挙動を固定する追補 test であること",
            "対応する AC",
            "期待値の根拠",
            "既存実装がすでに仕様を満たしていたこと",
            "形式的な Red のために本番 code を変更しない",
            "親が明示した一時 mutation 検証だけを行い、commit しない",
            "変更禁止範囲と本番 code を mutation の対象にしない",
        )

        for name in ("implementer", "senior-implementer", "expert-implementer"):
            paths = (
                Path("shared/agents") / f"{name}.md",
                Path("plugins/claude/agents") / f"{name}.md",
                Path("plugins/codex/install/agents") / f"{name}.toml",
            )
            for path in paths:
                with self.subTest(name=name, path=path):
                    normalized = "".join(self._repository_text(path).split())
                    for contract in required_contracts:
                        self.assertIn("".join(contract.split()), normalized)

    def test_repository_decision_corpus_covers_red_and_regression_green_cases(
        self,
    ) -> None:
        corpus = self._repository_text(Path("evals/workflow-decision-corpus.md"))
        required_contracts = (
            "## EVAL-11: 新機能では Red 証跡が必須",
            "新機能または未実装仕様",
            "Red 時点の失敗出力を必須",
            "## EVAL-12: regression test の追加時点 Green 例外",
            "既存挙動を固定する追補 test",
            "期待値の根拠",
            "既存実装がすでに仕様を満たしていた",
            "形式的 Red のために本番 code を変更しない",
            "mutation を commit しない",
            "親が AC、test、期待値の根拠、既存挙動の対応を確認",
        )
        normalized = "".join(corpus.split())
        for contract in required_contracts:
            self.assertIn("".join(contract.split()), normalized)

    def test_repository_decision_corpus_records_parent_managed_worktree_contract(
        self,
    ) -> None:
        """Fix the issue #49 worktree verification record and its retired-contract cleanup."""
        corpus = self._repository_text(Path("evals/workflow-decision-corpus.md"))
        normalized = "".join(corpus.split())

        required_contracts = (
            "### worktree 契約の検証記録(issue #49)",
            "親管理 worktree 契約を採用し、`isolation: \"worktree\"` を廃止する",
            "HEAD 不一致を検出し、reset / merge / checkout などの自力修復を試みず",
            "`git worktree remove` と `git branch -D`",
            "既知の制約",
            "## EVAL-19: 開始条件不成立を検出した未着手返却",
            "契約通りの正常動作として扱う",
            "branch 不一致、dirty status のいずれであっても同じ扱いとする。",
            "worktree を基準 commit から作り直し",
            "Implementer へ reset / merge / checkout などの自力修復を指示しない。",
            "未着手返却を失敗として扱い、Implementer を責める、または mode を引き下げる。",
            "HEAD 不一致だけを特別扱いし、path 不一致・branch 不一致・dirty status を異なる扱いにする。",
            "Claude Code と Codex は「platform 共通の期待」に記載した起動、継続 mechanism だけが異なる。",
            "Red 必須と親 QA は共通であり、agent の起動 mechanism だけが異なる。",
            "引き上げ受諾後の段階継続 mechanism は platform に合わせてよい。",
        )
        for contract in required_contracts:
            self.assertIn("".join(contract.split()), normalized)

        stale_contracts = (
            "Claude Code と Codex は「platform 共通の期待」に記載した worktree 準備、"
            "起動、継続 mechanism だけが異なる。",
            "Red 必須と親 QA は共通であり、worktree と agent の起動 mechanism だけが異なる。",
            "引き上げ受諾後の worktree 準備・段階継続 mechanism は platform に合わせてよい。",
        )
        for contract in stale_contracts:
            self.assertNotIn("".join(contract.split()), normalized)

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


class PlanImplementationBranchesContractsTest(
    RepositoryContractSupport,
    unittest.TestCase,
):
    def _plan_skill_texts(self) -> dict[str, str]:
        return {
            "source": self._repository_text(shared_skill_path(PLAN_SKILL)),
            "claude": self._repository_text(
                generated_skill_path("claude", PLAN_SKILL)
            ),
            "codex": self._repository_text(
                generated_skill_path("codex", PLAN_SKILL)
            ),
        }

    def _plan_reference_texts(self, name: str) -> dict[str, str]:
        return {
            "source": self._repository_text(
                shared_skill_reference_path(PLAN_SKILL, name)
            ),
            "claude": self._repository_text(
                generated_skill_reference_path("claude", PLAN_SKILL, name)
            ),
            "codex": self._repository_text(
                generated_skill_reference_path("codex", PLAN_SKILL, name)
            ),
        }

    def test_plan_skill_exposes_platform_frontmatter_and_reference_links(
        self,
    ) -> None:
        """Expose planning frontmatter and route each detail to its reference."""
        for platform in ("claude", "codex"):
            main = self._plan_skill_texts()[platform]
            with self.subTest(platform=platform):
                self.assertTrue(main.startswith(f"---\nname: {PLAN_SKILL}\n"))
                self.assertLess(len(main.splitlines()), 300)
                for name in PLAN_REFERENCE_NAMES:
                    self.assertIn(f"(references/{name})", main)
                self.assertNotIn("<!-- claude-only", main)
                self.assertNotIn("<!-- codex-only", main)

    def test_plan_references_carry_generated_warning_and_table_of_contents(
        self,
    ) -> None:
        """Give each planning reference a warning-free source and a table of contents."""
        for name in PLAN_REFERENCE_NAMES:
            texts = self._plan_reference_texts(name)
            with self.subTest(reference=name):
                self.assertFalse(
                    texts["source"].startswith(GENERATED_MARKDOWN_WARNING)
                )
                self.assertTrue(texts["source"].startswith("# "))
                self.assertIn("## 目次", texts["source"])
                for platform in ("claude", "codex"):
                    reference = texts[platform]
                    self.assertTrue(
                        reference.startswith(f"{GENERATED_MARKDOWN_WARNING}\n\n")
                    )
                    self.assertIn("## 目次", reference)

    def test_plan_schema_reference_holds_the_canonical_schema(self) -> None:
        """Carry the confirmed schema, violation codes, transitions, and tests meaning."""
        required = (
            "status: blocked | awaiting_review | approved",
            "confirmation_mode: review | auto",
            "delegation:",
            "authorized: false",
            "| code | 検査内容 |",
            "duplicate-id",
            "unknown-reference",
            "branch-without-primary-ac",
            "delegation-invalid",
            "mode-proposal-invalid",
            "## 状態遷移と権限",
            "## tests / stage_tests の意味",
        )
        excluded = (
            "## implementation_stages の実行規約",
            "## Executor 側の再検証",
            "## レビュー指摘への対応",
            "## 再レビュー指摘への対応",
            "## issue #46 確定事項からの意図的な変更",
        )
        for platform, text in self._plan_reference_texts(
            "branch-plan-schema.md"
        ).items():
            with self.subTest(platform=platform):
                normalized = "".join(text.split())
                for contract in required:
                    self.assertIn("".join(contract.split()), normalized)
                for section in excluded:
                    self.assertNotIn("".join(section.split()), normalized)

    def test_plan_skill_matches_confirmed_schema_contract(self) -> None:
        """Separate approval from delegation and never start delegation from the skill."""
        required = (
            "承認と委譲開始権限は独立",
            "`delegation.authorized` は常に `false`",
            "確認モードの既定は `review`",
            "`auto` はユーザーが明示した場合のみ",
            "`delegate-implementation` を直接起動しない",
            "blocking な不足は `unresolved_decisions`",
            "minor な不足は `assumptions`",
        )
        for platform, main in self._plan_skill_texts().items():
            with self.subTest(platform=platform):
                normalized = "".join(main.split())
                for contract in required:
                    self.assertIn("".join(contract.split()), normalized)


INTAKE_REFERENCE = "branch-plan-intake.md"
PLAN_SCHEMA_REFERENCE = "branch-plan-schema.md"


class DelegateImplementationIntakeContractsTest(
    RepositoryContractSupport,
    unittest.TestCase,
):
    def _assert_intake_reference_files_exist(self) -> None:
        paths = (
            shared_skill_reference_path(DELEGATE_SKILL, INTAKE_REFERENCE),
            generated_skill_reference_path("claude", DELEGATE_SKILL, INTAKE_REFERENCE),
            generated_skill_reference_path("codex", DELEGATE_SKILL, INTAKE_REFERENCE),
        )
        for path in paths:
            self.assertTrue(
                (REPOSITORY_ROOT / path).is_file(),
                f"missing intake reference: {path}",
            )

    def _intake_reference_texts(self) -> dict[str, str]:
        self._assert_intake_reference_files_exist()
        return {
            "source": self._repository_text(
                shared_skill_reference_path(DELEGATE_SKILL, INTAKE_REFERENCE)
            ),
            "claude": self._repository_text(
                generated_skill_reference_path(
                    "claude", DELEGATE_SKILL, INTAKE_REFERENCE
                )
            ),
            "codex": self._repository_text(
                generated_skill_reference_path(
                    "codex", DELEGATE_SKILL, INTAKE_REFERENCE
                )
            ),
        }

    def _delegate_skill_texts(self) -> dict[str, str]:
        return {
            "source": self._repository_text(shared_skill_path(DELEGATE_SKILL)),
            "claude": self._repository_text(
                generated_skill_path("claude", DELEGATE_SKILL)
            ),
            "codex": self._repository_text(
                generated_skill_path("codex", DELEGATE_SKILL)
            ),
        }

    def test_intake_reference_is_generated_with_warning_and_toc(self) -> None:
        """Distribute the intake reference to both platforms with a warning-free source."""
        texts = self._intake_reference_texts()
        self.assertTrue(texts["source"].startswith("# "))
        self.assertFalse(texts["source"].startswith(GENERATED_MARKDOWN_WARNING))
        self.assertIn("## 目次", texts["source"])
        for platform in ("claude", "codex"):
            reference = texts[platform]
            with self.subTest(platform=platform):
                self.assertTrue(
                    reference.startswith(f"{GENERATED_MARKDOWN_WARNING}\n\n")
                )
                self.assertIn("## 目次", reference)

    def test_delegate_skill_links_to_the_intake_reference(self) -> None:
        """Route a confirmed Branch Plan through the intake reference from SKILL.md."""
        for platform, main in self._delegate_skill_texts().items():
            with self.subTest(platform=platform):
                self.assertIn(f"(references/{INTAKE_REFERENCE})", main)
                self.assertLess(len(main.splitlines()), 300)
                normalized = "".join(main.split())
                self.assertIn(
                    "".join("確定済み Branch Plan が渡されている場合は".split()),
                    normalized,
                )

    def test_intake_reference_moves_execution_and_revalidation_sections(self) -> None:
        """Carry the execution and revalidation sections as the canonical source."""
        moved_sections = (
            "## implementation_stages の実行規約",
            "## Executor 側の再検証",
        )
        moved_body = (
            "stages を宣言した枝は `strict` の段階ゲート機構で実行する。",
            "各 stage を `strict` の1サイクル(テスト計画 → Red → Green → Refactor)"
            "として実行する。",
            "`status: approved` であり、`approval.method` が設定済みである。",
            "blocking violation code 表のすべての検査規則を入力 Data から再計算し、"
            "違反が0件である。",
        )
        for platform, text in self._intake_reference_texts().items():
            with self.subTest(platform=platform):
                for section in moved_sections:
                    self.assertIn(section, text)
                normalized = "".join(text.split())
                for body in moved_body:
                    self.assertIn("".join(body.split()), normalized)

    def test_intake_reference_declares_the_acceptance_gate_rules(self) -> None:
        """Re-validate before delegation and fall back to inline splitting otherwise."""
        gate_rules = (
            "「Executor 側の再検証」の4項目を委譲開始前に",
            "再検証を満たさない場合は実装を開始せず",
            "既存の委譲 prompt の Data へそのまま流し込む",
            "委譲 prompt の必須テストと検証 command で",
            "Branch Plan が渡されていない場合は、現行どおり親が inline に枝を分ける。",
            "`plan-implementation-branches` の使用を",
        )
        for platform, text in self._intake_reference_texts().items():
            with self.subTest(platform=platform):
                normalized = "".join(text.split())
                for rule in gate_rules:
                    self.assertIn("".join(rule.split()), normalized)

    def test_intake_reference_resolves_the_cross_skill_schema_link(self) -> None:
        """Resolve the schema code table link across shared and generated trees."""
        relative_link = (
            "../../plan-implementation-branches/references/branch-plan-schema.md"
        )
        intake_paths = {
            "source": shared_skill_reference_path(DELEGATE_SKILL, INTAKE_REFERENCE),
            "claude": generated_skill_reference_path(
                "claude", DELEGATE_SKILL, INTAKE_REFERENCE
            ),
            "codex": generated_skill_reference_path(
                "codex", DELEGATE_SKILL, INTAKE_REFERENCE
            ),
        }
        texts = self._intake_reference_texts()
        for structure, intake_path in intake_paths.items():
            with self.subTest(structure=structure):
                self.assertIn(relative_link, texts[structure])
                resolved = (REPOSITORY_ROOT / intake_path).parent / relative_link
                self.assertTrue(
                    resolved.resolve().is_file(),
                    f"unresolved cross-skill link from {intake_path}",
                )


if __name__ == "__main__":
    unittest.main()
