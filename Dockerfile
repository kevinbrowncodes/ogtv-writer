# syntax=docker/dockerfile:1
# ==============================================================================
# Multi-stage build:
#   1. css      — compile Tailwind with Node (build-time only)
#   2. runtime  — slim Python image that runs the app as a non-root user
# ==============================================================================

# --- Stage 1: build CSS -------------------------------------------------------
FROM node:20-alpine AS css
WORKDIR /build
COPY package.json ./
RUN npm install
COPY tailwind.config.js ./
COPY app ./app
RUN npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/app.css --minify

# --- Stage 2: runtime ---------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=production \
    HOST=0.0.0.0 \
    PORT=8000

# Build stamp baked in at image-build time (passed by `make deploy`); surfaced in
# the UI footer and /healthz so you can confirm exactly which build is running.
ARG BUILD_VERSION=""
ENV BUILD_VERSION=$BUILD_VERSION

WORKDIR /app

# Install the app + dependencies. Copy metadata + source, then `pip install .`.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install .

# Bring in the compiled CSS from the css stage (overwrites any local copy).
COPY --from=css /build/app/static/css/app.css ./app/static/css/app.css

# Alembic config + migration scripts must live at the image root: on startup the
# app runs migrations_runner.upgrade_to_head(), which loads ./alembic.ini and
# ./migrations (resolved relative to the repo root, i.e. /app). Without these the
# container crashes before serving. Copied before the chown so appuser owns them.
COPY alembic.ini ./
COPY migrations ./migrations

# Run as a non-root user; ensure the SQLite data dir is writable.
RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# A single worker is fine for SQLite. For Postgres + multiple workers, see README.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
