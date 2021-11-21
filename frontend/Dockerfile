# build frontned
FROM node:alpine as BUILD

WORKDIR /app
COPY . /app/

ENV NODE_OPTIONS=--openssl-legacy-provider
RUN npm install --silent
RUN npm install react-scripts@latest -g --silent
RUN npm run build

# prepare prod env
FROM nginx:alpine
COPY --from=BUILD /app/build /usr/share/nginx/html
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/

EXPOSE 80
CMD [ "nginx", "-g", "daemon off;" ]