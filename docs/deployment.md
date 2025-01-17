# Deployment Guide

This guide covers deployment options for the String Search Server.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Bare Metal Deployment](#bare-metal-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring Setup](#monitoring-setup)
- [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements
- CPU: 2+ cores recommended
- RAM: 4GB minimum, 8GB recommended
- Storage: 1GB + data file size
- Network: 100Mbps minimum

### Software Requirements
- Python 3.8+
- OpenSSL 1.1.1+
- Docker (optional)
- Prometheus (optional)
- Grafana (optional)

## Docker Deployment

### Building the Image
```bash
# Clone repository
git clone <repository-url>
cd string-search-server

# Build image
docker build -t string-search-server:latest .
```

### Running with Docker
```bash
# Basic run
docker run -d \
  --name string-search \
  -p 44445:44445 \
  -p 9090:9090 \
  -v /path/to/data:/app/data \
  -v /path/to/config:/app/config \
  string-search-server:latest

# Run with environment variables
docker run -d \
  --name string-search \
  -p 44445:44445 \
  -p 9090:9090 \
  -v /path/to/data:/app/data \
  -v /path/to/config:/app/config \
  -e SERVER_HOST=0.0.0.0 \
  -e SERVER_PORT=44445 \
  -e SSL_ENABLED=true \
  string-search-server:latest
```

### Docker Compose
```yaml
version: '3.8'
services:
  search-server:
    build: .
    ports:
      - "44445:44445"
      - "9090:9090"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=44445
      - SSL_ENABLED=true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Bare Metal Deployment

### System Setup
```bash
# Create user
sudo useradd -r -s /bin/false searchserver
sudo mkdir -p /opt/string-search
sudo chown searchserver:searchserver /opt/string-search

# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip openssl

# Install application
git clone <repository-url> /opt/string-search
cd /opt/string-search
pip3 install -r requirements.txt
```

### Systemd Service
```bash
# Copy service file
sudo cp string_search.service /etc/systemd/system/

# Start service
sudo systemctl daemon-reload
sudo systemctl enable string_search
sudo systemctl start string_search

# Check status
sudo systemctl status string_search
```

## Cloud Deployment

### AWS Deployment
1. Create EC2 instance (t3.small minimum)
2. Configure security groups:
   - Port 44445 (TCP)
   - Port 9090 (TCP)
3. Deploy using Docker or bare metal method
4. Configure AWS Application Load Balancer (optional)

### Google Cloud
1. Create Compute Engine instance
2. Configure firewall rules
3. Deploy using Docker or bare metal method
4. Configure Cloud Load Balancing (optional)

### Azure
1. Create Virtual Machine
2. Configure Network Security Group
3. Deploy using Docker or bare metal method
4. Configure Azure Load Balancer (optional)

## Monitoring Setup

### Prometheus Setup
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'string-search'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Grafana Setup
1. Import dashboard from `monitoring/dashboards/grafana.json`
2. Configure Prometheus data source
3. Set up alerting rules

### Alert Manager
```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'team-email'

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@example.com'
```

## Security Considerations

### SSL/TLS Setup
```bash
# Generate self-signed certificates
python3 src/ssl/cert_gen.py

# Use Let's Encrypt
certbot certonly --standalone -d your-domain.com
```

### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw allow 44445/tcp
sudo ufw allow 9090/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 44445 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 9090 -j ACCEPT
```

### File Permissions
```bash
# Set correct permissions
sudo chown -R searchserver:searchserver /opt/string-search
sudo chmod 600 /opt/string-search/ssl/*
sudo chmod 600 /opt/string-search/config/*
```

## Maintenance

### Backup
```bash
# Backup configuration
tar czf config-backup.tar.gz config/

# Backup data
tar czf data-backup.tar.gz data/
```

### Updates
```bash
# Update code
git pull origin main

# Update dependencies
pip3 install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart string_search
```

### Log Rotation
```bash
# /etc/logrotate.d/string-search
/var/log/string-search/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 searchserver searchserver
} 