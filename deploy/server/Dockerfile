FROM python:3.13-slim AS builder
WORKDIR /notebook
COPY website/requirements.txt website/requirements.txt
RUN pip install --no-cache-dir -r website/requirements.txt
COPY website/ website/
COPY content/ content/
RUN python website/build.py

FROM nginx:stable-alpine
COPY deploy/server/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /notebook/build/site/ /usr/share/nginx/html/
EXPOSE 80
