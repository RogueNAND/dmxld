FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install OLA Python client
RUN pip install --no-cache-dir ola

WORKDIR /app

# Copy library source
COPY src/ /app/src/

# Copy default shows (users can mount over this)
COPY shows/ /app/shows/

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Default OLA connection (host machine)
ENV OLA_HOST=host.docker.internal
ENV OLA_PORT=9010

# User shows directory (mount your shows here)
VOLUME ["/app/shows"]

# Copy and set entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]
