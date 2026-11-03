"""Application services — the business layer between entry points and persistence.

Entry points (API routers, worker, graph nodes) call services; services call
repositories and own the transaction boundary (one commit per use case).

Modules are imported directly (``from packages.services.projects import ProjectService``)
rather than re-exported here, because ``script_intelligence`` depends on the workflow
graph, which itself depends on ``script_review``.
"""
