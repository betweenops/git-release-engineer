from __future__ import annotations

from dataclasses import dataclass

from .live_state import ReleaseLiveState
from .manifest import ReleaseScope


@dataclass
class ScopeSummary:
    included_repo_count: int
    validation_target_count: int
    stage_issue_count: int
    child_task_count: int
    checklist_item_count: int
    open_stage_issue_count: int = 0
    open_child_task_count: int = 0
    missing_stage_issue_count: int = 0
    missing_child_task_count: int = 0
    missing_branch_count: int = 0
    failing_pipeline_count: int = 0


@dataclass
class DeterministicReport:
    status: str
    score: int
    blockers: list[str]
    risks: list[str]
    summary: ScopeSummary


def build_manifest_only_report(scope: ReleaseScope) -> DeterministicReport:
    included_repos = [repo for repo in scope.repos if repo.included]
    child_tasks = [child for stage in scope.stage_issues for child in stage.children]
    checklist_item_count = sum(len(stage.checklist) for stage in scope.stage_issues)

    blockers: list[str] = []
    risks: list[str] = []
    score = 100

    if scope.unresolved_placeholders:
        blockers.append("Manifest still contains unresolved placeholder values.")
        score -= 35

    if len(scope.stage_issues) < 3:
        blockers.append("Release manifest defines fewer than three top-level stage issues.")
        score -= 25

    if not included_repos:
        blockers.append("No included repositories were found in the release scope.")
        score -= 40

    if not scope.validation_targets:
        risks.append("No validation targets are defined for this release.")
        score -= 15

    if not child_tasks:
        risks.append("No child tasks were defined under the top-level release stages.")
        score -= 15

    if checklist_item_count == 0:
        risks.append("Top-level stages do not contain checklist guidance.")
        score -= 10

    missing_dependencies = [
        stage.key
        for stage in scope.stage_issues
        for dependency in stage.depends_on
        if dependency not in {candidate.key for candidate in scope.stage_issues}
    ]
    if missing_dependencies:
        risks.append(
            "Some stage dependencies reference undefined work items: "
            + ", ".join(sorted(set(missing_dependencies)))
        )
        score -= 10

    if any(repo.release_branch in {None, ""} for repo in included_repos):
        risks.append("One or more included repositories do not define a release branch.")
        score -= 10

    score = max(score, 0)
    if blockers:
        status = "red" if score <= 40 else "orange"
    elif risks:
        status = "yellow"
    else:
        status = "green"

    return DeterministicReport(
        status=status,
        score=score,
        blockers=blockers,
        risks=risks,
        summary=ScopeSummary(
            included_repo_count=len(included_repos),
            validation_target_count=len(scope.validation_targets),
            stage_issue_count=len(scope.stage_issues),
            child_task_count=len(child_tasks),
            checklist_item_count=checklist_item_count,
        ),
    )


def build_live_report(state: ReleaseLiveState) -> DeterministicReport:
    scope = state.scope
    manifest_report = build_manifest_only_report(scope)
    blockers = list(manifest_report.blockers)
    risks = list(manifest_report.risks)
    score = manifest_report.score

    if state.epic is None:
        blockers.append(f"Release epic '{scope.epic_title}' was not found in GitLab.")
        score -= 30

    missing_stage_issue_count = 0
    open_stage_issue_count = 0
    missing_child_task_count = 0
    open_child_task_count = 0

    for stage_state in state.stages:
        if stage_state.issue is None:
            missing_stage_issue_count += 1
            blockers.append(f"Stage issue missing: {stage_state.expected.title}")
        elif stage_state.issue.state != "closed":
            open_stage_issue_count += 1
            risks.append(f"Stage still open: {stage_state.expected.title}")

        for child, child_issue in stage_state.children:
            if child_issue is None:
                missing_child_task_count += 1
                blockers.append(f"Child task missing: {child.title}")
                continue
            if child_issue.state != "closed":
                open_child_task_count += 1
                if "release-blocker" in child_issue.labels or "blocker" in child_issue.labels:
                    blockers.append(f"Blocking child task still open: {child.title}")
                elif not child_issue.assignees:
                    risks.append(f"Open child task has no assignee: {child.title}")

    missing_branch_count = 0
    failing_pipeline_count = 0
    for repo_state in state.repos:
        if repo_state.branch_name and repo_state.branch is None:
            missing_branch_count += 1
            blockers.append(
                f"Release branch missing for {repo_state.project}: {repo_state.branch_name}"
            )
            continue
        if repo_state.branch_name and repo_state.latest_pipeline is None:
            risks.append(
                f"No pipeline found for release branch {repo_state.branch_name} in {repo_state.project}"
            )
            continue
        if (
            repo_state.latest_pipeline is not None
            and repo_state.latest_pipeline.status not in {"success", "passed"}
        ):
            failing_pipeline_count += 1
            status = repo_state.latest_pipeline.status or "unknown"
            blockers.append(
                f"Latest release-branch pipeline is not passing for {repo_state.project}: {status}"
            )

    score -= missing_stage_issue_count * 15
    score -= open_stage_issue_count * 5
    score -= missing_child_task_count * 4
    score -= open_child_task_count * 1
    score -= missing_branch_count * 8
    score -= failing_pipeline_count * 10
    score = max(score, 0)

    if blockers:
        status = "red" if score <= 40 else "orange"
    elif risks:
        status = "yellow"
    else:
        status = "green"

    child_task_count = sum(len(stage.children) for stage in scope.stage_issues)
    checklist_item_count = sum(len(stage.checklist) for stage in scope.stage_issues)

    return DeterministicReport(
        status=status,
        score=score,
        blockers=_dedupe(blockers),
        risks=_dedupe(risks),
        summary=ScopeSummary(
            included_repo_count=len([repo for repo in scope.repos if repo.included]),
            validation_target_count=len(scope.validation_targets),
            stage_issue_count=len(scope.stage_issues),
            child_task_count=child_task_count,
            checklist_item_count=checklist_item_count,
            open_stage_issue_count=open_stage_issue_count,
            open_child_task_count=open_child_task_count,
            missing_stage_issue_count=missing_stage_issue_count,
            missing_child_task_count=missing_child_task_count,
            missing_branch_count=missing_branch_count,
            failing_pipeline_count=failing_pipeline_count,
        ),
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
