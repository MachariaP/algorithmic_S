# Use Python 3.8 slim base image
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/ssl

# Generate self-signed certificates for development
RUN python src/ssl/cert_gen.py

# Create non-root user
RUN useradd -m -u 1000 searchserver
RUN chown -R searchserver:searchserver /app
USER searchserver

# Expose ports
EXPOSE 44445  # Main server port
EXPOSE 9090   # Prometheus metrics port

# Set environment variables
ENV PYTHONPATH=/app
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=44445

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Run server
CMD ["python", "server.py"] 