ARG NODE_IMAGE
ARG CADDY_IMAGE
FROM ${NODE_IMAGE} AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_AMAP_WEB_JS_KEY
ENV VITE_API_BASE_URL="" VITE_AMAP_WEB_JS_KEY=${VITE_AMAP_WEB_JS_KEY}
RUN npm run build
FROM ${CADDY_IMAGE}
COPY --from=build /app/dist /srv/trip
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY deploy/portal/ /srv/portal/
