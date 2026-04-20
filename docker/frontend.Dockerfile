FROM node:20-alpine AS base
WORKDIR /app
COPY frontend/package.json ./frontend/package.json
COPY frontend/tsconfig.json ./frontend/tsconfig.json
COPY frontend/next.config.mjs ./frontend/next.config.mjs
COPY frontend/tailwind.config.ts ./frontend/tailwind.config.ts
COPY frontend/postcss.config.mjs ./frontend/postcss.config.mjs
COPY frontend/app ./frontend/app
COPY frontend/components ./frontend/components
WORKDIR /app/frontend
RUN npm install
RUN npm run build
CMD ["npm", "run", "start"]
