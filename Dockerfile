FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user first
RUN useradd --create-home appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code with correct ownership
COPY --chown=appuser:appuser service/ ./service/

# Switch to non-root user
USER appuser

# MODE: "webhook" (push to TRMNL) or "api" (TRMNL polls us)
ENV MODE=webhook

# Webhook mode settings
ENV INTERVAL=300

# API mode settings
ENV HOST=0.0.0.0
ENV PORT=8080

# Dual-mode entrypoint
CMD if [ "$MODE" = "api" ]; then \
      exec gunicorn -b ${HOST}:${PORT} "service.api:create_app()"; \
    else \
      exec python -m service.main; \
    fi
