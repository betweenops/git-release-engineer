from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"<([A-Z0-9_]+)>")


class ManifestError(RuntimeError):
    """Raised when the manifest cannot be parsed."""


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    return value


class SimpleYamlParser:
    """A minimal YAML parser for the EdgeOps manifest shape."""

    def __init__(self, text: str) -> None:
        self.lines = text.splitlines()

    def parse(self) -> Any:
        if not self.lines:
            return {}
        value, index = self._parse_block(0, 0)
        index = self._skip_empty(index)
        if index != len(self.lines):
            raise ManifestError(f"Unexpected content near line {index + 1}")
        return value

    def _skip_empty(self, index: int) -> int:
        while index < len(self.lines):
            stripped = self.lines[index].strip()
            if stripped == "" or stripped.startswith("#"):
                index += 1
                continue
            break
        return index

    def _indent(self, line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def _split_key_value(self, text: str) -> tuple[str, str | None]:
        if ":" not in text:
            raise ManifestError(f"Expected key/value mapping: {text!r}")
        key, rest = text.split(":", 1)
        return key.strip(), rest.lstrip()

    def _parse_block(self, index: int, indent: int) -> tuple[Any, int]:
        index = self._skip_empty(index)
        if index >= len(self.lines):
            return {}, index
        current = self.lines[index]
        current_indent = self._indent(current)
        if current_indent < indent:
            return {}, index
        stripped = current[current_indent:]
        if stripped.startswith("- "):
            return self._parse_list(index, indent)
        return self._parse_mapping(index, indent)

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while True:
            index = self._skip_empty(index)
            if index >= len(self.lines):
                break
            line = self.lines[index]
            current_indent = self._indent(line)
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ManifestError(f"Unexpected indentation on line {index + 1}")
            stripped = line[indent:]
            if stripped.startswith("- "):
                break
            key, rest = self._split_key_value(stripped)
            index += 1
            if rest == "|":
                value, index = self._parse_block_scalar(index, indent + 2)
            elif rest == "":
                next_index = self._skip_empty(index)
                if next_index < len(self.lines) and self._indent(self.lines[next_index]) > indent:
                    value, index = self._parse_block(next_index, indent + 2)
                else:
                    value = None
                    index = next_index
            else:
                value = parse_scalar(rest)
            result[key] = value
        return result, index

    def _parse_list(self, index: int, indent: int) -> tuple[list[Any], int]:
        items: list[Any] = []
        while True:
            index = self._skip_empty(index)
            if index >= len(self.lines):
                break
            line = self.lines[index]
            current_indent = self._indent(line)
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ManifestError(f"Unexpected indentation on line {index + 1}")
            stripped = line[indent:]
            if not stripped.startswith("- "):
                break
            payload = stripped[2:].strip()
            index += 1
            if payload == "":
                value, index = self._parse_block(index, indent + 2)
                items.append(value)
                continue

            if ":" in payload and not payload.startswith(("'", '"')):
                key, rest = self._split_key_value(payload)
                item: dict[str, Any] = {}
                if rest == "|":
                    value, index = self._parse_block_scalar(index, indent + 2)
                elif rest == "":
                    next_index = self._skip_empty(index)
                    if next_index < len(self.lines) and self._indent(self.lines[next_index]) > indent:
                        value, index = self._parse_block(next_index, indent + 2)
                    else:
                        value = None
                        index = next_index
                else:
                    value = parse_scalar(rest)
                item[key] = value

                next_index = self._skip_empty(index)
                if next_index < len(self.lines):
                    next_indent = self._indent(self.lines[next_index])
                    if next_indent > indent:
                        extra, index = self._parse_mapping(next_index, indent + 2)
                        item.update(extra)
                    else:
                        index = next_index
                items.append(item)
                continue

            items.append(parse_scalar(payload))
        return items, index

    def _parse_block_scalar(self, index: int, indent: int) -> tuple[str, int]:
        lines: list[str] = []
        while index < len(self.lines):
            line = self.lines[index]
            stripped = line.strip()
            if stripped == "":
                lines.append("")
                index += 1
                continue
            current_indent = self._indent(line)
            if current_indent < indent:
                break
            lines.append(line[indent:])
            index += 1
        return "\n".join(lines), index


def load_vars_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ManifestError(f"Unable to read vars file {path}: {exc}") from exc

    values: dict[str, str] = {}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ManifestError(
                f"Invalid vars entry in {path} line {line_number}: expected KEY=VALUE"
            )
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def replace_placeholders(value: str, context: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        return context.get(token, match.group(0))

    return PLACEHOLDER_RE.sub(repl, value)


def render_node(node: Any, context: dict[str, str]) -> Any:
    if isinstance(node, str):
        return replace_placeholders(node, context)
    if isinstance(node, list):
        return [render_node(item, context) for item in node]
    if isinstance(node, dict):
        return {key: render_node(value, context) for key, value in node.items()}
    return node


def normalize_context_key(key: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", key.upper()).strip("_")


def build_context(manifest: dict[str, Any], overrides: dict[str, str] | None = None) -> dict[str, str]:
    release = manifest.get("release", {})
    variables = manifest.get("variables", {})
    context: dict[str, str] = {
        "VERSION": str(release.get("version", "")),
        "RC_NUMBER": str(release.get("rc_iteration", "")),
    }
    context.update(overrides or {})
    for _ in range(5):
        changed = False
        for key, value in variables.items():
            if not isinstance(value, str):
                continue
            rendered = replace_placeholders(value, context)
            context_key = normalize_context_key(key)
            if context.get(context_key) != rendered:
                context[context_key] = rendered
                changed = True
        if not changed:
            break
    return context


def has_unresolved_placeholders(node: Any) -> bool:
    if isinstance(node, str):
        return bool(PLACEHOLDER_RE.search(node))
    if isinstance(node, list):
        return any(has_unresolved_placeholders(item) for item in node)
    if isinstance(node, dict):
        return any(has_unresolved_placeholders(value) for value in node.values())
    return False


@dataclass
class ChildTask:
    key: str
    title: str
    project: str
    type: str
    acceptance_criteria: list[str] = field(default_factory=list)
    applies_to_repos: list[str] = field(default_factory=list)
    applies_to_projects: list[str] = field(default_factory=list)
    conditional: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageIssue:
    key: str
    title: str
    project: str
    type: str
    depends_on: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    children: list[ChildTask] = field(default_factory=list)


@dataclass
class ReleaseRepo:
    key: str
    name: str
    project: str
    url: str
    release_branch: str | None
    included: bool


@dataclass
class ValidationTarget:
    key: str
    name: str
    mode: str | None


@dataclass
class ReleaseScope:
    version: str
    rc_iteration: str
    title: str
    group: str
    epic_project: str
    epic_title: str
    labels: list[str]
    repos: list[ReleaseRepo]
    validation_targets: list[ValidationTarget]
    stage_issues: list[StageIssue]
    unresolved_placeholders: bool


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"Unable to read manifest {path}: {exc}") from exc
    data = SimpleYamlParser(raw).parse()
    if not isinstance(data, dict):
        raise ManifestError("Manifest root must be a mapping")
    return data


def normalize_release_scope(
    manifest_path: Path, vars_file: Path | None = None, overrides: dict[str, str] | None = None
) -> ReleaseScope:
    manifest = load_manifest(manifest_path)
    vars_context = load_vars_file(vars_file)
    context = build_context(manifest, overrides={**vars_context, **(overrides or {})})
    rendered = render_node(manifest, context)
    release = rendered.get("release", {})
    epic = release.get("epic", {})

    repos = [
        ReleaseRepo(
            key=str(repo["key"]),
            name=str(repo["name"]),
            project=str(repo["project"]),
            url=str(repo["url"]),
            release_branch=repo.get("release_branch"),
            included=bool(repo.get("included", True)),
        )
        for repo in rendered.get("repos", [])
        if isinstance(repo, dict)
    ]

    validation_targets = [
        ValidationTarget(
            key=str(target["key"]),
            name=str(target["name"]),
            mode=target.get("mode"),
        )
        for target in rendered.get("validation_targets", [])
        if isinstance(target, dict)
    ]

    stage_issues: list[StageIssue] = []
    for item in rendered.get("work_items", []):
        if not isinstance(item, dict):
            continue
        children = [
            ChildTask(
                key=str(child["key"]),
                title=str(child["title"]),
                project=str(child.get("project", item.get("project", ""))),
                type=str(child["type"]),
                acceptance_criteria=[str(x) for x in child.get("acceptance_criteria", [])],
                applies_to_repos=[str(x) for x in child.get("applies_to_repos", [])],
                applies_to_projects=[str(x) for x in child.get("applies_to_projects", [])],
                conditional=child.get("conditional", {}) or {},
            )
            for child in item.get("children", [])
            if isinstance(child, dict)
        ]
        stage_issues.append(
            StageIssue(
                key=str(item["key"]),
                title=str(item["title"]),
                project=str(item["project"]),
                type=str(item["type"]),
                depends_on=[str(x) for x in item.get("depends_on", [])],
                checklist=[str(x) for x in item.get("checklist", [])],
                children=children,
            )
        )

    return ReleaseScope(
        version=str(release.get("version", "")),
        rc_iteration=str(release.get("rc_iteration", "")),
        title=str(release.get("title", "")),
        group=str(release.get("group", "")),
        epic_project=str(epic.get("project", "")),
        epic_title=str(epic.get("title", "")),
        labels=[str(x) for x in release.get("labels", [])],
        repos=repos,
        validation_targets=validation_targets,
        stage_issues=stage_issues,
        unresolved_placeholders=has_unresolved_placeholders(rendered),
    )
