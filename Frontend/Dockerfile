# ── Etapa 1: Build de React con Vite ─────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Se puede sobreescribir en build-time para apuntar a otra API
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# ── Etapa 2: Servir el build estático con Nginx ──────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
