#!/usr/bin/env python3
"""Generate Claude and Codex plugin assets from the shared sources."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("claude", "codex")
AGENT_NAMES = (
    "implementer",
    "senior-implementer",
    "responsibility-boundary-reviewer",
    "test-quality-reviewer",
    "writing-principles-refactorer",
    "security-side-effect-reviewer",
    "review-patch-refactorer",
)
VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
TERM_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
PLACEHOLDER_PATTERN = re.compile(r"\{\{([^{}\n]+)\}\}")
MARKER_LIKE_PATTERN = re.compile(
    r"<!--\s*[A-Za-z0-9_-]+-only(?:\s*:\s*[A-Za-z0-9_-]*)?\s*-->"
)
MARKERS = {
    "<!-- claude-only:start -->": ("claude", "start"),
    "<!-- claude-only:end -->": ("claude", "end"),
    "<!-- codex-only:start -->": ("codex", "start"),
    "<!-- codex-only:end -->": ("codex", "end"),
}
MARKDOWN_WARNING = "<!-- Generated from shared/. Do not edit directly. -->"
TOML_WARNING = "# Generated from shared/. Do not edit directly."


@dataclass(frozen=True)
class Diagnostic:
    """Describe one user-correctable input validation error."""

    path: Path
    message: str
    line: int | None = None

    def format(self, root: Path) -> str:
        """Format a stable repository-relative diagnostic for stderr."""
        try:
            display_path = self.path.relative_to(root).as_posix()
        except ValueError:
            display_path = self.path.as_posix()
        location = f"{display_path}:{self.line}" if self.line is not None else display_path
        return f"{location}: {self.message}"


@dataclass(frozen=True)
class AgentSource:
    """Hold validated agent metadata and its common Markdown body."""

    path: Path
    name: str
    claude: dict[str, Any]
    codex: dict[str, Any]
    body: str
    body_line: int


def parse_arguments(argv: list[str]) -> argparse.Namespace:
    """Parse the documented generator command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report generated files that are missing or out of date",
    )
    return parser.parse_args(argv)


def read_source(path: Path, errors: list[Diagnostic]) -> str | None:
    """Read one required UTF-8 source and record a concise failure."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(Diagnostic(path, "required file is missing"))
    except UnicodeDecodeError as error:
        errors.append(Diagnostic(path, f"file is not valid UTF-8: {error}"))
    except OSError as error:
        errors.append(Diagnostic(path, f"cannot read file: {error}"))
    return None


def load_version(root: Path, errors: list[Diagnostic]) -> str | None:
    """Load the single shared three-component bundle version."""
    path = root / "shared/VERSION"
    content = read_source(path, errors)
    if content is None:
        return None
    lines = content.splitlines()
    if len(lines) != 1 or VERSION_PATTERN.fullmatch(lines[0]) is None:
        errors.append(Diagnostic(path, "expected a single X.Y.Z version without leading zeroes", 1))
        return None
    return lines[0]


def toml_error_line(error: tomllib.TOMLDecodeError) -> int | None:
    """Extract a TOML parser line number across supported Python versions."""
    line = getattr(error, "lineno", None)
    if isinstance(line, int):
        return line
    match = re.search(r"at line (\d+)", str(error))
    return int(match.group(1)) if match else None


def load_terms(root: Path, errors: list[Diagnostic]) -> dict[str, dict[str, str]]:
    """Load and validate the non-recursive platform term table."""
    path = root / "shared/terms.toml"
    content = read_source(path, errors)
    if content is None:
        return {}
    try:
        document = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        errors.append(Diagnostic(path, f"invalid TOML: {error}", toml_error_line(error)))
        return {}
    if set(document) != {"terms"} or not isinstance(document.get("terms"), dict):
        errors.append(Diagnostic(path, "expected only [terms.<name>] tables"))
        return {}

    validated: dict[str, dict[str, str]] = {}
    for name, values in document["terms"].items():
        if TERM_NAME_PATTERN.fullmatch(name) is None:
            errors.append(Diagnostic(path, f"invalid term name: {name}"))
            continue
        if not isinstance(values, dict):
            errors.append(Diagnostic(path, f"term {name} must be a table"))
            continue
        unknown = sorted(set(values) - set(PLATFORMS))
        missing = sorted(set(PLATFORMS) - set(values))
        for key in unknown:
            errors.append(Diagnostic(path, f"term {name} has unknown key: {key}"))
        for platform in missing:
            errors.append(Diagnostic(path, f"term {name} is missing {platform}"))
        term_values: dict[str, str] = {}
        for platform in PLATFORMS:
            value = values.get(platform)
            if not isinstance(value, str):
                if platform in values:
                    errors.append(Diagnostic(path, f"term {name}.{platform} must be a string"))
                continue
            if not value or "\n" in value or "\r" in value:
                errors.append(
                    Diagnostic(path, f"term {name}.{platform} must be a non-empty single line")
                )
                continue
            term_values[platform] = value
        if not unknown and not missing and len(term_values) == len(PLATFORMS):
            validated[name] = term_values
    return validated


def load_manifest(
    path: Path,
    errors: list[Diagnostic],
) -> tuple[dict[str, Any], str] | None:
    """Load one version synchronization target as a JSON object."""
    content = read_source(path, errors)
    if content is None:
        return None
    try:
        document = json.loads(content)
    except json.JSONDecodeError as error:
        errors.append(Diagnostic(path, f"invalid JSON: {error.msg}", error.lineno))
        return None
    if not isinstance(document, dict):
        errors.append(Diagnostic(path, "top-level JSON value must be an object"))
        return None
    if "version" not in document:
        errors.append(Diagnostic(path, "version key is required"))
        return None
    if not isinstance(document["version"], str):
        errors.append(Diagnostic(path, "version must be a string"))
        return None
    return document, content


def validate_string_field(
    path: Path,
    table_name: str,
    table: dict[str, Any],
    key: str,
    errors: list[Diagnostic],
) -> None:
    """Require one non-empty string metadata field."""
    if key not in table:
        errors.append(Diagnostic(path, f"[{table_name}] is missing required key: {key}"))
    elif not isinstance(table[key], str) or not table[key]:
        errors.append(Diagnostic(path, f"[{table_name}].{key} must be a non-empty string"))


def validate_agent_metadata(
    path: Path,
    expected_name: str,
    document: dict[str, Any],
    errors: list[Diagnostic],
) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
    """Validate the closed common, Claude, and Codex metadata schemas."""
    allowed_top = {"name", "claude", "codex"}
    for key in sorted(set(document) - allowed_top):
        errors.append(Diagnostic(path, f"unknown top-level key: {key}"))

    name = document.get("name")
    if not isinstance(name, str) or not name:
        errors.append(Diagnostic(path, "name must be a non-empty string"))
    elif name != expected_name:
        errors.append(Diagnostic(path, f"name must match filename stem: {expected_name}"))

    claude = document.get("claude")
    codex = document.get("codex")
    if not isinstance(claude, dict):
        errors.append(Diagnostic(path, "[claude] table is required"))
        claude = {}
    if not isinstance(codex, dict):
        errors.append(Diagnostic(path, "[codex] table is required"))
        codex = {}

    claude_keys = {"description", "model", "effort"}
    codex_keys = {
        "description",
        "model",
        "model_reasoning_effort",
        "sandbox_mode",
        "nickname_candidates",
    }
    for key in sorted(set(claude) - claude_keys):
        errors.append(Diagnostic(path, f"[claude] has unknown key: {key}"))
    for key in sorted(set(codex) - codex_keys):
        errors.append(Diagnostic(path, f"[codex] has unknown key: {key}"))
    for key in ("description", "model", "effort"):
        validate_string_field(path, "claude", claude, key, errors)
    for key in ("description", "model", "model_reasoning_effort"):
        validate_string_field(path, "codex", codex, key, errors)
    if "sandbox_mode" in codex:
        validate_string_field(path, "codex", codex, "sandbox_mode", errors)

    nicknames = codex.get("nickname_candidates")
    if nicknames is None:
        errors.append(Diagnostic(path, "[codex] is missing required key: nickname_candidates"))
    elif not isinstance(nicknames, list) or any(
        not isinstance(candidate, str) or not candidate for candidate in nicknames
    ):
        errors.append(
            Diagnostic(path, "[codex].nickname_candidates must be a list of non-empty strings")
        )

    if any(error.path == path for error in errors):
        return None
    return name, claude, codex


def parse_agent_source(
    path: Path,
    expected_name: str,
    content: str,
    errors: list[Diagnostic],
) -> AgentSource | None:
    """Parse one TOML-frontmatter agent source and require a Markdown body."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "+++":
        errors.append(Diagnostic(path, "agent source must start with +++", 1))
        return None
    closing_index = next(
        (index for index, line in enumerate(lines[1:], 1) if line.rstrip("\r\n") == "+++"),
        None,
    )
    if closing_index is None:
        errors.append(Diagnostic(path, "agent frontmatter is not closed", 1))
        return None

    frontmatter = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :])
    body_line = closing_index + 2
    if PLACEHOLDER_PATTERN.search(frontmatter):
        errors.append(Diagnostic(path, "placeholders are not allowed in agent frontmatter"))
    if not body.strip():
        errors.append(Diagnostic(path, "agent Markdown body must not be empty", body_line))
    try:
        document = tomllib.loads(frontmatter)
    except tomllib.TOMLDecodeError as error:
        errors.append(Diagnostic(path, f"invalid TOML frontmatter: {error}", toml_error_line(error)))
        return None
    metadata = validate_agent_metadata(path, expected_name, document, errors)
    if metadata is None or not body.strip():
        return None
    name, claude, codex = metadata
    return AgentSource(path, name, claude, codex, body, body_line)


def load_agents(root: Path, errors: list[Diagnostic]) -> list[AgentSource]:
    """Reject shared agent files outside the canonical distribution set."""
    directory = root / "shared/agents"
    if directory.is_dir():
        expected = {f"{name}.md" for name in AGENT_NAMES}
        for path in sorted(directory.glob("*.md")):
            if path.name not in expected:
                errors.append(Diagnostic(path, "unknown shared agent Markdown file"))

    agents: list[AgentSource] = []
    for name in AGENT_NAMES:
        path = directory / f"{name}.md"
        content = read_source(path, errors)
        if content is None:
            continue
        agent = parse_agent_source(path, name, content, errors)
        if agent is not None:
            agents.append(agent)
    return agents


def process_markers(
    path: Path,
    content: str,
    start_line: int,
    errors: list[Diagnostic],
) -> dict[str, str]:
    """Validate platform markers once and render both selected line streams."""
    rendered: dict[str, list[str]] = {platform: [] for platform in PLATFORMS}
    active: tuple[str, int] | None = None
    for offset, line in enumerate(content.splitlines(keepends=True)):
        line_number = start_line + offset
        stripped = line.strip()
        marker = MARKERS.get(stripped)
        if marker is None:
            if MARKER_LIKE_PATTERN.search(line):
                errors.append(
                    Diagnostic(path, "platform marker must be a known marker on its own line", line_number)
                )
            if active is None:
                for platform in PLATFORMS:
                    rendered[platform].append(line)
            else:
                rendered[active[0]].append(line)
            continue

        platform, action = marker
        if action == "start":
            if active is not None:
                errors.append(Diagnostic(path, "platform markers must not be nested", line_number))
            else:
                active = (platform, line_number)
        elif active is None:
            errors.append(Diagnostic(path, "platform end marker has no matching start", line_number))
        elif active[0] != platform:
            errors.append(Diagnostic(path, "platform end marker does not match its start", line_number))
            active = None
        else:
            active = None
    if active is not None:
        errors.append(Diagnostic(path, "platform marker is not closed", active[1]))
    return {platform: "".join(lines) for platform, lines in rendered.items()}


def validate_placeholders(
    path: Path,
    content: str,
    start_line: int,
    terms: dict[str, dict[str, str]],
    used_terms: set[str],
    errors: list[Diagnostic],
) -> None:
    """Validate raw placeholders and record every referenced defined term."""
    for match in PLACEHOLDER_PATTERN.finditer(content):
        name = match.group(1)
        line = start_line + content.count("\n", 0, match.start())
        if TERM_NAME_PATTERN.fullmatch(name) is None:
            errors.append(Diagnostic(path, f"invalid placeholder name: {name}", line))
        elif name not in terms:
            errors.append(Diagnostic(path, f"undefined placeholder: {name}", line))
        else:
            used_terms.add(name)


def replace_terms(content: str, platform: str, terms: dict[str, dict[str, str]]) -> str:
    """Replace placeholders once without recursively scanning inserted values."""
    return PLACEHOLDER_PATTERN.sub(
        lambda match: terms[match.group(1)][platform],
        content,
    )


def normalize_body(body: str) -> str:
    """Remove the frontmatter separator newline and ensure one final newline."""
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return body.rstrip("\r\n") + "\n"


def render_skill(
    path: Path,
    platform: str,
    content: str,
    errors: list[Diagnostic],
) -> str | None:
    """Validate rendered YAML frontmatter/body and insert the generated warning."""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        errors.append(Diagnostic(path, f"{platform} skill must start with YAML frontmatter", 1))
        return None
    closing_index = next(
        (index for index, line in enumerate(lines[1:], 1) if line.rstrip("\r\n") == "---"),
        None,
    )
    if closing_index is None:
        errors.append(Diagnostic(path, f"{platform} skill YAML frontmatter is not closed", 1))
        return None
    body = "".join(lines[closing_index + 1 :])
    if not body.strip():
        errors.append(Diagnostic(path, f"{platform} skill Markdown body must not be empty"))
        return None
    frontmatter = "".join(lines[: closing_index + 1])
    return ensure_text(frontmatter + MARKDOWN_WARNING + "\n" + body)


def yaml_scalar(value: str) -> str:
    """Encode a metadata string as a YAML-compatible JSON scalar."""
    return json.dumps(value, ensure_ascii=False)


def toml_scalar(value: str) -> str:
    """Encode a single-line string as a TOML-compatible JSON scalar."""
    return json.dumps(value, ensure_ascii=False)


def toml_multiline(value: str) -> str:
    """Encode Markdown as a readable TOML multiline basic string."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"""\n{escaped}"""'


def render_claude_agent(agent: AgentSource, body: str) -> str:
    """Render Claude YAML frontmatter followed by the common Markdown body."""
    metadata = agent.claude
    return ensure_text(
        "---\n"
        f"name: {yaml_scalar(agent.name)}\n"
        f"description: {yaml_scalar(metadata['description'])}\n"
        f"model: {metadata['model']}\n"
        f"effort: {metadata['effort']}\n"
        "---\n"
        f"{MARKDOWN_WARNING}\n\n"
        f"{normalize_body(body)}"
    )


def render_codex_agent(agent: AgentSource, body: str) -> str:
    """Render ordered Codex TOML metadata and an escaped Markdown instruction body."""
    metadata = agent.codex
    lines = [
        TOML_WARNING,
        f"name = {toml_scalar(agent.name)}",
        f"description = {toml_scalar(metadata['description'])}",
        f"model = {toml_scalar(metadata['model'])}",
        f"model_reasoning_effort = {toml_scalar(metadata['model_reasoning_effort'])}",
    ]
    if "sandbox_mode" in metadata:
        lines.append(f"sandbox_mode = {toml_scalar(metadata['sandbox_mode'])}")
    nicknames = ", ".join(toml_scalar(candidate) for candidate in metadata["nickname_candidates"])
    lines.append(f"nickname_candidates = [{nicknames}]")
    lines.append(f"developer_instructions = {toml_multiline(normalize_body(body))}")
    return ensure_text("\n".join(lines))


def ensure_text(content: str) -> str:
    """Normalize generated text to LF with exactly one trailing newline."""
    return content.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def render_manifest(document: dict[str, Any], original: str, version: str) -> str:
    """Update only the manifest version while preserving already-matching bytes."""
    if document["version"] == version:
        return original
    updated = dict(document)
    updated["version"] = version
    return json.dumps(updated, ensure_ascii=False, indent=2) + "\n"


def build_outputs(root: Path) -> tuple[dict[Path, str], list[Diagnostic]]:
    """Validate every input and construct the complete generated output map."""
    errors: list[Diagnostic] = []
    version = load_version(root, errors)
    terms = load_terms(root, errors)
    agents = load_agents(root, errors)

    skill_path = root / "shared/skill/delegate-implementation.md"
    skill_source = read_source(skill_path, errors)
    skill_rendered: dict[str, str] = {}
    used_terms: set[str] = set()
    if skill_source is not None:
        validate_placeholders(skill_path, skill_source, 1, terms, used_terms, errors)
        skill_rendered = process_markers(skill_path, skill_source, 1, errors)

    rendered_agent_bodies: dict[str, dict[str, str]] = {}
    for agent in agents:
        validate_placeholders(
            agent.path,
            agent.body,
            agent.body_line,
            terms,
            used_terms,
            errors,
        )
        rendered_agent_bodies[agent.name] = process_markers(
            agent.path,
            agent.body,
            agent.body_line,
            errors,
        )

    terms_path = root / "shared/terms.toml"
    for name in sorted(set(terms) - used_terms):
        errors.append(Diagnostic(terms_path, f"unused term: {name}"))

    manifest_paths = (
        root / "plugins/claude/.claude-plugin/plugin.json",
        root / "plugins/codex/.codex-plugin/plugin.json",
    )
    manifests = {path: load_manifest(path, errors) for path in manifest_paths}

    if errors:
        return {}, errors

    outputs: dict[Path, str] = {}
    for platform in PLATFORMS:
        replaced = replace_terms(skill_rendered[platform], platform, terms)
        rendered = render_skill(skill_path, platform, replaced, errors)
        if rendered is not None:
            outputs[
                root / f"plugins/{platform}/skills/delegate-implementation/SKILL.md"
            ] = rendered

    for agent in agents:
        bodies = rendered_agent_bodies[agent.name]
        for platform in PLATFORMS:
            body = replace_terms(bodies[platform], platform, terms)
            if not body.strip():
                errors.append(
                    Diagnostic(agent.path, f"{platform} agent Markdown body must not be empty")
                )
        if errors:
            continue
        outputs[root / f"plugins/claude/agents/{agent.name}.md"] = render_claude_agent(
            agent, bodies["claude"] and replace_terms(bodies["claude"], "claude", terms)
        )
        outputs[
            root / f"plugins/codex/install/agents/{agent.name}.toml"
        ] = render_codex_agent(
            agent, bodies["codex"] and replace_terms(bodies["codex"], "codex", terms)
        )

    if errors:
        return {}, errors
    assert version is not None
    for path, loaded in manifests.items():
        assert loaded is not None
        document, original = loaded
        outputs[path] = render_manifest(document, original, version)
    outputs[root / "plugins/codex/install/VERSION"] = f"{version}\n"
    return outputs, []


def relative_path(path: Path, root: Path) -> str:
    """Return a stable repository-relative output path."""
    return path.relative_to(root).as_posix()


def check_outputs(root: Path, outputs: dict[Path, str]) -> int:
    """Compare every generated file without changing the filesystem."""
    mismatches: list[Path] = []
    for path, expected in sorted(outputs.items()):
        try:
            actual = path.read_bytes()
        except FileNotFoundError:
            actual = None
        if actual != expected.encode("utf-8"):
            mismatches.append(path)
    if mismatches:
        for path in mismatches:
            print(f"out of date: {relative_path(path, root)}", file=sys.stderr)
        return 1
    print("plugin assets are up to date")
    return 0


def write_outputs(root: Path, outputs: dict[Path, str]) -> int:
    """Write only generated files whose UTF-8 bytes have changed."""
    updated: list[Path] = []
    for path, content in sorted(outputs.items()):
        encoded = content.encode("utf-8")
        try:
            current = path.read_bytes()
        except FileNotFoundError:
            current = None
        if current == encoded:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        updated.append(path)
    if updated:
        for path in updated:
            print(f"updated: {relative_path(path, root)}")
    else:
        print("plugin assets are up to date")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Validate, render, then either compare or write the complete asset set."""
    arguments = parse_arguments(sys.argv[1:] if argv is None else argv)
    outputs, errors = build_outputs(ROOT)
    if errors:
        for error in errors:
            print(error.format(ROOT), file=sys.stderr)
        return 1
    if arguments.check:
        return check_outputs(ROOT, outputs)
    return write_outputs(ROOT, outputs)


if __name__ == "__main__":
    raise SystemExit(main())
