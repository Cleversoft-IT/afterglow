# syntax=docker/dockerfile:1.7

# Two-stage build: Node builds the Expo web static bundle, nginx serves it.

FROM node:22-alpine AS builder
WORKDIR /app

# Install deps from package-lock.json — cached layer when only source changes.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --prefer-offline

# Build-time arg → injected into the bundle as process.env.EXPO_PUBLIC_API_BASE.
ARG EXPO_PUBLIC_API_BASE=https://api.95-179-245-107.sslip.io
ENV EXPO_PUBLIC_API_BASE=${EXPO_PUBLIC_API_BASE}

COPY . .
# Metro's per-module transform cache lives in /tmp/metro-cache and the
# project-local .expo/web/cache directory; mounting both as BuildKit
# caches lets the second deploy reuse them and skips re-transforming
# unchanged modules. Cold build still ~75s; warm builds drop a lot.
RUN --mount=type=cache,target=/tmp/metro-cache \
    --mount=type=cache,target=/app/.expo \
    --mount=type=cache,target=/root/.cache \
    npx expo export --platform web

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
