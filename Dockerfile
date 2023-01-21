# syntax=docker/dockerfile:1

# --- build stage: compile wheels so the runtime image needs no toolchain ----
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# --- runtime stage ----------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=tradecore.settings

WORKDIR /app

# curl is here for the compose healthcheck below and nothing else.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 tradecore \
    && useradd --system --uid 1001 --gid tradecore --create-home tradecore

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=tradecore:tradecore . .

# Collected at build time so the runtime filesystem can stay read-only.
RUN DJANGO_SECRET_KEY=build-time-only-not-used-at-runtime \
    DJANGO_DEBUG=false \
    python manage.py collectstatic --noinput

USER tradecore

EXPOSE 8000

CMD ["gunicorn", "tradecore.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-"]
