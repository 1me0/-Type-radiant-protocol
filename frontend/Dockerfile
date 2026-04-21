# frontend/Dockerfile
# Multi‑stage build for the Radiant Protocol frontend (React)
# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files first (better layer caching)
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy the rest of the source code
COPY . .

# Build the production bundle
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine

# Copy custom nginx configuration (optional, but recommended for SPA routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Healthcheck to ensure the server is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost/ || exit 1

# Run nginx as a non‑root user for better security
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

USER nginx

CMD ["nginx", "-g", "daemon off;"]
