# High-Performance String Search Server

A high-performance TCP server for exact string matching in large text files, optimized for speed and scalability.

## Features

- O(1) lookups using optimized data structures (Bloom filter + Hash table)
- Memory-mapped file access for performance
- LRU caching of search results
- SSL support with configurable authentication
- Rate limiting capabilities
- Comprehensive logging and monitoring
- Graceful error handling and fallbacks

## Performance

- REREAD_ON_QUERY=False: ~0.02ms average search time
- REREAD_ON_QUERY=True: ~35ms average search time
- Supports up to 10,000 concurrent connections
- Memory usage: ~50MB for 250,000 lines

## Requirements

- Python 3.8+
- Linux/Unix environment
- Dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd string-search-server
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Generate SSL certificates (if using SSL):
```bash
python3 src/ssl/cert_gen.py
```

5. Configure the server:
```bash
cp config/config.ini.example config/config.ini
# Edit config.ini with your settings
```

## Running as a Linux Service

1. Copy the service file:
```bash
sudo cp string_search.service /etc/systemd/system/
```

2. Edit the service file to match your installation path:
```bash
sudo nano /etc/systemd/system/string_search.service
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable string_search
sudo systemctl start string_search
```

4. Check service status:
```bash
sudo systemctl status string_search
```

## Usage

### Starting the Server

```bash
# Development mode
python3 server.py

# Production mode (as service)
sudo systemctl start string_search
```

### Client Usage

```python
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('localhost', 44445))
    s.sendall(b"your_search_string\n")
    response = s.recv(1024).decode()
    print(response)
```

## Configuration

Key configuration options in `config.ini`:

```ini
[DEFAULT]
# File settings
linuxpath = data/200k.txt
reread_on_query = false

# Performance settings
max_workers = 100
cache_size = 10000
buffer_size = 1048576

# Security settings
ssl_enabled = false
ssl_cert_path = ssl/server.crt
ssl_key_path = ssl/server.key
rate_limit_enabled = true
requests_per_minute = 1000
```

## Testing

Run the test suite:
```bash
pytest tests/
```

Run benchmarks:
```bash
python3 benchmarks/search_algorithms.py
```

## Performance Report

See [PERFORMANCE.md](docs/PERFORMANCE.md) for detailed benchmarks comparing different search algorithms.

## Security

- SSL/TLS encryption support
- Rate limiting per IP
- Buffer overflow protection
- Input validation
- Configurable authentication

## Monitoring

The server provides comprehensive logging and monitoring:
- Request logs with timestamps
- Performance metrics
- Error tracking
- Cache hit rates
- Resource usage statistics

## Troubleshooting

See [TROUBLESHOOTING.md](docs/troubleshooting.md) for common issues and solutions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.