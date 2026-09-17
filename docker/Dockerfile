# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps and pip-compile
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Metadata
LABEL org.opencontainers.image.title="CampusBell"
LABEL org.opencontainers.image.description="Daily Timetable Reminder App"
LABEL org.opencontainers.image.version="1.0.0"

# Non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd  --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser app.py       ./app.py
COPY --chown=appuser:appuser notifier.py  ./notifier.py
COPY --chown=appuser:appuser scheduler.py ./scheduler.py
COPY --chown=appuser:appuser static/      ./static/

# Copy default data files (they will be overridden by Docker volume mounts in prod)
COPY --chown=appuser:appuser timetable_data.json ./timetable_data.json
COPY --chown=appuser:appuser config.json          ./config.json

# Create log file with correct ownership so the app can write to it
RUN touch /app/reminder_logs.json && chown appuser:appuser /app/reminder_logs.json

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=8000

USER appuser

EXPOSE 8000

# Use exec form so signals propagate correctly (Ctrl-C / docker stop)
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
