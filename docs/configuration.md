# Configuration Guide

## Overview
The String Search Server is configured through `config/config.ini`. This guide explains each configuration option.

## File Settings

### linuxpath
- Path to the data file containing search strings
- Example: `linuxpath = data/200k.txt`
- Must be readable by the server process

### reread_on_query
- Controls file reading behavior
- `true`: Re-read file on every query (for dynamic files)
- `false`: Read file once at startup (for static files)
- Performance impact: ~40ms vs 0.5ms per query

## Performance Settings

### max_workers
- Maximum number of concurrent worker threads
- Default: 100
- Increase for higher concurrency
- Memory impact: ~1MB per worker

### cache_size
- Number of recent queries to cache
- Default: 10000
- Memory impact: ~100 bytes per entry

### buffer_size
- Socket buffer size in bytes
- Default: 1048576 (1MB)
- Adjust based on network conditions

## Security Settings

### ssl_enabled
- Enable/disable SSL encryption
- Requires valid certificate and key in `ssl/` directory
- Generate using `tools/setup_ssl.py`

### rate_limit_enabled
- Enable/disable request rate limiting
- Prevents DoS attacks

### requests_per_minute
- Maximum requests per minute per IP
- Default: 1000
- Adjust based on client needs

## Example Configuration
```ini
[DEFAULT]
# File settings
linuxpath = data/200k.txt
reread_on_query = false

# Performance
max_workers = 100
cache_size = 10000
buffer_size = 1048576

# Security
ssl_enabled = true
rate_limit_enabled = true
requests_per_minute = 1000
``` 