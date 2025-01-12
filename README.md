# High-Performance String Search Server

A high-performance TCP server for exact string matching in large text files, optimized for speed and scalability.

## Features

- **High Performance**
  - O(1) lookups using Bloom filters and hash tables
  - Memory-mapped file access
  - LRU caching with >80% hit rate
  - Sub-millisecond response times
  - Supports 10,000+ concurrent connections

- **Security**
  - SSL/TLS encryption support
  - Rate limiting
  - Buffer overflow protection
  - Input validation

- **Monitoring**
  - Real-time performance metrics
  - Cache hit rate tracking
  - Memory usage monitoring
  - Detailed logging

- **Reliability**
  - Graceful error handling
  - Automatic fallbacks
  - Comprehensive test coverage
  - Memory leak protection

## Performance Benchmarks

| Configuration | Average Time | Max Time | Memory Usage |
|--------------|--------------|----------|--------------|
| REREAD=False | 0.02ms      | 0.5ms    | ~50MB       |
| REREAD=True  | 35ms        | 40ms     | ~50MB       |

## Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install as service:
```bash
sudo ./scripts/install.sh
```

## Configuration

Edit `config/config.ini`:

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
ssl_cert_path = ssl/server.crt
ssl_key_path = ssl/server.key
rate_limit_enabled = true
requests_per_minute = 1000

# Logging
log_level = INFO
log_file = logs/server.log
```

## SSL Setup

1. Generate self-signed certificate:
```bash
./tools/setup_ssl.py
```

2. Enable SSL in config:
```ini
ssl_enabled = true
```

## Usage

### Start Server
```bash
# As service
sudo systemctl start string-search

# Manual start
./server.py
```

### Client Usage
```bash
# Basic search
./client.py

# With SSL
./client.py --ssl

# Custom host/port
./client.py --host example.com --port 44445
```

## Testing

Run test suite:
```bash
pytest tests/
```

Performance tests:
```bash
./tools/benchmark.py
```

## Architecture

### Core Components

1. **Server (`server.py`)**
   - Multi-threaded TCP server
   - Connection handling
   - Request processing

2. **Search Engine**
   - Bloom filter for quick rejection
   - Hash table for O(1) lookups
   - Memory-mapped file access
   - LRU caching

3. **Security Layer**
   - SSL/TLS encryption
   - Rate limiting
   - Input validation

4. **Monitoring**
   - Performance metrics
   - Resource usage
   - Cache statistics

### Optimization Techniques

1. **Bloom Filter**
   - 16MB size optimized for 250K entries
   - False positive rate < 0.1%
   - Eliminates unnecessary disk reads

2. **Hash Table**
   - O(1) lookup for existing strings
   - XXHash for fast hashing
   - Memory efficient storage

3. **Memory Mapping**
   - Direct file access
   - Reduced system calls
   - Shared memory benefits

4. **LRU Cache**
   - 10K entry cache
   - >80% hit rate for common queries
   - Sub-microsecond cache lookups

## Performance Tuning

### Memory Usage

- Bloom filter: 16MB
- Hash table: ~2MB per 10K entries
- Memory map: File size
- Cache: ~1MB per 1K entries

### Concurrency

- Default: 100 worker threads
- Maximum: 10,000 concurrent connections
- Rate limit: 1,000 requests/minute

## Troubleshooting

### Common Issues

1. **Address in use**
   ```bash
   sudo netstat -tulpn | grep 44445
   sudo kill <pid>
   ```

2. **Permission denied**
   ```bash
   sudo chown string-search:string-search /opt/string-search
   sudo chmod 755 /opt/string-search
   ```

3. **SSL errors**
   ```bash
   ./tools/setup_ssl.py --force
   ```

## Contributing

This is a private project. Please do not share or distribute the code.

## License

Proprietary and confidential. All rights reserved.

## Project Structure

```
string-search-server/
├── src/                      # Source code
│   ├── __init__.py
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   └── config.py       # Configuration handling
│   ├── search/             # Search implementation
│   │   ├── __init__.py
│   │   └── matcher.py      # String matching algorithms
│   ├── monitoring/         # Performance monitoring
│   │   ├── __init__.py
│   │   └── metrics.py      # Metrics collection
│   ├── rate_limiter/       # Rate limiting
│   │   ├── __init__.py
│   │   └── limiter.py      # Rate limiting implementation
│   ├── ssl/                # SSL handling
│   │   ├── __init__.py
│   │   ├── ssl_config.py   # SSL configuration
│   │   └── cert_gen.py     # Certificate generation
│   └── utils/              # Utilities
│       ├── __init__.py
│       ├── logging.py      # Logging configuration
│       └── monitoring.py   # Monitoring utilities
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Test configuration
│   ├── test_server.py     # Server tests
│   ├── test_search.py     # Search tests
│   └── test_comprehensive.py # Integration tests
├── tools/                  # Utility scripts
│   ├── benchmark.py       # Performance benchmarking
│   ├── setup_ssl.py       # SSL setup utility
│   └── monitor.py         # Monitoring tool
├── scripts/               # Installation scripts
│   ├── install.sh        # Installation script
│   └── setup_project.py  # Project setup
├── docs/                 # Documentation
│   ├── USER_GUIDE.md    # User guide
│   ├── TECHNICAL_DOCS.md # Technical documentation
│   └── configuration.md  # Configuration guide
├── data/                 # Data files
│   └── README.md        # Data documentation
├── config/              # Configuration files
│   └── config.ini      # Main configuration
├── requirements.txt    # Python dependencies
├── setup.py           # Package setup
├── server.py         # Main server script
├── client.py        # Client implementation
└── README.md       # Project documentation
```

## Key Files

### Core Components
- [server.py](server.py) - Main server implementation
- [client.py](client.py) - Client implementation
- [src/search/matcher.py](src/search/matcher.py) - Search algorithms
- [src/config/config.py](src/config/config.py) - Configuration management

### Configuration
- [config/config.ini](config/config.ini) - Main configuration file
- [.env](.env) - Environment variables
- [docs/configuration.md](docs/configuration.md) - Configuration guide

### Documentation
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - User guide
- [docs/TECHNICAL_DOCS.md](docs/TECHNICAL_DOCS.md) - Technical documentation
- [docs/performance.md](docs/performance.md) - Performance analysis

### Testing
- [tests/test_server.py](tests/test_server.py) - Server tests
- [tests/test_search.py](tests/test_search.py) - Search algorithm tests
- [tests/test_comprehensive.py](tests/test_comprehensive.py) - Integration tests

### Tools
- [tools/benchmark.py](tools/benchmark.py) - Performance benchmarking
- [tools/setup_ssl.py](tools/setup_ssl.py) - SSL setup utility
- [tools/monitor.py](tools/monitor.py) - Real-time monitoring

### Installation
- [scripts/install.sh](scripts/install.sh) - Installation script
- [string_search.service](string_search.service) - Systemd service file
