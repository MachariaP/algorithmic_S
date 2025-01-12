#!/bin/bash

# Installation script for String Search Server
# Must be run as root

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Print with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${1}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log "${RED}Please run as root${NC}"
    exit 1
fi

# Check prerequisites
log "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { log "${RED}Python 3 is required${NC}"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { log "${RED}pip3 is required${NC}"; exit 1; }
command -v virtualenv >/dev/null 2>&1 || { log "${RED}virtualenv is required${NC}"; exit 1; }

# Set up environment
log "Setting up test environment..."
INSTALL_DIR="/opt/string_search"
LOG_DIR="/var/log/string_search"
CONFIG_DIR="/etc/string_search"

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$CONFIG_DIR"

# Create service user
log "Setting up service user..."
useradd -r -s /bin/false string_search 2>/dev/null || true

# Install dependencies
log "Installing dependencies..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -r requirements.txt

# Generate SSL certificates
log "Generating SSL certificates..."
./generate_ssl.py

# Copy files
log "Copying files..."
cp -r server.py benchmark.py load_test.py "$INSTALL_DIR/"
cp config.ini "$CONFIG_DIR/"
cp string_search.service /etc/systemd/system/

# Set permissions
log "Setting permissions..."
chown -R string_search:string_search "$INSTALL_DIR"
chown -R string_search:string_search "$LOG_DIR"
chown -R string_search:string_search "$CONFIG_DIR"
chmod 755 "$INSTALL_DIR"
chmod 755 "$LOG_DIR"
chmod 644 "$CONFIG_DIR/config.ini"
chmod 644 /etc/systemd/system/string_search.service

# Install systemd service
log "Installing systemd service..."
systemctl daemon-reload
systemctl enable string_search.service

# Start service
log "Starting service..."
systemctl start string_search.service

# Run unit tests
log "Running unit tests..."
"$INSTALL_DIR/venv/bin/python" -m pytest tests/

# Run benchmark tests
log "Running benchmark tests..."
"$INSTALL_DIR/venv/bin/python" benchmark.py

# Run load tests
log "Running load tests..."
"$INSTALL_DIR/venv/bin/python" load_test.py

# Test basic functionality
log "Testing basic functionality..."
echo "test_string_1" | nc localhost 44445

# Print success message
log "${GREEN}Installation complete!${NC}"
log "Service is running at localhost:44445"
log "Configuration file: $CONFIG_DIR/config.ini"
log "Logs: $LOG_DIR/server.log"
log "Error logs: $LOG_DIR/error.log" 