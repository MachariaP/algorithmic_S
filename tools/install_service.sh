#!/bin/bash

# Install string search server as systemd service

# Create service file
cat > /etc/systemd/system/string-search.service << EOL
[Unit]
Description=String Search Server
After=network.target

[Service]
Type=simple
User=string-search
Group=string-search
WorkingDirectory=/opt/string-search
ExecStart=/opt/string-search/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

# Create user
useradd -r -s /bin/false string-search

# Create directories
mkdir -p /opt/string-search
mkdir -p /var/log/string-search

# Copy files
cp -r . /opt/string-search/
chown -R string-search:string-search /opt/string-search
chown -R string-search:string-search /var/log/string-search

# Enable and start service
systemctl daemon-reload
systemctl enable string-search
systemctl start string-search 