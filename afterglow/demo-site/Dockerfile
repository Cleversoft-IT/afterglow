# syntax=docker/dockerfile:1.7

# Vite static build + nginx, mirroring the app/ Dockerfile.

FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --prefer-offline

ARG VITE_APP_URL=https://app.95-179-245-107.sslip.io
ENV VITE_APP_URL=${VITE_APP_URL}

# Cap Node heap to keep `vite build` from getting OOM-killed on
# the small Coolify VM (build silently dies after "computing gzip
# size" otherwise — log just stops mid-chunk).
ENV NODE_OPTIONS=--max-old-space-size=1024

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
