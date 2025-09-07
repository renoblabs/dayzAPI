FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN if [ -f package-lock.json ]; then npm ci --omit=dev; \
    elif [ -f yarn.lock ]; then yarn install --production; \
    else npm install --omit=dev; fi
COPY tsconfig.json ./
COPY src ./src
RUN npm run build || (echo "Falling back to dev deps install" && npm install && npm run build)
EXPOSE 8080
CMD ["node", "dist/server.js"]
