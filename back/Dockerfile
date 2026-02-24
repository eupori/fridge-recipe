FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 + Node.js for Claude Code CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create data directories for image cache (writable by appuser)
RUN mkdir -p /app/data/images

# Create non-root user
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
