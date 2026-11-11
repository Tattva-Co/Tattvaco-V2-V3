# Build from the repo root: docker build -f apps/worker/Dockerfile -t tattva-worker .
# (docker-compose.yml does this for you).
FROM python:3.11-slim

WORKDIR /srv

COPY pyproject.toml ./
RUN mkdir -p packages apps && touch packages/__init__.py apps/__init__.py
RUN pip install --no-cache-dir -e .

COPY packages ./packages
COPY apps ./apps
COPY alembic.ini ./

# No HEALTHCHECK: a polling loop process has no port to probe. docker-compose depends_on
# (condition: service_started) is the ordering signal for this service; its own liveness
# is the process exit code docker already tracks (a crashed worker exits non-zero).
CMD ["python", "-m", "apps.worker.worker"]
