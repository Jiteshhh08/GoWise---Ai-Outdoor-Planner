FROM node:22-alpine AS frontend-build
WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /tmp/requirements.txt
RUN grep -v '^torch' /tmp/requirements.txt > /tmp/runtime-requirements.txt \
    && pip install --no-cache-dir -r /tmp/runtime-requirements.txt \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu 'torch>=2.6,<3'
COPY backend/app/ /app/backend/app/
COPY --from=frontend-build /workspace/frontend/dist/ /app/frontend/dist/
WORKDIR /app/backend
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
