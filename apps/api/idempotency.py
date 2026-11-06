"""Idempotency-Key support for POST requests (TFD-OPS-004; plan C6).

A client that may retry a request (a timeout, a dropped connection, a double click)
sends the same ``Idempotency-Key`` header on every attempt. The first attempt runs
normally and its response is stored. A later attempt with the same key:

- and the same request (method, path, query and body) gets the stored response back,
  marked with ``Idempotent-Replayed: true``, and nothing runs a second time;
- with a different request gets 422 ``IdempotencyKeyReused``;
- while the first attempt is still running gets 409 ``IdempotencyKeyInProgress``.

Keys are scoped to the authenticated user, so two users can't collide or read each
other's responses. Responses with status 500 or above are not stored: the key is
released so a retry can run again. Records expire after ``idempotency_ttl_hours``.

This is ASGI middleware rather than a per-route dependency so it sees the raw body
(including multipart uploads) and the final response for every POST in one place. A
request without the header is passed through untouched.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from packages.core.config import Settings, get_settings
from packages.core.logging import get_logger
from packages.persistence.database import SessionLocal
from packages.persistence.models import IdempotencyKeyModel, utc_now

logger = get_logger("api.idempotency")

HEADER = "idempotency-key"
REPLAYED_HEADER = "Idempotent-Replayed"
METHODS = frozenset({"POST"})
MAX_KEY_LENGTH = 255
# Login issues a fresh token each time; replaying an old one would be wrong.
EXEMPT_PATH_PARTS = ("/auth/",)


@dataclass(frozen=True)
class Claim:
    outcome: str  # "new", "replay", "mismatch", "in_progress"
    record_id: str | None = None
    status: int | None = None
    body: bytes | None = None
    content_type: str | None = None


def fingerprint(method: str, path: str, query: bytes, content_type: str, body: bytes) -> str:
    """Hash what makes two requests 'the same'. A multipart boundary is random per
    attempt, so it is normalised out of the body before hashing."""
    if "boundary=" in content_type:
        boundary = content_type.split("boundary=", 1)[1].split(";", 1)[0].strip().strip('"')
        if boundary:
            body = body.replace(boundary.encode(), b"BOUNDARY")
    digest = hashlib.sha256()
    for part in (method.encode(), path.encode(), query, body):
        digest.update(part)
        digest.update(b"\0")
    return digest.hexdigest()


class IdempotencyStore:
    """Database side of the protocol. Each call uses its own short session and commits."""

    def __init__(self, ttl: timedelta):
        self.ttl = ttl

    def claim(self, org_id: str, user_id: str, key: str, method: str, path: str, request_hash: str) -> Claim:
        db = SessionLocal()
        try:
            row = db.query(IdempotencyKeyModel).filter_by(organization_id=org_id, user_id=user_id, key=key).first()
            if row is not None and row.created_at < utc_now() - self.ttl:
                db.delete(row)
                db.commit()
                row = None
            if row is not None:
                if (row.method, row.path, row.request_hash) != (method, path, request_hash):
                    return Claim("mismatch")
                if row.status != "completed":
                    return Claim("in_progress")
                return Claim("replay", row.id, row.response_status, row.response_body, row.response_content_type)
            row = IdempotencyKeyModel(
                organization_id=org_id, user_id=user_id, key=key, method=method, path=path,
                request_hash=request_hash, status="in_progress",
            )
            db.add(row)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()  # another attempt with this key claimed it first
                return Claim("in_progress")
            return Claim("new", row.id)
        finally:
            db.close()

    def complete(self, record_id: str, status: int, body: bytes, content_type: str | None) -> None:
        db = SessionLocal()
        try:
            row = db.get(IdempotencyKeyModel, record_id)
            if row is not None:
                row.status = "completed"
                row.response_status = status
                row.response_body = body
                row.response_content_type = content_type
                row.completed_at = utc_now()
                db.commit()
        finally:
            db.close()

    def release(self, record_id: str) -> None:
        db = SessionLocal()
        try:
            db.query(IdempotencyKeyModel).filter_by(id=record_id).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


async def _send_json(send: Send, status: int, payload: dict[str, Any], extra: list[tuple[bytes, bytes]] | None = None) -> None:
    body = json.dumps(payload).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers + (extra or [])})
    await send({"type": "http.response.body", "body": body})


class IdempotencyMiddleware:
    def __init__(self, app: ASGIApp, actor_resolver: Callable[..., Any]):
        self.app = app
        self.resolve_actor = actor_resolver

    def _settings(self, scope: Scope) -> Settings:
        # Honour app.dependency_overrides[get_settings] the way route dependencies do.
        app = scope.get("app")
        override = getattr(app, "dependency_overrides", {}).get(get_settings) if app else None
        return (override or get_settings)()

    def _actor(self, headers: Headers, settings: Settings):
        db = SessionLocal()
        try:
            return self.resolve_actor(headers.get("authorization"), headers.get("x-actor-id"), db, settings)
        finally:
            db.close()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in METHODS:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        key = headers.get(HEADER)
        path: str = scope["path"]
        if key is None or any(part in path for part in EXEMPT_PATH_PARTS):
            await self.app(scope, receive, send)
            return
        key = key.strip()
        if not key or len(key) > MAX_KEY_LENGTH or not key.isprintable():
            await _send_json(send, 400, {
                "detail": f"Idempotency-Key must be 1 to {MAX_KEY_LENGTH} printable characters.",
                "error": "InvalidIdempotencyKey",
            })
            return

        # Buffer the body so it can be hashed and then handed to the app unchanged.
        chunks: list[bytes] = []
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        body = b"".join(chunks)
        replayed = False

        async def replay_receive() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        settings = self._settings(scope)
        try:
            actor = await run_in_threadpool(self._actor, headers, settings)
        except Exception:
            # Unauthenticated: let the route produce its normal 401. Nothing is stored.
            await self.app(scope, replay_receive, send)
            return

        store = IdempotencyStore(timedelta(hours=settings.idempotency_ttl_hours))
        request_hash = fingerprint(scope["method"], path, scope.get("query_string", b""),
                                   headers.get("content-type", ""), body)
        claim = await run_in_threadpool(store.claim, actor.org_id, actor.user_id, key, scope["method"], path, request_hash)

        if claim.outcome == "mismatch":
            await _send_json(send, 422, {
                "detail": "This Idempotency-Key was already used with a different request.",
                "error": "IdempotencyKeyReused",
            })
            return
        if claim.outcome == "in_progress":
            await _send_json(send, 409, {
                "detail": "A request with this Idempotency-Key is still being processed. Retry shortly.",
                "error": "IdempotencyKeyInProgress",
            })
            return
        if claim.outcome == "replay":
            stored = claim.body or b""
            out = [(b"content-length", str(len(stored)).encode()), (REPLAYED_HEADER.lower().encode(), b"true")]
            if claim.content_type:
                out.append((b"content-type", claim.content_type.encode()))
            await send({"type": "http.response.start", "status": claim.status or 200, "headers": out})
            await send({"type": "http.response.body", "body": stored})
            return

        status_code = 500
        content_type: str | None = None
        captured: list[bytes] = []

        async def capture_send(message: Message) -> None:
            nonlocal status_code, content_type
            if message["type"] == "http.response.start":
                status_code = message["status"]
                content_type = Headers(raw=message.get("headers", [])).get("content-type")
            elif message["type"] == "http.response.body":
                captured.append(message.get("body", b""))
            await send(message)

        assert claim.record_id is not None
        try:
            await self.app(scope, replay_receive, capture_send)
        except Exception:
            await run_in_threadpool(store.release, claim.record_id)
            raise
        if status_code >= 500:
            await run_in_threadpool(store.release, claim.record_id)
        else:
            await run_in_threadpool(store.complete, claim.record_id, status_code, b"".join(captured), content_type)
