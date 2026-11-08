#!/usr/bin/env python3
"""Dump the FastAPI OpenAPI schema to apps/web/openapi.json.

Run from the repo root (or via `npm run generate-api-types` in apps/web, which calls
this with the right relative path). No server needs to be running: this builds the
FastAPI app in-process and reads app.openapi() directly. The "development" environment
is used only to construct the app object (so the dev-only /auth/dev-login route is
included in the schema); it does not start the app or touch any database.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.main import create_app  # noqa: E402
from packages.core.config import Settings  # noqa: E402


def main() -> None:
    app = create_app(
        settings=Settings(
            environment="development",
            secret_key="schema-dump-only-not-a-real-secret!!",  # noqa: S106 -- placeholder, never used to sign anything
        )
    )
    spec = app.openapi()
    out_path = Path(__file__).resolve().parent.parent / "openapi.json"
    out_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(spec['paths'])} paths, {len(spec.get('components', {}).get('schemas', {}))} schemas)")


if __name__ == "__main__":
    main()
