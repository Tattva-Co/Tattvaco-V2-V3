# Build from the repo root: docker build -f apps/web/Dockerfile -t tattva-web apps/web
# (docker-compose.yml does this for you, with apps/web itself as the build context --
# this Dockerfile never reaches outside that directory).
FROM node:20-alpine AS build
WORKDIR /srv
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /srv/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
# 127.0.0.1, not localhost: this image's /etc/hosts resolves "localhost" to ::1 first,
# and nginx (see nginx.conf) only listens on 0.0.0.0, so busybox wget's IPv6 attempt was
# refused before ever falling back to IPv4 -- verified against a real running container.
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
    CMD wget -qO- http://127.0.0.1/ > /dev/null || exit 1
