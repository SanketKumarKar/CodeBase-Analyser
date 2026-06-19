# ==============================================================================
# Frontend Dockerfile — Next.js 14 (development mode)
# ==============================================================================

FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
