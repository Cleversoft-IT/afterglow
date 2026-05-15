# Two-stage build: Node builds the Expo web static bundle, nginx serves it.

FROM node:22-alpine AS builder
WORKDIR /app

# Install deps from package-lock.json — cached layer when only source changes.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Build-time arg → injected into the bundle as process.env.EXPO_PUBLIC_API_BASE.
ARG EXPO_PUBLIC_API_BASE=https://api.95-179-245-107.sslip.io
ENV EXPO_PUBLIC_API_BASE=${EXPO_PUBLIC_API_BASE}

COPY . .
RUN npx expo export --platform web

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
