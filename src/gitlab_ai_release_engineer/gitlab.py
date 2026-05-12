from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .manifest import ManifestError


@dataclass
class GitLabEpic:
    id: int
    iid: int | None
    title: str
    state: str | None
    web_url: str | None


@dataclass
class GitLabIssue:
    id: int
    iid: int | None
    title: str
    state: str | None
    labels: list[str]
    assignees: list[str]
    web_url: str | None
    project_id: int | None


@dataclass
class GitLabBranch:
    name: str
    merged: bool | None
    protected: bool | None
    web_url: str | None


@dataclass
class GitLabPipeline:
    id: int
    status: str | None
    ref: str | None
    sha: str | None
    web_url: str | None


class GitLabClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token or ""
        self.project_cache: dict[str, dict[str, Any]] = {}

    def request_json(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
    ) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)

        headers: dict[str, str] = {}
        if self.token:
            headers["PRIVATE-TOKEN"] = self.token

        request = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raw = exc.read().decode("utf-8", errors="replace")
            raise ManifestError(f"GitLab API error {exc.code} for {url}: {raw}") from exc
        except urllib.error.URLError as exc:
            raise ManifestError(f"Unable to reach GitLab API at {url}: {exc}") from exc

        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def get_project(self, project_path: str) -> dict[str, Any]:
        if project_path not in self.project_cache:
            encoded = urllib.parse.quote(project_path, safe="")
            project = self.request_json("GET", f"/api/v4/projects/{encoded}")
            if not isinstance(project, dict):
                raise ManifestError(
                    "Unable to resolve GitLab project: "
                    f"{project_path}. The project may not exist, or the provided token lacks access."
                )
            self.project_cache[project_path] = project
        return self.project_cache[project_path]

    def find_epic(self, group: str, title: str) -> GitLabEpic | None:
        encoded = urllib.parse.quote(group, safe="")
        items = self.request_json(
            "GET",
            f"/api/v4/groups/{encoded}/epics",
            query={"search": title},
        )
        if not isinstance(items, list):
            return None
        for item in items:
            if item.get("title") == title:
                return GitLabEpic(
                    id=item["id"],
                    iid=item.get("iid"),
                    title=item["title"],
                    state=item.get("state"),
                    web_url=item.get("web_url"),
                )
        return None

    def find_issue(self, project_path: str, title: str) -> GitLabIssue | None:
        project = self.get_project(project_path)
        items = self.request_json(
            "GET",
            f"/api/v4/projects/{project['id']}/issues",
            query={"search": title, "scope": "all", "per_page": 100},
        )
        if not isinstance(items, list):
            return None
        for item in items:
            if item.get("title") == title:
                return GitLabIssue(
                    id=item["id"],
                    iid=item.get("iid"),
                    title=item["title"],
                    state=item.get("state"),
                    labels=[str(label) for label in item.get("labels", [])],
                    assignees=[
                        str(assignee.get("username") or assignee.get("name"))
                        for assignee in item.get("assignees", [])
                        if isinstance(assignee, dict)
                    ],
                    web_url=item.get("web_url"),
                    project_id=project["id"],
                )
        return None

    def get_branch(self, project_path: str, branch_name: str) -> GitLabBranch | None:
        project = self.get_project(project_path)
        encoded_branch = urllib.parse.quote(branch_name, safe="")
        branch = self.request_json(
            "GET",
            f"/api/v4/projects/{project['id']}/repository/branches/{encoded_branch}",
        )
        if not isinstance(branch, dict):
            return None
        return GitLabBranch(
            name=branch["name"],
            merged=branch.get("merged"),
            protected=branch.get("protected"),
            web_url=branch.get("web_url"),
        )

    def get_latest_pipeline(self, project_path: str, ref: str) -> GitLabPipeline | None:
        project = self.get_project(project_path)
        items = self.request_json(
            "GET",
            f"/api/v4/projects/{project['id']}/pipelines",
            query={"ref": ref, "per_page": 1},
        )
        if not isinstance(items, list) or not items:
            return None
        pipeline = items[0]
        return GitLabPipeline(
            id=pipeline["id"],
            status=pipeline.get("status"),
            ref=pipeline.get("ref"),
            sha=pipeline.get("sha"),
            web_url=pipeline.get("web_url"),
        )
