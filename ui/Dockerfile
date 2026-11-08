FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24
USER root
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 8080
USER 101:101
CMD ["nginx", "-g", "daemon off;"]
