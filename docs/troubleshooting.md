# Troubleshooting Guide

## Common Issues and Solutions

### 1. Server Won't Start

#### Address Already in Use
```
OSError: [Errno 98] Address already in use
```

**Solution:**
1. Check if another instance is running:
```bash
sudo netstat -tulpn | grep 44445
```

2. Kill the existing process:
```bash
sudo kill <pid>
```

3. Or change the port in config.ini:
```ini
port = 44446
```

#### Permission Denied
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
1. Check file permissions:
```bash
ls -l /home/phines-macharia/Projects/portf/algorithmic_S
```

2. Fix permissions:
```bash
sudo chown -R phines-macharia:phines-macharia /home/phines-macharia/Projects/portf/algorithmic_S
sudo chmod 755 /home/phines-macharia/Projects/portf/algorithmic_S
```

### 2. SSL Issues

#### Certificate Not Found
```
ValueError: SSL certificate not found
```

**Solution:**
1. Generate new certificates:
```bash
python3 src/ssl/cert_gen.py
```

2. Check certificate paths in config.ini:
```ini
ssl_cert_path = ssl/server.crt
ssl_key_path = ssl/server.key
```

#### SSL Handshake Failed
```
ssl.SSLError: [SSL: HANDSHAKE_FAILURE] handshake failure
```

**Solution:**
1. Verify certificate configuration:
```bash
openssl x509 -in ssl/server.crt -text -noout
```

2. Check client SSL configuration:
```python
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
```

### 3. Performance Issues

#### High Memory Usage
```
MemoryError: Unable to allocate memory
```

**Solution:**
1. Check current memory usage:
```bash
ps aux | grep server.py
```

2. Adjust configuration:
```ini
cache_size = 5000  # Reduce cache size
buffer_size = 524288  # Reduce buffer size
```

#### Slow Response Times
```
Response times > 40ms with REREAD_ON_QUERY=True
```

**Solution:**
1. Enable performance logging:
```ini
log_level = DEBUG
```

2. Check system resources:
```bash
top -p <pid>
```

3. Optimize settings:
```ini
max_workers = 50  # Reduce worker threads
reread_on_query = false  # Disable rereading if not needed
```

### 4. Data File Issues

#### File Not Found
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/200k.txt'
```

**Solution:**
1. Check file path in config.ini:
```ini
linuxpath = data/200k.txt
```

2. Create data directory:
```bash
mkdir -p data
```

3. Download test data:
```bash
wget -O data/200k.txt https://www.dropbox.com/s/vx9bvgx3scl5qn4/200k.txt
```

#### File Permission Issues
```
PermissionError: [Errno 13] Permission denied: 'data/200k.txt'
```

**Solution:**
1. Fix file permissions:
```bash
sudo chown phines-macharia:phines-macharia data/200k.txt
chmod 644 data/200k.txt
```

### 5. Service Management

#### Service Won't Start
```
Failed to start string_search.service: Unit not found
```

**Solution:**
1. Check service file:
```bash
sudo systemctl status string_search
```

2. Reload systemd:
```bash
sudo systemctl daemon-reload
```

3. Check service file location:
```bash
ls -l /etc/systemd/system/string_search.service
```

#### Service Crashes
```
Process exited with status 1
```

**Solution:**
1. Check logs:
```bash
sudo journalctl -u string_search -n 50
```

2. Check permissions:
```bash
sudo systemctl status string_search
```

3. Verify Python path:
```bash
which python3
```

### 6. Rate Limiting Issues

#### Too Many Requests
```
RATE LIMIT EXCEEDED
```

**Solution:**
1. Check current limits:
```ini
rate_limit_enabled = true
requests_per_minute = 1000
```

2. Adjust if needed:
```ini
requests_per_minute = 2000  # Increase limit
```

3. Monitor request patterns:
```bash
tail -f logs/server.log | grep "Rate limit"
```

### 7. Logging Issues

#### No Log Output
```
No logs appearing in console or file
```

**Solution:**
1. Check log configuration:
```ini
log_level = INFO
log_file = logs/server.log
```

2. Create log directory:
```bash
mkdir -p logs
touch logs/server.log
chmod 644 logs/server.log
```

3. Verify logging setup:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler()]
)
```

### 8. Client Connection Issues

#### Connection Refused
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:**
1. Verify server is running:
```bash
ps aux | grep server.py
```

2. Check firewall:
```bash
sudo ufw status
```

3. Allow port:
```bash
sudo ufw allow 44445/tcp
```

### Getting Help

If you encounter issues not covered in this guide:

1. Check the logs:
```bash
tail -f logs/server.log
```

2. Enable debug logging:
```ini
log_level = DEBUG
```

3. Run tests:
```bash
pytest tests/
```

4. Check system resources:
```bash
htop
df -h
free -m
``` 