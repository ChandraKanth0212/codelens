FROM node:22-bookworm-slim AS web
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM node:22-bookworm-slim AS analyzer
WORKDIR /build/analyzer
COPY analyzer/package*.json ./
RUN npm ci --omit=dev

FROM python:3.13-slim-bookworm AS runtime
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY codelens ./codelens
RUN pip install --no-cache-dir -c requirements.lock . && useradd --uid 10001 --create-home codelens
COPY analyzer ./analyzer
COPY --from=analyzer /build/analyzer/node_modules ./analyzer/node_modules
COPY migrations ./migrations
COPY alembic.ini ./
COPY --from=web /build/web/dist ./web/dist
USER 10001
EXPOSE 8000
CMD ["uvicorn", "codelens.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
