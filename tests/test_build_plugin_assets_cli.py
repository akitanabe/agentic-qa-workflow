"""Isolated-repository CLI behavior tests for the plugin asset generator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib
import unittest

from build_plugin_assets_test_support import (
    AGENT_NAMES,
    DELEGATE_SKILL,
    GENERATED_SKILL_REFERENCE_PATHS,
    GENERATED_MARKDOWN_WARNING,
    GENERATED_TOML_WARNING,
    IsolatedRepositorySupport,
    PLATFORMS,
    REFACTORER_NAMES,
    REVIEWER_NAMES,
    SHARED_SKILL_PATH,
    SHARED_SKILL_REFERENCE_PATHS,
    SKILL_REFERENCE_NAMES,
    generated_skill_path,
    generated_skill_reference_path,
    shared_skill_path,
    shared_skill_reference_path,
)


class BuildPluginAssetsCliTest(IsolatedRepositorySupport, unittest.TestCase):
    """Verify the generator only through its documented command-line interface."""

    def test_build_generates_all_assets_and_syncs_versions(self) -> None:
        """Generate skill packages, eighteen agent assets, and synchronized versions."""
        with self._temporary_repository() as root:
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
        with self._temporary_repository() as root:
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

    def test_build_generates_platform_specific_skill_references(self) -> None:
        """Render every canonical reference with the same marker and term rules."""
        with self._temporary_repository() as root:
            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            self.assertEqual("", result.stderr)
            for name in SKILL_REFERENCE_NAMES[DELEGATE_SKILL]:
                claude = (
                    root / GENERATED_SKILL_REFERENCE_PATHS["claude"][name]
                ).read_text(encoding="utf-8")
                codex = (
                    root / GENERATED_SKILL_REFERENCE_PATHS["codex"][name]
                ).read_text(encoding="utf-8")

                self.assertTrue(
                    claude.startswith(f"{GENERATED_MARKDOWN_WARNING}\n\n")
                )
                self.assertTrue(
                    codex.startswith(f"{GENERATED_MARKDOWN_WARNING}\n\n")
                )
                self.assertIn(
                    "Parent Claude agent reference uses SendMessage.",
                    claude,
                )
                self.assertIn(f"Claude reference only: {name}.", claude)
                self.assertNotIn("Codex reference only:", claude)
                self.assertIn(
                    "Parent Codex agent reference uses followup_task.",
                    codex,
                )
                self.assertIn(f"Codex reference only: {name}.", codex)
                self.assertNotIn("Claude reference only:", codex)
                self.assertNotIn("<!-- claude-only", claude + codex)
                self.assertNotIn("<!-- codex-only", claude + codex)
                self.assertTrue(claude.endswith("\n"))
                self.assertTrue(codex.endswith("\n"))

    def test_build_generates_every_registered_skill(self) -> None:
        """Generate SKILL.md and references for each mapping entry on both platforms."""
        extra = {"secondary-workflow": ("alpha.md", "beta.md")}
        with self._temporary_repository(extra_skills=extra) as root:
            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            self.assertEqual("", result.stderr)
            for platform in PLATFORMS:
                skill = root / generated_skill_path(platform, "secondary-workflow")
                self.assertTrue(skill.is_file(), skill)
                for name in extra["secondary-workflow"]:
                    reference = root / generated_skill_reference_path(
                        platform, "secondary-workflow", name
                    )
                    self.assertTrue(reference.is_file(), reference)
                    self.assertTrue(
                        reference.read_text(encoding="utf-8").startswith(
                            f"{GENERATED_MARKDOWN_WARNING}\n\n"
                        )
                    )
                self.assertTrue(
                    (root / generated_skill_path(platform, DELEGATE_SKILL)).is_file()
                )

    def test_build_generates_skill_without_references(self) -> None:
        """Emit only SKILL.md for a registered skill that maps to no references."""
        extra = {"reference-free": ()}
        with self._temporary_repository(extra_skills=extra) as root:
            result = self._run(root)

            self.assertEqual(0, result.returncode, result)
            self.assertEqual("", result.stderr)
            for platform in PLATFORMS:
                self.assertTrue(
                    (root / generated_skill_path(platform, "reference-free")).is_file()
                )
                self.assertFalse(
                    (
                        root / f"plugins/{platform}/skills/reference-free/references"
                    ).exists()
                )

    def test_build_rejects_unknown_skill_directory(self) -> None:
        """Reject a skill directory that no mapping entry registers."""
        with self._temporary_repository() as root:
            self._write(
                root,
                "shared/skill/unregistered/SKILL.md",
                "---\nname: unregistered\ndescription: x\n---\n\n# body\n",
            )
            before = self._snapshot(self._generated_paths(root))

            self._assert_validation_error(
                root,
                ("shared/skill/unregistered",),
                before,
            )

    def test_build_requires_and_bounds_every_registered_skill_source(self) -> None:
        """Require each mapped source and reject unknown Markdown for every skill."""
        extra = {"secondary-workflow": ("alpha.md",)}

        def remove_skill(root: Path) -> str:
            path = shared_skill_path("secondary-workflow")
            (root / path).unlink()
            return path.as_posix()

        def remove_reference(root: Path) -> str:
            path = shared_skill_reference_path("secondary-workflow", "alpha.md")
            (root / path).unlink()
            return path.as_posix()

        def add_unknown_markdown(root: Path) -> str:
            path = "shared/skill/secondary-workflow/notes.md"
            self._write(root, path, "# stray\n")
            return path

        def add_unknown_reference(root: Path) -> str:
            path = "shared/skill/secondary-workflow/references/stray.md"
            self._write(root, path, "# stray\n")
            return path

        for label, mutate in {
            "missing SKILL.md": remove_skill,
            "missing reference": remove_reference,
            "unknown skill Markdown": add_unknown_markdown,
            "unknown reference Markdown": add_unknown_reference,
        }.items():
            with (
                self.subTest(label=label),
                self._temporary_repository(extra_skills=extra) as root,
            ):
                expected_path = mutate(root)
                before = self._snapshot(self._generated_paths(root, extra_skills=extra))

                self._assert_validation_error(root, (expected_path,), before)

    def test_check_detects_stale_output_for_each_registered_skill(self) -> None:
        """Report one registered skill's stale artifact while leaving others intact."""
        extra = {"secondary-workflow": ("alpha.md",)}
        with self._temporary_repository(extra_skills=extra) as root:
            build = self._run(root)
            self.assertEqual(0, build.returncode, build)

            stale = root / generated_skill_reference_path(
                "claude", "secondary-workflow", "alpha.md"
            )
            stale.write_text("stale\n", encoding="utf-8", newline="")
            paths = self._generated_paths(root, extra_skills=extra)
            before = self._snapshot(paths)

            result = self._run(root, "--check")

            self.assertEqual(1, result.returncode, result)
            self.assertEqual("", result.stdout)
            self.assertIn(
                generated_skill_reference_path(
                    "claude", "secondary-workflow", "alpha.md"
                ).as_posix(),
                result.stderr,
            )
            self.assertEqual(before, self._snapshot(paths))

    def test_build_accepts_whitespace_around_marker_lines(self) -> None:
        """Treat a marker as valid after stripping leading and trailing whitespace."""
        with self._temporary_repository() as root:
            source = root / SHARED_SKILL_PATH
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
            with self.subTest(label=label), self._temporary_repository() as root:
                source = root / SHARED_SKILL_PATH
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
                    (SHARED_SKILL_PATH.as_posix(),),
                    before,
                )

                self.assertRegex(
                    stderr,
                    rf"{SHARED_SKILL_PATH.as_posix()}:\d+",
                )
                self.assertIn("marker", stderr.lower())

    def test_build_preserves_unrelated_html_comments(self) -> None:
        """Keep ordinary HTML comments that are not platform marker syntax."""
        with self._temporary_repository() as root:
            source = root / SHARED_SKILL_PATH
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
                    self._temporary_repository() as root,
                ):
                    source = root / SHARED_SKILL_PATH
                    source.write_text(
                        rendered_validation_source(platform, problem),
                        encoding="utf-8",
                        newline="",
                    )
                    before = self._snapshot(self._generated_paths(root))

                    stderr = self._assert_validation_error(
                        root,
                        (SHARED_SKILL_PATH.as_posix(),),
                        before,
                    )

                    self.assertIn(platform, stderr.lower())

    def test_build_renders_agent_metadata_and_markdown_body(self) -> None:
        """Render ordered platform metadata while preserving the Markdown body."""
        with self._temporary_repository() as root:
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
        with self._temporary_repository() as root:
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

    def test_build_publishes_read_only_codex_reviewers_and_writable_refactorers(
        self,
    ) -> None:
        """Publish reviewer sandboxes without restricting writable refactorers."""
        with self._temporary_repository() as root:
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

            for name in REFACTORER_NAMES:
                with self.subTest(name=name):
                    refactorer = tomllib.loads(
                        (
                            root / f"plugins/codex/install/agents/{name}.toml"
                        ).read_text(encoding="utf-8")
                    )
                    self.assertNotIn("sandbox_mode", refactorer)

    def test_build_emits_claude_read_only_tool_policy_for_writing_reviewer(
        self,
    ) -> None:
        """Expose only read operations and explicitly reject file-changing tools."""
        with self._temporary_repository() as root:
            result = self._run(root)
            self.assertEqual(0, result.returncode, result)

            reviewer = (
                root / "plugins/claude/agents/writing-principles-reviewer.md"
            ).read_text(encoding="utf-8")
            self.assertIn("tools: Read, Grep, Glob\n", reviewer)
            self.assertIn(
                "disallowedTools: Bash, Edit, Write, NotebookEdit\n",
                reviewer,
            )

            refactorer = (
                root / "plugins/claude/agents/review-patch-refactorer.md"
            ).read_text(encoding="utf-8")
            self.assertNotIn("tools:", refactorer)
            self.assertNotIn("disallowedTools:", refactorer)

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
            "wrong Claude tools type": lambda text: text.replace(
                'effort = "medium"\n',
                'effort = "medium"\ntools = "Read"\n',
                1,
            ),
            "wrong Claude tool element type": lambda text: text.replace(
                'effort = "medium"\n',
                'effort = "medium"\ntools = ["Read", 1]\n',
                1,
            ),
            "wrong Claude disallowed tools type": lambda text: text.replace(
                'effort = "medium"\n',
                'effort = "medium"\ndisallowed_tools = "Write"\n',
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
            with self.subTest(label=label), self._temporary_repository() as root:
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
            with self.subTest(label=label), self._temporary_repository() as root:
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
            source = root / SHARED_SKILL_PATH
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
            with self.subTest(label=label), self._temporary_repository() as root:
                mutate(root)
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(root, ("shared/",), before)

    def test_build_does_not_recursively_expand_term_values(self) -> None:
        """Leave placeholder-shaped text introduced by a term value untouched."""
        with self._temporary_repository() as root:
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

    def test_build_requires_fixed_sources_and_rejects_unknown_shared_markdown(self) -> None:
        """Require every canonical input and reject unknown managed Markdown."""
        required_sources = (
            "shared/VERSION",
            "shared/terms.toml",
            SHARED_SKILL_PATH.as_posix(),
            *(path.as_posix() for path in SHARED_SKILL_REFERENCE_PATHS.values()),
            *(f"shared/agents/{name}.md" for name in AGENT_NAMES),
        )
        for missing in required_sources:
            with self.subTest(missing=missing), self._temporary_repository() as root:
                (root / missing).unlink()
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(root, (missing,), before)

        with self._temporary_repository() as root:
            self._write(root, "shared/agents/unknown-agent.md", self._agent_source("unknown-agent"))
            before = self._snapshot(self._generated_paths(root))
            self._assert_validation_error(
                root,
                ("shared/agents/unknown-agent.md",),
                before,
            )

        unknown_skill_paths = (
            SHARED_SKILL_PATH.parent / "notes.md",
            SHARED_SKILL_PATH.parent / "references" / "unknown-reference.md",
        )
        for unknown in unknown_skill_paths:
            with self.subTest(unknown=unknown), self._temporary_repository() as root:
                self._write(root, unknown.as_posix(), "# Unknown reference\n")
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(
                    root,
                    (unknown.as_posix(),),
                    before,
                )

    def test_build_rejects_invalid_skill_references_atomically(self) -> None:
        """Reject invalid or platform-empty references without partial updates."""
        mutations = {
            "invalid marker": (
                lambda text: text + "<!-- claude-only:start -->\nunclosed\n",
                "marker",
            ),
            "undefined placeholder": (
                lambda text: text.replace(
                    "{{parent_name}} reference",
                    "{{missing_term}} reference",
                    1,
                ),
                "undefined placeholder",
            ),
            "platform-empty body": (
                lambda text: (
                    "<!-- codex-only:start -->\n"
                    "# Codex only\n"
                    "<!-- codex-only:end -->\n"
                ),
                "claude",
            ),
        }
        reference_path = SHARED_SKILL_REFERENCE_PATHS[
            "implementation-branches.md"
        ]

        for label, (mutate, expected_message) in mutations.items():
            with self.subTest(label=label), self._temporary_repository() as root:
                source = root / reference_path
                source.write_text(
                    mutate(source.read_text(encoding="utf-8")),
                    encoding="utf-8",
                    newline="",
                )
                before = self._snapshot(self._generated_paths(root))

                stderr = self._assert_validation_error(
                    root,
                    (reference_path.as_posix(),),
                    before,
                )

                self.assertIn(expected_message, stderr.lower())

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
            with self.subTest(version=version), self._temporary_repository() as root:
                (root / "shared/VERSION").write_text(
                    f"{version}\n", encoding="utf-8", newline=""
                )
                before = self._snapshot(self._generated_paths(root))
                self._assert_validation_error(root, ("shared/VERSION",), before)

    def test_build_accepts_zero_and_multi_digit_version_components(self) -> None:
        """Accept zero and nonzero multi-digit components allowed by the version regex."""
        for version in ("0.0.0", "10.20.30"):
            with self.subTest(version=version), self._temporary_repository() as root:
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
                    self._temporary_repository() as root,
                ):
                    apply_manifest_problem(root / manifest, problem)
                    before = self._snapshot(self._generated_paths(root))
                    self._assert_validation_error(root, (manifest,), before)

        with self._temporary_repository() as root:
            apply_manifest_problem(root / manifests[0], "invalid JSON")
            apply_manifest_problem(root / manifests[1], "top-level non-object")
            before = self._snapshot(self._generated_paths(root))

            self._assert_validation_error(root, manifests, before)

    def test_build_places_generated_warnings_only_on_markdown_and_agent_toml(self) -> None:
        """Place exact warnings at generated frontmatter boundaries and nowhere else."""
        with self._temporary_repository() as root:
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
        with self._temporary_repository() as root:
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
        with self._temporary_repository() as root:
            build = self._run(root)
            self.assertEqual(0, build.returncode, build)

            stale_skill = root / "plugins/claude/skills/delegate-implementation/SKILL.md"
            stale_reference = (
                root
                / GENERATED_SKILL_REFERENCE_PATHS["claude"][
                    "implementation-branches.md"
                ]
            )
            missing_reference = (
                root
                / GENERATED_SKILL_REFERENCE_PATHS["codex"]["expert-selection.md"]
            )
            missing_agent = root / "plugins/codex/install/agents/implementer.toml"
            stale_manifest = root / "plugins/codex/.codex-plugin/plugin.json"
            stale_skill.write_text("stale\n", encoding="utf-8", newline="")
            stale_reference.write_text("stale\n", encoding="utf-8", newline="")
            missing_reference.unlink()
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
                (
                    "plugins/claude/skills/delegate-implementation/references/"
                    "implementation-branches.md"
                ),
                (
                    "plugins/codex/skills/delegate-implementation/references/"
                    "expert-selection.md"
                ),
                "plugins/codex/install/agents/implementer.toml",
                "plugins/codex/.codex-plugin/plugin.json",
            ):
                self.assertIn(relative_path, result.stderr)
            self.assertEqual(before, self._snapshot(paths))

    def test_check_reports_input_errors_without_writing(self) -> None:
        """Return validation exit one on --check and preserve every stale output."""
        with self._temporary_repository() as root:
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
            with self.subTest(arguments=arguments), self._temporary_repository() as root:
                paths = self._generated_paths(root)
                before = self._snapshot(paths)

                result = self._run(root, *arguments)

                self.assertEqual(2, result.returncode, result)
                self.assertEqual("", result.stdout)
                self.assertIn("usage:", result.stderr.lower())
                self.assertEqual(before, self._snapshot(paths))

    def test_independent_input_errors_are_aggregated_without_partial_updates(self) -> None:
        """Report independent source errors together before changing any output."""
        with self._temporary_repository() as root:
            skill = root / SHARED_SKILL_PATH
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
                    SHARED_SKILL_PATH.as_posix(),
                    "shared/agents/implementer.md",
                ),
                before,
            )

    def test_build_updates_only_files_with_changed_content(self) -> None:
        """Avoid rewriting equal files and repair only one deliberately stale output."""
        with self._temporary_repository() as root:
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
        with self._temporary_repository() as first_root, self._temporary_repository() as second_root:
            roots = (first_root, second_root)
            snapshots = []
            for root in roots:
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
        with self._temporary_repository() as root:
            outside_paths = [
                root / "README.md",
                root / "docs/plan.md",
                root / "plugins/codex/install/install-agents.sh",
                root / "plugins/codex/skills/delegate-implementation/agents/openai.yaml",
                (
                    root
                    / "plugins/codex/skills/delegate-implementation/references/local.md"
                ),
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
