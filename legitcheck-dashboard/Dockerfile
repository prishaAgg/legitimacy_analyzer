FROM node:20-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

EXPOSE 5173

# Vite dev server — binds to 0.0.0.0 so Docker can expose it
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
