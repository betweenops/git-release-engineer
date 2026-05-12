from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .gitlab import GitLabClient
from .live_state import ReleaseLiveState, load_release_live_state
from .manifest import ManifestError, normalize_release_scope
from .readiness import build_live_report, build_manifest_only_report


def load_local_env() -> None:
    for candidate in (Path(".env"), Path(".env.local")):
        if candidate.is_file():
            load_env_file(candidate)


def load_env_file(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ManifestError(f"Unable to read env file {path}: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ManifestError(
                f"Invalid env entry in {path} line {line_number}: expected KEY=VALUE"
            )
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ManifestError(
                f"Invalid env entry in {path} line {line_number}: empty variable name"
            )
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def default_manifest_path() -> Path | None:
    manifest = os.environ.get("RELEASE_MANIFEST_PATH", "").strip()
    if manifest:
        return Path(manifest)
    root = os.environ.get("RELEASE_DEFINITION_ROOT", "").strip()
    if root:
        return Path(root) / "release.yaml"
    return None


def default_vars_file_path() -> Path | None:
    vars_file = os.environ.get("RELEASE_VARS_FILE", "").strip()
    if vars_file:
        return Path(vars_file)
    root = os.environ.get("RELEASE_DEFINITION_ROOT", "").strip()
    if root:
        return Path(root) / "release.vars.env"
    return None


def resolve_manifest_path(path: Path | None) -> Path:
    if path is not None:
        return path
    env_path = default_manifest_path()
    if env_path is not None:
        return env_path
    raise ManifestError(
        "Manifest path not provided. Set RELEASE_MANIFEST_PATH or RELEASE_DEFINITION_ROOT, "
        "or pass the manifest path explicitly."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitlab-ai-release-engineer",
        description="Inspect manifest-driven release definitions and generate deterministic reports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_manifest = subparsers.add_parser(
        "inspect-manifest",
        help="Load and normalize a release manifest.",
    )
    inspect_manifest.add_argument("manifest", type=Path, nargs="?")
    inspect_manifest.add_argument("--vars-file", type=Path, default=default_vars_file_path())

    report = subparsers.add_parser(
        "report",
        help="Generate a manifest-only deterministic readiness report.",
    )
    report.add_argument("manifest", type=Path, nargs="?")
    report.add_argument("--vars-file", type=Path, default=default_vars_file_path())

    report_live = subparsers.add_parser(
        "report-live",
        help="Generate a live readiness report from GitLab and the release manifest.",
    )
    report_live.add_argument("manifest", type=Path, nargs="?")
    report_live.add_argument("--vars-file", type=Path, default=default_vars_file_path())
    report_live.add_argument(
        "--gitlab-url",
        default=os.environ.get("GITLAB_URL", ""),
    )
    report_live.add_argument(
        "--token-env",
        default="GITLAB_TOKEN",
        help="Environment variable containing the GitLab private token.",
    )
    report_live.add_argument(
        "--json",
        action="store_true",
        help="Emit the computed report as JSON.",
    )

    return parser


def command_inspect_manifest(args: argparse.Namespace) -> int:
    scope = normalize_release_scope(resolve_manifest_path(args.manifest), vars_file=args.vars_file)
    payload = {
        "version": scope.version,
        "rc_iteration": scope.rc_iteration,
        "title": scope.title,
        "group": scope.group,
        "epic_project": scope.epic_project,
        "epic_title": scope.epic_title,
        "labels": scope.labels,
        "repos": [
            {
                "key": repo.key,
                "name": repo.name,
                "project": repo.project,
                "release_branch": repo.release_branch,
                "included": repo.included,
            }
            for repo in scope.repos
        ],
        "validation_targets": [
            {"key": target.key, "name": target.name, "mode": target.mode}
            for target in scope.validation_targets
        ],
        "stage_issues": [
            {
                "key": stage.key,
                "title": stage.title,
                "project": stage.project,
                "depends_on": stage.depends_on,
                "checklist_count": len(stage.checklist),
                "child_count": len(stage.children),
            }
            for stage in scope.stage_issues
        ],
        "unresolved_placeholders": scope.unresolved_placeholders,
    }
    print(json.dumps(payload, indent=2))
    return 0


def command_report(args: argparse.Namespace) -> int:
    scope = normalize_release_scope(resolve_manifest_path(args.manifest), vars_file=args.vars_file)
    report = build_manifest_only_report(scope)
    print(render_report(scope.title or scope.version, report))
    return 0


def command_report_live(args: argparse.Namespace) -> int:
    scope = normalize_release_scope(resolve_manifest_path(args.manifest), vars_file=args.vars_file)
    token = os.environ.get(args.token_env, "")
    gitlab_url = (args.gitlab_url or "").strip()
    if not gitlab_url:
        raise ManifestError(
            "Set GITLAB_URL or pass --gitlab-url before using report-live."
        )
    if not token:
        raise ManifestError(
            f"Set {args.token_env} before using report-live against private GitLab data."
        )
    client = GitLabClient(gitlab_url, token=token)
    state = load_release_live_state(client, scope)
    report = build_live_report(state)

    if args.json:
        payload = build_live_payload(scope.title or scope.version, state, report)
        print(json.dumps(payload, indent=2))
        return 0

    print(render_live_report(scope.title or scope.version, state, report))
    return 0


def render_report(release_name: str, report) -> str:
    lines = [
        f"Release: {release_name}",
        f"Status: {report.status}",
        f"Score: {report.score}",
        "",
        "Summary:",
        f"- Included repos: {report.summary.included_repo_count}",
        f"- Validation targets: {report.summary.validation_target_count}",
        f"- Stage issues: {report.summary.stage_issue_count}",
        f"- Child tasks: {report.summary.child_task_count}",
        f"- Checklist items: {report.summary.checklist_item_count}",
    ]

    if (
        report.summary.open_stage_issue_count
        or report.summary.open_child_task_count
        or report.summary.missing_stage_issue_count
        or report.summary.missing_child_task_count
        or report.summary.missing_branch_count
        or report.summary.failing_pipeline_count
    ):
        lines.extend(
            [
                f"- Open stage issues: {report.summary.open_stage_issue_count}",
                f"- Open child tasks: {report.summary.open_child_task_count}",
                f"- Missing stage issues: {report.summary.missing_stage_issue_count}",
                f"- Missing child tasks: {report.summary.missing_child_task_count}",
                f"- Missing branches: {report.summary.missing_branch_count}",
                f"- Failing pipelines: {report.summary.failing_pipeline_count}",
            ]
        )

    if report.blockers:
        lines.extend(["", "Blockers:"])
        lines.extend(f"- {item}" for item in report.blockers)

    if report.risks:
        lines.extend(["", "Risks:"])
        lines.extend(f"- {item}" for item in report.risks)

    return "\n".join(lines)


def render_live_report(release_name: str, state: ReleaseLiveState, report) -> str:
    lines = [render_report(release_name, report)]

    lines.extend(
        [
            "",
            "Epic:",
            f"- Found: {'yes' if state.epic is not None else 'no'}",
        ]
    )
    if state.epic is not None:
        lines.append(f"- URL: {state.epic.web_url or 'n/a'}")
        lines.append(f"- State: {state.epic.state or 'unknown'}")

    lines.extend(["", "Stages:"])
    for stage_state in state.stages:
        issue = stage_state.issue
        status = issue.state if issue is not None else "missing"
        lines.append(
            f"- {stage_state.expected.title} [{status}]"
        )
        if issue is not None and issue.web_url:
            lines.append(f"  URL: {issue.web_url}")

        open_children = [
            (child, child_issue)
            for child, child_issue in stage_state.children
            if child_issue is None or child_issue.state != "closed"
        ]
        if not open_children:
            lines.append("  Open work: none")
            continue

        lines.append(f"  Open work: {len(open_children)}")
        for child, child_issue in open_children:
            child_status = child_issue.state if child_issue is not None else "missing"
            assignees = (
                ", ".join(child_issue.assignees)
                if child_issue is not None and child_issue.assignees
                else "unassigned"
            )
            lines.append(f"  - {child.title} [{child_status}] ({assignees})")
            if child_issue is not None and child_issue.web_url:
                lines.append(f"    {child_issue.web_url}")

    lines.extend(["", "Repos:"])
    for repo_state in state.repos:
        branch_status = "missing" if repo_state.branch is None else "present"
        pipeline_status = (
            "missing"
            if repo_state.latest_pipeline is None
            else (repo_state.latest_pipeline.status or "unknown")
        )
        lines.append(
            f"- {repo_state.name}: branch {repo_state.branch_name or 'n/a'} [{branch_status}], pipeline [{pipeline_status}]"
        )
        lines.append(f"  Project: {repo_state.project}")
        lines.append(f"  Repo URL: {repo_state.url}")
        if repo_state.latest_pipeline is not None and repo_state.latest_pipeline.web_url:
            lines.append(f"  Pipeline URL: {repo_state.latest_pipeline.web_url}")

    return "\n".join(lines)


def build_live_payload(release_name: str, state: ReleaseLiveState, report) -> dict:
    return {
        "release": release_name,
        "status": report.status,
        "score": report.score,
        "summary": asdict(report.summary),
        "blockers": report.blockers,
        "risks": report.risks,
        "epic": (
            {
                "found": True,
                "title": state.epic.title,
                "state": state.epic.state,
                "web_url": state.epic.web_url,
            }
            if state.epic is not None
            else {"found": False}
        ),
        "stages": [
            {
                "key": stage.expected.key,
                "title": stage.expected.title,
                "project": stage.expected.project,
                "issue": (
                    {
                        "found": True,
                        "state": stage.issue.state,
                        "web_url": stage.issue.web_url,
                        "assignees": stage.issue.assignees,
                        "labels": stage.issue.labels,
                    }
                    if stage.issue is not None
                    else {"found": False}
                ),
                "open_children": [
                    {
                        "key": child.key,
                        "title": child.title,
                        "project": child.project,
                        "issue": (
                            {
                                "found": True,
                                "state": child_issue.state,
                                "web_url": child_issue.web_url,
                                "assignees": child_issue.assignees,
                                "labels": child_issue.labels,
                            }
                            if child_issue is not None
                            else {"found": False}
                        ),
                    }
                    for child, child_issue in stage.children
                    if child_issue is None or child_issue.state != "closed"
                ],
            }
            for stage in state.stages
        ],
        "repos": [
            {
                "key": repo.key,
                "name": repo.name,
                "project": repo.project,
                "url": repo.url,
                "branch_name": repo.branch_name,
                "branch_found": repo.branch is not None,
                "pipeline": (
                    {
                        "found": True,
                        "status": repo.latest_pipeline.status,
                        "web_url": repo.latest_pipeline.web_url,
                    }
                    if repo.latest_pipeline is not None
                    else {"found": False}
                ),
            }
            for repo in state.repos
        ],
    }


def main() -> int:
    parser = build_parser()
    load_local_env()
    args = parser.parse_args()
    try:
        if args.command == "inspect-manifest":
            return command_inspect_manifest(args)
        if args.command == "report":
            return command_report(args)
        if args.command == "report-live":
            return command_report_live(args)
    except ManifestError as exc:
        parser.exit(2, f"error: {exc}\n")
    parser.exit(2, f"error: unsupported command {args.command!r}\n")


if __name__ == "__main__":
    raise SystemExit(main())
