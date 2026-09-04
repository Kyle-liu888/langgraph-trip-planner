ARG NODE_IMAGE
ARG UV_IMAGE
ARG PYTHON_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=uv /uv /uvx /usr/local/bin/
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 dev && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash dev \
    && mkdir -p /workspace/backend/.venv /workspace/frontend/node_modules /home/dev/.cache/uv /home/dev/.npm \
    && chown -R dev:dev /workspace /home/dev
ENV UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
USER dev
WORKDIR /workspace
CMD ["sleep", "infinity"]
