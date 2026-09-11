FROM nginx:1.31.5
# This is a full main-context nginx config, so it must replace /etc/nginx/nginx.conf,
# not land in conf.d/ (which is included inside the http{} block).
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx
COPY nginx.conf /etc/nginx/templates/nginx.conf.template
