# Frontend image — local development (Next.js dev server with hot reload).
# A production build/runtime image is introduced when pages land (Slice 4 / ops).
FROM node:20-alpine

WORKDIR /app

# Install dependencies first for layer caching. No lockfile is committed yet
# (Slice 1/2); `npm install` is correct until package-lock.json lands.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000

# `next dev` boots the dev server now; App Router pages arrive in Slice 4.
CMD ["npm", "run", "dev"]
