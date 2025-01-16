# Technical Documentation

## Architecture Overview

### Core Components

```
string-search-server/
├── server.py           # Main server implementation
├── src/
│   ├── config/        # Configuration management
│   ├── search/        # Search algorithms
│   ├── ssl/           # SSL/TLS handling
│   └── utils/         # Utilities
├── tests/             # Test suite
├── benchmarks/        # Performance testing
└── docs/             # Documentation
```

### Data Flow

1. **Client Request**
   ```
   Client -> TCP Connection -> SSL (optional) -> Server
   ```

2. **Request Processing**
   ```
   Raw Request -> Rate Limiter -> Query Parser -> Search Engine -> Response Formatter
   ```

3. **Search Process**
   ```
   Query -> Cache -> Bloom Filter -> Hash Table -> File System (if REREAD=True)
   ```

## Implementation Details

### 1. Server Component

```python
class StringSearchServer:
    def __init__(self):
        # Initialize components
        self.setup_logging()
        self.load_config()
        self.initialize_data_structures()
        self.setup_network()

    def start(self):
        # Start server
        self.bind_socket()
        self.accept_connections()
```

Key features:
- Multi-threaded design
- Connection pooling
- Graceful shutdown
- Resource cleanup

### 2. Search Engine

#### Data Structures

1. **Bloom Filter**
   - Size: 2^24 bits (16MB)
   - Hash function: xxHash
   - False positive rate: 0.1%

2. **Hash Table**
   - Key: xxHash of string
   - Value: Original string
   - Load factor: 0.75

3. **LRU Cache**
   - Size: 10,000 entries
   - Eviction: Least Recently Used
   - Thread-safe implementation

#### Search Algorithm

```python
def search(query: str) -> bool:
    # 1. Check cache
    if query in cache:
        return cache[query]

    # 2. Check Bloom filter
    hash_val = xxhash(query)
    if not bloom_filter[hash_val]:
        return False

    # 3. Check hash table
    return hash_table.get(hash_val) == query
```

### 3. Configuration System

#### Configuration Sources
1. Default values
2. Configuration file
3. Environment variables
4. Command line arguments

#### Sample Configuration
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
```

### 4. Security Features

#### SSL/TLS Implementation
```python
def setup_ssl(self):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(
        certfile=self.config.ssl_cert_path,
        keyfile=self.config.ssl_key_path
    )
    return context
```

#### Rate Limiting
```python
def check_rate_limit(self, ip: str) -> bool:
    with self._lock:
        now = time.time()
        if ip not in self.request_times:
            self.request_times[ip] = []
        return len([t for t in self.request_times[ip] 
                   if t > now - 60]) < self.config.requests_per_minute
```

### 5. Monitoring and Logging

#### Metrics Collected
- Request count
- Response times
- Cache hit rates
- Memory usage
- Error rates

#### Logging Format
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True)
    ]
)
```

## Performance Optimization

### 1. Memory Management

```python
def optimize_memory(self):
    # Use memory mapping
    self.mmap_file = mmap.mmap(
        self.data_file.fileno(),
        0,
        access=mmap.ACCESS_READ
    )

    # Optimize string storage
    self.data = {line.strip() for line in self.mmap_file}
```

### 2. Concurrency Control

```python
def handle_client(self, client_sock: socket.socket):
    with self._lock:  # Thread-safe operations
        if not self._check_rate_limit(client_ip):
            return

    with ThreadPoolExecutor() as executor:
        future = executor.submit(self._process_request)
```

### 3. Cache Optimization

```python
@lru_cache(maxsize=10000)
def _cached_search(self, query: str) -> bool:
    # LRU cache with size limit
    return self._search_implementation(query)
```

## Error Handling

### 1. Network Errors

```python
try:
    client_sock.recv(1024)
except socket.error as e:
    logging.error(f"Network error: {e}")
    self._cleanup_connection(client_sock)
```

### 2. File System Errors

```python
try:
    with open(self.config.file_path, 'rb') as f:
        # File operations
except (IOError, OSError) as e:
    logging.error(f"File system error: {e}")
    raise
```

### 3. Memory Errors

```python
try:
    self.data_bloom = bitarray(2 ** 24)
except MemoryError:
    logging.error("Insufficient memory for Bloom filter")
    self._fallback_to_basic_mode()
```

## Testing Strategy

### 1. Unit Tests

```python
def test_search_exact_match(self):
    assert self.server._cached_search("test_string") is True
```

### 2. Integration Tests

```python
def test_end_to_end(self):
    with socket.create_connection(("localhost", 44445)) as s:
        s.sendall(b"test_string\n")
        assert b"STRING EXISTS" in s.recv(1024)
```

### 3. Performance Tests

```python
def test_response_time(self):
    start = time.perf_counter()
    result = self.server._cached_search("test_string")
    duration = time.perf_counter() - start
    assert duration < 0.001  # 1ms limit
```

## Deployment

### 1. System Requirements

- Python 3.8+
- 4GB RAM minimum
- SSD storage recommended
- Linux/Unix environment

### 2. Installation Steps

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate SSL certificates
python3 src/ssl/cert_gen.py

# 4. Configure service
sudo cp string_search.service /etc/systemd/system/
sudo systemctl enable string_search
```

### 3. Monitoring Setup

```bash
# Setup logging
mkdir -p /var/log/string-search
chown string-search:string-search /var/log/string-search

# Configure log rotation
cp string-search.logrotate /etc/logrotate.d/
```

## Maintenance

### 1. Backup Procedures

```bash
# Backup configuration
cp config/config.ini config/config.ini.bak

# Backup data
cp data/200k.txt data/200k.txt.bak
```

### 2. Update Procedures

```bash
# Update code
git pull origin master

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart string_search
```

### 3. Troubleshooting

See [TROUBLESHOOTING.md](troubleshooting.md) for detailed procedures. 