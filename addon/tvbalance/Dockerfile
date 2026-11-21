# Build context: the repository root.
#   docker build -f addon/tvbalance/Dockerfile -t tvbalance .
# The same image serves the Home Assistant Add-on and standalone Docker installs.

FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY engine/openapi.json /engine/openapi.json
RUN npm run build

FROM python:3.13-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY engine/pyproject.toml engine/pyproject.toml
COPY engine/src engine/src
COPY adapters adapters
COPY client/pyproject.toml client/pyproject.toml
COPY client/src client/src
RUN uv sync --frozen --no-dev --no-install-workspace --package tvbalance \
 && uv sync --frozen --no-dev \
      --package tvbalance \
      --package tvbalance-adapter-webos \
      --package tvbalance-adapter-roku \
      --package tvbalance-adapter-androidtv \
      --package tvbalance-adapter-samsung
COPY --from=web /web/dist /app/web

ARG BUILD_VERSION=dev
ARG BUILD_ARCH=amd64
LABEL io.hass.type="addon" \
      io.hass.name="TVBalance" \
      io.hass.version="${BUILD_VERSION}" \
      io.hass.arch="${BUILD_ARCH}" \
      org.opencontainers.image.title="TVBalance" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.source="https://github.com/tvbalance/tvbalance" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PATH="/app/.venv/bin:$PATH" \
    TVBALANCE_WEB_DIR=/app/web \
    TVBALANCE_DATA_DIR=/data \
    TVBALANCE_PORT=8765 \
    TVBALANCE_INGRESS_TRUSTED=172.30.32.2
VOLUME /data
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8765/api/v1/health', timeout=4)"
CMD ["tvbalance"]
