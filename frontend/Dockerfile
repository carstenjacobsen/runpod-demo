FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html config.js /usr/share/nginx/html/
COPY 40-write-config.sh /docker-entrypoint.d/40-write-config.sh
RUN chmod +x /docker-entrypoint.d/40-write-config.sh

EXPOSE 80

# Write config.js from API_URL, then start nginx. Done in ENTRYPOINT so it
# still runs if the platform replaces the default nginx startup scripts.
ENTRYPOINT ["/bin/sh", "-c", "/docker-entrypoint.d/40-write-config.sh && exec nginx -g 'daemon off;'"]
