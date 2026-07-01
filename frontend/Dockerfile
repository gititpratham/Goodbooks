# Stage 1: Compile TypeScript
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json and install typescript compiler
COPY package.json ./
RUN npm install

# Copy configuration and source files
COPY tsconfig.json ./
COPY src/ ./src/

# Compile TypeScript to JavaScript (generates ./dist/index.js)
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:stable-alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets (HTML and CSS) from root
COPY index.html /usr/share/nginx/html/
COPY index.css /usr/share/nginx/html/

# Copy compiled JavaScript output from Stage 1
COPY --from=build /app/dist /usr/share/nginx/html/dist

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
