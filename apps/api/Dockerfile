# Build from the repo root: docker build -f apps/api/Dockerfile -t tattva-api .
# (docker-compose.yml does this for you).
FROM python:3.11-slim

WORKDIR /srv

# No apt-get at all: psycopg[binary] ships its own libpq, so no postgres client headers
# are needed; libmagic/poppler etc. are deliberately not installed -- extraction
# (packages/services/extraction.py) uses pure-Python pypdf/python-docx/defusedxml. The
# healthcheck below uses Python's own stdlib instead of curl for the same reason: no
# system package install, nothing to go stale, one less thing to pull from an OS mirror.

COPY pyproject.toml ./
# A minimal package tree so `pip install -e .` can resolve the project's own name/version
# from pyproject.toml without the full source tree yet -- keeps the dependency-install
# layer cacheable independent of day-to-day code changes.
RUN mkdir -p packages apps && touch packages/__init__.py apps/__init__.py
RUN pip install --no-cache-dir -e .

COPY packages ./packages
COPY apps ./apps
COPY alembic.ini ./

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=3)"

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
