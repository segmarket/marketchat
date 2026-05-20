# Estágio 1: build do Vite
FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=
ARG VITE_APP_ORIGIN=
ARG VITE_MARKETING_ORIGIN=
ARG VITE_PLAN_PRICE=59,90
ARG VITE_TRIAL_SUBSCRIPTION_PRICE=59,90

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_APP_ORIGIN=$VITE_APP_ORIGIN \
    VITE_MARKETING_ORIGIN=$VITE_MARKETING_ORIGIN \
    VITE_PLAN_PRICE=$VITE_PLAN_PRICE \
    VITE_TRIAL_SUBSCRIPTION_PRICE=$VITE_TRIAL_SUBSCRIPTION_PRICE

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# Em Docker usamos vite build direto (tsc exige @types/node no CI).
RUN npx vite build

# Estágio 2: servir SPA
FROM node:20-alpine

RUN npm install -g serve

WORKDIR /app

COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
