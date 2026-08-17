# Hermes Proving Ground - container image
#
# Pure-stdlib Python 3.11 service. There are no third-party runtime
# dependencies, so no pip install step is required.

FROM python:3.11-slim

# Runtime hardening / determinism.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

# The health server resolves the static dashboard relative to its own file
# location (<repo>/backend/app/health_server.py -> <repo>/frontend), so both
# directories must live under /app.
COPY backend/ ./backend/
COPY frontend/ ./frontend/

EXPOSE 8765

# The app is healthy when the stdlib health check reports status "ok".
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m app.health_server --check || exit 1

CMD ["python", "-m", "app.health_server", "--host", "0.0.0.0", "--port", "8765"]
