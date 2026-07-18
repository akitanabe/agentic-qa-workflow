"""Test fixtures shared by the CLI and repository contract suites."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, Iterator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUILDER_SOURCE = REPOSITORY_ROOT / "scripts" / "build_plugin_assets.py"
AGENT_NAMES = (
    "implementer",
    "senior-implementer",
    "expert-implementer",
    "expert-selection-reviewer",
    "responsibility-boundary-reviewer",
    "test-quality-reviewer",
    "writing-principles-reviewer",
    "security-side-effect-reviewer",
    "review-patch-refactorer",
)
REVIEWER_NAMES = (
    "expert-selection-reviewer",
    "responsibility-boundary-reviewer",
    "test-quality-reviewer",
    "writing-principles-reviewer",
    "security-side-effect-reviewer",
)
REFACTORER_NAMES = (
    "review-patch-refactorer",
)
GENERATED_MARKDOWN_WARNING = "<!-- Generated from shared/. Do not edit directly. -->"
GENERATED_TOML_WARNING = "# Generated from shared/. Do not edit directly."
PLATFORMS = ("claude", "codex")
DELEGATE_SKILL = "delegate-implementation"
SHARED_SKILL_ROOT = Path("shared/skill")
# Mirror the generator's skill-name -> reference-name mapping so fixtures and
# path derivation stay data-driven per skill instead of hardcoding one skill.
SKILL_REFERENCE_NAMES = {
    DELEGATE_SKILL: (
        "implementation-branches.md",
        "expert-selection.md",
        "qa-and-integration.md",
        "qa-report.md",
        "branch-plan-intake.md",
    ),
    "plan-implementation-branches": (
        "branch-plan-schema.md",
        "branch-splitting.md",
        "plan-review.md",
    ),
}


def shared_skill_path(skill: str) -> Path:
    return SHARED_SKILL_ROOT / skill / "SKILL.md"


def shared_skill_reference_path(skill: str, name: str) -> Path:
    return SHARED_SKILL_ROOT / skill / "references" / name


def generated_skill_path(platform: str, skill: str) -> Path:
    return Path(f"plugins/{platform}/skills/{skill}/SKILL.md")


def generated_skill_reference_path(platform: str, skill: str, name: str) -> Path:
    return Path(f"plugins/{platform}/skills/{skill}/references/{name}")


# Single-skill aliases for the sole distributed skill keep the real-repository
# contract assertions concise; both derive from the per-skill builders above.
SHARED_SKILL_PATH = shared_skill_path(DELEGATE_SKILL)
SHARED_SKILL_REFERENCE_PATHS = {
    name: shared_skill_reference_path(DELEGATE_SKILL, name)
    for name in SKILL_REFERENCE_NAMES[DELEGATE_SKILL]
}
GENERATED_SKILL_PATHS = {
    platform: generated_skill_path(platform, DELEGATE_SKILL)
    for platform in PLATFORMS
}
GENERATED_SKILL_REFERENCE_PATHS = {
    platform: {
        name: generated_skill_reference_path(platform, DELEGATE_SKILL, name)
        for name in SKILL_REFERENCE_NAMES[DELEGATE_SKILL]
    }
    for platform in PLATFORMS
}
CODEX_PROFILE_PATH = Path("plugins/codex/install/agents")
CLAUDE_PROFILE_PATH = Path("plugins/claude/agents")


@dataclass(frozen=True)
class ModelProfile:
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class RepositorySkillTexts:
    source: str
    claude: str
    codex: str
    source_main: str
    claude_main: str
    codex_main: str
    source_references: dict[str, str]
    claude_references: dict[str, str]
    codex_references: dict[str, str]

    def all_texts(self) -> tuple[str, str, str]:
        return (self.source, self.claude, self.codex)


CODEX_MODEL_PROFILES = {
    "implementer": ModelProfile("gpt-5.6-luna", "xhigh"),
    "senior-implementer": ModelProfile("gpt-5.6-sol", "medium"),
    "expert-implementer": ModelProfile("gpt-5.6-sol", "xhigh"),
    "expert-selection-reviewer": ModelProfile("gpt-5.6-sol", "medium"),
    "responsibility-boundary-reviewer": ModelProfile("gpt-5.6-sol", "medium"),
    "test-quality-reviewer": ModelProfile("gpt-5.6-sol", "medium"),
    "writing-principles-reviewer": ModelProfile("gpt-5.6-luna", "xhigh"),
    "security-side-effect-reviewer": ModelProfile("gpt-5.6-sol", "high"),
    "review-patch-refactorer": ModelProfile("gpt-5.6-luna", "high"),
}
CLAUDE_MODEL_PROFILES = {
    "implementer": ModelProfile("sonnet", "high"),
    "senior-implementer": ModelProfile("opus", "high"),
    "expert-implementer": ModelProfile("fable", "xhigh"),
    "expert-selection-reviewer": ModelProfile("opus", "high"),
    "responsibility-boundary-reviewer": ModelProfile("opus", "high"),
    "test-quality-reviewer": ModelProfile("opus", "high"),
    "writing-principles-reviewer": ModelProfile("sonnet", "high"),
    "security-side-effect-reviewer": ModelProfile("fable", "high"),
    "review-patch-refactorer": ModelProfile("sonnet", "medium"),
}


class RepositoryContractSupport:
    def _repository_text(self, relative_path: Path) -> str:
        return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")

    def _repository_skill_texts(self) -> RepositorySkillTexts:
        source_main = self._repository_text(SHARED_SKILL_PATH)
        claude_main = self._repository_text(GENERATED_SKILL_PATHS["claude"])
        codex_main = self._repository_text(GENERATED_SKILL_PATHS["codex"])
        source_references = {
            name: self._repository_text(path)
            for name, path in SHARED_SKILL_REFERENCE_PATHS.items()
        }
        claude_references = {
            name: self._repository_text(path)
            for name, path in GENERATED_SKILL_REFERENCE_PATHS["claude"].items()
        }
        codex_references = {
            name: self._repository_text(path)
            for name, path in GENERATED_SKILL_REFERENCE_PATHS["codex"].items()
        }

        def combine(main: str, references: dict[str, str]) -> str:
            return main + "\n" + "\n".join(
                references[name] for name in SKILL_REFERENCE_NAMES[DELEGATE_SKILL]
            )

        return RepositorySkillTexts(
            source=combine(source_main, source_references),
            claude=combine(claude_main, claude_references),
            codex=combine(codex_main, codex_references),
            source_main=source_main,
            claude_main=claude_main,
            codex_main=codex_main,
            source_references=source_references,
            claude_references=claude_references,
            codex_references=codex_references,
        )

    def _agent_source_metadata(self, name: str) -> dict[str, Any]:
        source = self._repository_text(Path("shared/agents") / f"{name}.md")
        return tomllib.loads(source.split("+++", 2)[1])

    def _codex_agent_artifact_metadata(self, name: str) -> dict[str, Any]:
        return tomllib.loads(
            self._repository_text(CODEX_PROFILE_PATH / f"{name}.toml")
        )

    def _repository_workflow_texts(self) -> dict[Path, str]:
        skills = self._repository_skill_texts()
        return {
            SHARED_SKILL_PATH: skills.source,
            GENERATED_SKILL_PATHS["claude"]: skills.claude,
            GENERATED_SKILL_PATHS["codex"]: skills.codex,
        }


class IsolatedRepositorySupport:
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

    def _agent_source(
        self,
        name: str,
        *,
        sandbox_mode: str | None = None,
        read_only_tools: bool = False,
    ) -> str:
        """Return a hand-written common agent source with platform metadata."""
        sandbox_line = (
            f'sandbox_mode = "{sandbox_mode}"\n' if sandbox_mode is not None else ""
        )
        claude_tool_lines = (
            'tools = ["Read", "Grep", "Glob"]\n'
            'disallowed_tools = ["Bash", "Edit", "Write", "NotebookEdit"]\n'
            if read_only_tools
            else ""
        )
        return (
            "+++\n"
            f'name = "{name}"\n'
            "\n"
            "[claude]\n"
            f'description = "Claude {name}"\n'
            'model = "sonnet"\n'
            'effort = "medium"\n'
            f"{claude_tool_lines}"
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

    def _skill_source(self, skill: str = DELEGATE_SKILL) -> str:
        """Return a common skill source covering frontmatter and body markers."""
        return (
            "<!-- claude-only:start -->\n"
            "---\n"
            f"name: {skill}\n"
            "description: Claude fixture skill\n"
            "---\n"
            "<!-- claude-only:end -->\n"
            "<!-- codex-only:start -->\n"
            "---\n"
            f"name: {skill}\n"
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

    def _skill_reference_source(self, name: str) -> str:
        """Return one generated skill reference fixture."""
        return (
            f"# {name}\n"
            "\n"
            "{{parent_name}} reference uses {{followup_tool}}.\n"
            "\n"
            "<!-- claude-only:start -->\n"
            f"Claude reference only: {name}.\n"
            "<!-- claude-only:end -->\n"
            "<!-- codex-only:start -->\n"
            f"Codex reference only: {name}.\n"
            "<!-- codex-only:end -->\n"
        )

    def _active_skills(
        self, extra_skills: dict[str, tuple[str, ...]] | None
    ) -> dict[str, tuple[str, ...]]:
        """Merge the distributed skill mapping with test-only extra skills."""
        return {**SKILL_REFERENCE_NAMES, **(extra_skills or {})}

    def _make_repository(
        self,
        root: Path,
        extra_skills: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        """Create a complete minimal repository fixture with stale generated files."""
        skills = self._active_skills(extra_skills)
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
        for skill, reference_names in skills.items():
            self._write(
                root,
                shared_skill_path(skill).as_posix(),
                self._skill_source(skill),
            )
            for name in reference_names:
                self._write(
                    root,
                    shared_skill_reference_path(skill, name).as_posix(),
                    self._skill_reference_source(name),
                )
        for name in AGENT_NAMES:
            sandbox_mode = "read-only" if name in REVIEWER_NAMES else None
            self._write(
                root,
                f"shared/agents/{name}.md",
                self._agent_source(
                    name,
                    sandbox_mode=sandbox_mode,
                    read_only_tools=name == "writing-principles-reviewer",
                ),
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

        for platform in PLATFORMS:
            for skill, reference_names in skills.items():
                self._write(
                    root,
                    generated_skill_path(platform, skill).as_posix(),
                    f"stale {platform} skill\n",
                )
                for name in reference_names:
                    self._write(
                        root,
                        generated_skill_reference_path(platform, skill, name).as_posix(),
                        "stale skill reference\n",
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
            "plugins/codex/skills/delegate-implementation/references/local.md",
            "outside local reference\n",
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
        if extra_skills:
            self._extend_skill_mapping(script, extra_skills)

    def _extend_skill_mapping(
        self, script: Path, extra_skills: dict[str, tuple[str, ...]]
    ) -> None:
        """Register extra skills by adding one mapping entry to the copied script."""
        # Editing the copied script mirrors the production intent that a new skill
        # becomes generated by adding a single mapping entry; the anchor asserts the
        # mapping literal has not silently drifted from this data-driven shape.
        anchor = "SKILL_REFERENCE_NAMES = {\n"
        text = script.read_text(encoding="utf-8")
        self.assertIn(anchor, text)
        entries = "".join(
            f"    {skill!r}: ({''.join(f'{name!r}, ' for name in names)}),\n"
            for skill, names in extra_skills.items()
        )
        script.write_text(
            text.replace(anchor, anchor + entries, 1),
            encoding="utf-8",
            newline="\n",
        )

    @contextmanager
    def _temporary_repository(
        self, extra_skills: dict[str, tuple[str, ...]] | None = None
    ) -> Iterator[Path]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_repository(root, extra_skills)
            yield root

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

    def _generated_paths(
        self,
        root: Path,
        extra_skills: dict[str, tuple[str, ...]] | None = None,
    ) -> list[Path]:
        """List every file whose content is owned by the generator."""
        skills = self._active_skills(extra_skills)
        paths = [
            root / "plugins/claude/.claude-plugin/plugin.json",
            root / "plugins/codex/.codex-plugin/plugin.json",
            root / "plugins/codex/install/VERSION",
        ]
        for platform in PLATFORMS:
            for skill, reference_names in skills.items():
                paths.append(root / generated_skill_path(platform, skill))
                paths.extend(
                    root / generated_skill_reference_path(platform, skill, name)
                    for name in reference_names
                )
        for name in AGENT_NAMES:
            paths.extend(
                (
                    root / CLAUDE_PROFILE_PATH / f"{name}.md",
                    root / CODEX_PROFILE_PATH / f"{name}.toml",
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
