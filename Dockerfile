# BrainMed+ — permanent host (API + built SPA)
FROM node:22-bookworm AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# System deps often needed by scipy/mne wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY config.py config_ext.py ./
COPY src ./src
COPY docs ./docs
COPY runtime_assets/models ./models
COPY runtime_assets/data ./data
COPY --from=frontend /frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn src.api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
