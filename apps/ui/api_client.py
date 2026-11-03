"""Thin HTTP client for the Tattva API. The UI never talks to the database directly."""

from __future__ import annotations

from typing import Any, Dict

import requests


class ApiError(Exception):
    """An API call failed; ``message`` is safe to show to the user."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class TattvaApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0, actor_id: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"X-Actor-ID": actor_id} if actor_id else {}

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        try:
            resp = requests.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ApiError(f"Cannot reach the Tattva API at {self.base_url}: {exc}") from exc

        if resp.ok:
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise ApiError(f"{detail} (HTTP {resp.status_code})", resp.status_code)

    def get(self, endpoint: str) -> Any:
        return self._request("GET", endpoint)

    def post(self, endpoint: str, data: Dict | None = None, files: Dict | None = None) -> Any:
        if files is not None:
            return self._request("POST", endpoint, files=files)
        return self._request("POST", endpoint, json=data)

    # -- endpoints -----------------------------------------------------------

    def list_projects(self):
        return self.get("/projects")

    def get_project(self, project_id: str):
        return self.get(f"/projects/{project_id}")

    def create_project(self, title: str, logline: str, genre: str):
        return self.post("/projects", {"title": title, "logline": logline, "genre": genre})

    def list_assets(self, project_id: str):
        return self.get(f"/projects/{project_id}/assets")

    def upload_asset(self, project_id: str, filename: str, content: bytes, mime_type: str):
        return self.post(
            f"/projects/{project_id}/assets/upload", files={"file": (filename, content, mime_type)}
        )

    def run_script_intelligence(self, project_id: str, asset_id: str, sync: bool = True):
        return self.post(
            f"/projects/{project_id}/workflows/script-intelligence",
            {"script_asset_id": asset_id, "sync_execution": sync},
        )

    def get_candidates(self, project_id: str):
        return self.get(f"/projects/{project_id}/candidates")

    def decide_approval(
        self,
        approval_id: str,
        decision: str,
        notes: str = "",
        scene_ids: list | None = None,
        entity_ids: list | None = None,
    ):
        payload: Dict[str, Any] = {"decision": decision, "notes": notes}
        if decision == "approved":
            payload["approved_scene_ids"] = scene_ids or []
            payload["approved_entity_ids"] = entity_ids or []
        return self.post(f"/approvals/{approval_id}/decide", payload)

    def list_scenes(self, project_id: str):
        return self.get(f"/projects/{project_id}/scenes")

    def list_entities(self, project_id: str):
        return self.get(f"/projects/{project_id}/entities")

    def list_versions(self, project_id: str):
        return self.get(f"/projects/{project_id}/versions")

    def audit_log(self, project_id: str):
        return self.get(f"/projects/{project_id}/audit-log")
