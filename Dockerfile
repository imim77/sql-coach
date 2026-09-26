FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    POSTGRES_USER=sqlcoach \
    POSTGRES_PASSWORD=sqlcoach \
    POSTGRES_DB=sqlcoach \
    DATABASE_URL=postgresql://sqlcoach:sqlcoach@127.0.0.1:5432/sqlcoach \
    STUDENT_DATABASE_URL=postgresql://student:student@127.0.0.1:5432/sqlcoach \
    STATIC_DIR=/app/frontend/dist

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/exercises ./exercises
COPY db/init/ /docker-entrypoint-initdb.d/
COPY --from=frontend /src/frontend/dist /app/frontend/dist
COPY docker/entrypoint.sh /usr/local/bin/sqlcoach-entrypoint.sh

RUN chmod +x /usr/local/bin/sqlcoach-entrypoint.sh /docker-entrypoint-initdb.d/99_ready.sh \
    && mkdir -p /app/backend/tasks /app/backend/generated

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=20 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

ENTRYPOINT ["sqlcoach-entrypoint.sh"]
