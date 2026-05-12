from __future__ import annotations

from dataclasses import dataclass

from .gitlab import GitLabBranch, GitLabClient, GitLabEpic, GitLabIssue, GitLabPipeline
from .manifest import ChildTask, ReleaseScope, StageIssue


@dataclass
class StageIssueState:
    expected: StageIssue
    issue: GitLabIssue | None
    children: list[tuple[ChildTask, GitLabIssue | None]]


@dataclass
class RepoState:
    key: str
    name: str
    project: str
    url: str
    branch_name: str | None
    branch: GitLabBranch | None
    latest_pipeline: GitLabPipeline | None


@dataclass
class ReleaseLiveState:
    scope: ReleaseScope
    epic: GitLabEpic | None
    stages: list[StageIssueState]
    repos: list[RepoState]


def load_release_live_state(client: GitLabClient, scope: ReleaseScope) -> ReleaseLiveState:
    epic = client.find_epic(scope.group, scope.epic_title)

    stages: list[StageIssueState] = []
    for stage in scope.stage_issues:
        issue = client.find_issue(stage.project, stage.title)
        children = [
            (child, client.find_issue(child.project, child.title))
            for child in stage.children
        ]
        stages.append(StageIssueState(expected=stage, issue=issue, children=children))

    repos: list[RepoState] = []
    for repo in scope.repos:
        if not repo.included:
            continue
        branch = None
        pipeline = None
        if repo.release_branch:
            branch = client.get_branch(repo.project, repo.release_branch)
            if branch is not None:
                pipeline = client.get_latest_pipeline(repo.project, repo.release_branch)
        repos.append(
            RepoState(
                key=repo.key,
                name=repo.name,
                project=repo.project,
                url=repo.url,
                branch_name=repo.release_branch,
                branch=branch,
                latest_pipeline=pipeline,
            )
        )

    return ReleaseLiveState(scope=scope, epic=epic, stages=stages, repos=repos)
