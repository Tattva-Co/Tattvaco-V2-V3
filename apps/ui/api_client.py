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
        claim_ids: list | None = None,
        question_ids: list | None = None,
        panel_ids: list | None = None,
        rule_ids: list | None = None,
    ):
        payload: Dict[str, Any] = {"decision": decision, "notes": notes}
        if decision == "approved":
            if scene_ids is not None:
                payload["approved_scene_ids"] = scene_ids
            if entity_ids is not None:
                payload["approved_entity_ids"] = entity_ids
            if claim_ids is not None:
                payload["approved_claim_ids"] = claim_ids
            if question_ids is not None:
                payload["approved_question_ids"] = question_ids
            if panel_ids is not None:
                payload["approved_panel_ids"] = panel_ids
            if rule_ids is not None:
                payload["approved_rule_ids"] = rule_ids
        return self.post(f"/approvals/{approval_id}/decide", payload)

    def list_scenes(self, project_id: str):
        return self.get(f"/projects/{project_id}/scenes")

    def list_entities(self, project_id: str):
        return self.get(f"/projects/{project_id}/entities")

    def list_versions(self, project_id: str):
        return self.get(f"/projects/{project_id}/versions")

    def audit_log(self, project_id: str):
        return self.get(f"/projects/{project_id}/audit-log")

    # -- historical research -------------------------------------------------

    def list_research_questions(self, project_id: str, status: str | None = None):
        endpoint = f"/projects/{project_id}/research/questions"
        if status:
            endpoint += f"?status={status}"
        return self.get(endpoint)

    def create_research_question(self, project_id: str, text: str, category: str = "general"):
        return self.post(
            f"/projects/{project_id}/research/questions",
            {"text": text, "category": category},
        )

    def list_research_sources(self, project_id: str):
        return self.get(f"/projects/{project_id}/research/sources")

    def create_research_source(
        self,
        project_id: str,
        title: str,
        tier: str = "tier_2_scholarly",
        author: str | None = None,
        locator: str | None = None,
    ):
        return self.post(
            f"/projects/{project_id}/research/sources",
            {"title": title, "tier": tier, "author": author, "locator": locator},
        )

    def list_research_claims(self, project_id: str, claim_class: str | None = None):
        endpoint = f"/projects/{project_id}/research/claims"
        if claim_class:
            endpoint += f"?claim_class={claim_class}"
        return self.get(endpoint)

    def list_research_conflicts(self, project_id: str):
        return self.get(f"/projects/{project_id}/research/conflicts")

    def run_historical_research(
        self, project_id: str, topic: str, seed_text: str | None = None, sync: bool = True
    ):
        return self.post(
            f"/projects/{project_id}/workflows/historical-research",
            {"topic": topic, "seed_text": seed_text, "sync_execution": sync},
        )

    # -- storyboard intelligence ----------------------------------------------

    def list_storyboard_panels(self, project_id: str):
        return self.get(f"/projects/{project_id}/storyboard/panels")

    def run_storyboard_intelligence(
        self, project_id: str, brief: str | None = None, sync: bool = True
    ):
        return self.post(
            f"/projects/{project_id}/workflows/storyboard-intelligence",
            {"brief": brief, "sync_execution": sync},
        )

    # -- film bible & visual world --------------------------------------------

    def list_film_bible_rules(self, project_id: str, category: str | None = None):
        endpoint = f"/projects/{project_id}/film-bible/rules"
        if category:
            endpoint += f"?category={category}"
        return self.get(endpoint)

    def create_film_bible_rule(
        self,
        project_id: str,
        category: str,
        title: str,
        rule_text: str,
        negative_prompt_guidance: str | None = None,
        strictness: str = "guideline",
    ):
        return self.post(
            f"/projects/{project_id}/film-bible/rules",
            {
                "category": category,
                "title": title,
                "rule_text": rule_text,
                "negative_prompt_guidance": negative_prompt_guidance,
                "strictness": strictness,
            },
        )

    def run_film_bible_synthesis(
        self, project_id: str, user_notes: str | None = None, sync: bool = True
    ):
        return self.post(
            f"/projects/{project_id}/workflows/film-bible-synthesis",
            {"user_notes": user_notes, "sync_execution": sync},
        )
