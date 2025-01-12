#!/bin/bash

# Test setup script
set -e

# Create test directories
TEST_DIR="/tmp/string_search"
sudo mkdir -p "$TEST_DIR"/{data,logs,ssl}
sudo chown -R string_search:string_search "$TEST_DIR"

# Copy files
sudo cp server.py "$TEST_DIR/"
sudo cp config.ini "$TEST_DIR/"
sudo cp -r data/* "$TEST_DIR/data/"

# Set up Python environment
sudo -u string_search python3 -m venv "$TEST_DIR/venv"
sudo -u string_search "$TEST_DIR/venv/bin/pip" install -r requirements.txt

# Generate SSL certificates
sudo -u string_search ./generate_ssl.py -o "$TEST_DIR/ssl" -n localhost

# Set permissions
sudo chmod 755 "$TEST_DIR"
sudo chmod 644 "$TEST_DIR/config.ini"
sudo chmod 644 "$TEST_DIR/server.py"

# Update systemd service
sudo cp string_search.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "Test setup complete. Try starting the service:"
echo "sudo systemctl start string_search"
echo "sudo systemctl status string_search" 