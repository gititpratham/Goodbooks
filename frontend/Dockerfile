FROM node:20-alpine

WORKDIR /app

# Copy dependency files first
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application source
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Start Vite dev server in host mode
CMD ["npm", "run", "dev"]
