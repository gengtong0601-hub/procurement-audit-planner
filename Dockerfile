FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock.txt requirements.lock.txt
# Optional build_ca supplies the trusted CA bundle on corporate proxy networks.
RUN --mount=type=secret,id=build_ca,target=/etc/ssl/certs/ca-certificates.crt pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd --create-home auditor && mkdir -p /app/runtime && chown -R auditor:auditor /app
USER auditor
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 8 --timeout 300 harness.app:app"]
