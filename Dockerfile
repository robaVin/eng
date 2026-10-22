# Multi-stage build: build the frontend, then serve it from the FastAPI backend.
# Single web service — suitable for Render (Docker runtime).

# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend runtime ----
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
# FastAPI serves the built frontend from <repo>/frontend/dist
# (app/main.py resolves parents[2]/frontend/dist == /app/frontend/dist).
COPY --from=frontend /app/frontend/dist /app/frontend/dist

EXPOSE 8000
# Render provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
