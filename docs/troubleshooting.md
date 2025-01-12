# Troubleshooting Guide

## Common Issues

### Server Won't Start

#### Address Already in Use
```
Error: [Errno 98] Address already in use
```

Solution:
1. Check for running instances:
```bash
ps aux | grep server.py
```

2. Kill existing process:
```bash
pkill -f server.py
```

3. Wait for socket timeout:
```bash
sleep 60
```

#### Permission Denied
```
Error: Permission denied: '/opt/string-search'
```

Solution:
```bash
sudo chown -R string-search:string-search /opt/string-search
sudo chmod 755 /opt/string-search
```

### Connection Refused

#### Server Not Running
Verify server status:
```bash
systemctl status string-search
```

#### Firewall Issues
Check firewall:
```bash
sudo ufw status
sudo ufw allow 44445/tcp
```

### SSL Errors

#### Certificate Not Found
```
Error: SSL certificate not found
```

Solution:
```bash
python tools/setup_ssl.py
```

#### Certificate Permission
```
Error: Permission denied: 'ssl/server.key'
```

Solution:
```bash
sudo chown string-search:string-search ssl/
sudo chmod 600 ssl/server.key
```

## Performance Issues

### Slow Response Times

1. Check file reading mode:
```ini
reread_on_query = false
```

2. Verify data file size:
```bash
wc -l data/200k.txt
```

3. Monitor system resources:
```bash
top -p $(pgrep -f server.py)
```

### Memory Usage

1. Check cache size:
```ini
cache_size = 10000
```

2. Monitor memory:
```bash
python tools/monitor_memory.py
```

## Logging

### Enable Debug Logs
```ini
log_level = DEBUG
```

### View Logs
```bash
tail -f logs/server.log
```

### Analyze Logs
```bash
python tools/analyze_logs.py
``` 