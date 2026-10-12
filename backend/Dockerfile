# Wolf backend image (used by Railway; works on any container host).
FROM python:3.13-slim

ARG LITESTREAM_VERSION=0.3.13
ARG TARGETARCH=amd64

# Litestream continuously backs up the SQLite database to a bucket (optional, see deploy/start.sh).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-${TARGETARCH}.tar.gz" \
       | tar -xz -C /usr/local/bin litestream \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

WORKDIR /app
# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY deploy/start.sh deploy/litestream.yml ./
RUN chmod +x start.sh

ENV PATH="/app/.venv/bin:$PATH" \
    WOLF_DATA_DIR=/data \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["./start.sh"]
