# String Search Server

## Project Overview
A high-performance TCP server implementation that efficiently searches for exact string matches in large datasets. This server is designed to handle high-throughput string search operations with sub-millisecond response times.

### Problem Statement
- Need for fast string searching in large datasets
- Requirement to handle concurrent requests efficiently
- Necessity for real-time response with large files
- Challenge of maintaining performance with file updates

### Solution
- In-memory data structure for O(1) lookups
- Thread pool for concurrent request handling
- Configurable caching system
- Real-time file monitoring capability

### Comparison with Existing Solutions
- Faster than traditional grep-based solutions
- More memory efficient than full-text search engines
- Simpler deployment than distributed systems
- Custom-built for exact string matching

## 🚀 Key Features

- **High Performance**
  - ⚡ Sub-millisecond response times (0.5ms) with caching enabled
  - 📈 Handles files up to 250,000 rows efficiently
  - 🔄 Concurrent request handling with thread pooling
  - 🎯 Exact string matching (no partial matches)

- **Enterprise Ready**
  - 🔒 SSL/TLS encryption support
  - 📊 Comprehensive logging and monitoring
  - 🛡️ Buffer overflow protection
  - 🔧 Configurable via config.ini
  - 👥 Unlimited concurrent connections

## Technical Details

### Search Algorithm
- Set-based lookup for O(1) time complexity
- Memory-mapped file reading for large files
- Optimized string comparison
- Cache-friendly data structures

### Memory Management
- Efficient memory allocation
- Garbage collection optimization
- Memory pooling for connections
- Cache size limits and eviction policies

### Threading Model
- Thread pool executor
- Connection queuing
- Thread-safe data structures
- Resource limiting

### Cache Implementation
- LRU cache policy
- Thread-safe cache access
- Configurable cache size
- Cache statistics tracking

## Performance Analysis

### Benchmarking Results
| Test Case | Response Time | Memory Usage | CPU Usage |
|-----------|---------------|--------------|-----------|
| Single Query | 0.5ms | 10MB | 5% |
| 100 concurrent | 1.2ms | 50MB | 25% |
| 1000 concurrent | 2.5ms | 200MB | 60% |
| With SSL | +1ms | +20MB | +10% |

### Memory Usage
- Base memory: 50MB
- Per connection: ~100KB
- Cache size: Configurable
- Peak usage patterns

### CPU Utilization
- Single core performance
- Multi-core scaling
- Thread pool impact
- System call overhead

### Network Performance
- Connection handling capacity
- Network buffer optimization
- Timeout handling
- Keep-alive connections

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Linux environment (tested on Ubuntu 20.04+)
- 2GB RAM minimum (4GB recommended)
- Network connectivity

### Installation Steps
```bash
# Clone repository
git clone <repository-url>
cd algorithmic_S

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Prepare directories
mkdir -p data logs ssl benchmark_results

# Download test data
curl -L "https://www.dropbox.com/s/vx9bvgx3scl5qn4/200k.txt?dl=1" -o data/200k.txt

# Make scripts executable
chmod +x server.py client.py load_test.py
```

### Development Tools
- pytest for testing
- black for code formatting
- mypy for type checking
- flake8 for linting

### Code Style Guidelines
- PEP 8 compliance
- Type hints required
- Docstrings for all functions
- Maximum line length: 79 characters

## Testing Strategy

### Unit Tests
```bash
# Run all tests
pytest test_server.py

# Run with coverage
pytest --cov=. test_server.py
```

### Integration Tests
- Server-client communication
- SSL handshake
- File monitoring
- Cache behavior

### Performance Tests
```bash
# Basic load test
./load_test.py

# Advanced load test
./load_test.py --max-clients 100 --duration 30 --step 10
```

### Test Data Generation
- Random string generation
- Edge case creation
- Large file handling
- Invalid input testing

## Deployment Guide

### System Service Setup
```bash
sudo cp string_search.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable string_search
sudo systemctl start string_search
```

### Cloud Deployment
- AWS EC2 setup
- Google Cloud deployment
- Azure configuration
- Load balancer setup

### Docker Support
- Dockerfile provided
- Docker Compose configuration
- Container optimization
- Resource limits

### Monitoring Setup
```bash
# Check service status
sudo systemctl status string_search

# Monitor logs
tail -f logs/server.log

# View metrics
./monitor.py
```

## Security Considerations

### Security Measures
- Input validation
- Buffer overflow protection
- Rate limiting
- SSL/TLS encryption

### Known Limitations
- Maximum file size
- Connection limits
- Memory constraints
- CPU bottlenecks

### Security Best Practices
- Regular updates
- SSL certificate rotation
- Access control
- Log monitoring

### Penetration Testing
- SQL injection prevention
- DoS protection
- Memory leak prevention
- Error handling security

## Author

**Phinehas Macharia**
- Email: walburphinehas78@gmail.com
- GitHub: [phines-macharia](https://github.com/phines-macharia)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with Python's robust standard library
- Inspired by high-performance server architectures
- Thanks to all contributors and testers

---

## System Architecture

![String Search Server Architecture](docs/images/string_search_architecture.png)

*System Architecture Diagram - © 2025 Phinehas Macharia (walburphinehas78@gmail.com)*

### Component Description

1. **Client Layer**
   - Multiple clients connecting simultaneously
   - Sends search queries
   - Receives responses

2. **Security Layer**
   - SSL/TLS encryption
   - Rate limiting
   - Input validation

3. **Thread Pool**
   - Manages concurrent connections
   - Distributes workload
   - Handles request processing

4. **Memory Management**
   - LRU Cache for frequent queries
   - In-memory dataset for O(1) lookups
   - Efficient memory allocation

5. **Storage Layer**
   - Data file (200k.txt)
   - Log files
   - Configuration files

# Data Directory

This directory contains the search data files:

- `200k.txt`: Main data file containing search strings
- Test files generated during testing

## File Format

Each line in the data files should:
- Be a complete search string
- End with a newline character
- Not contain partial matches

Example format:
```
7;0;6;28;0;23;5;0;
1;0;6;16;0;19;3;0;
18;0;21;26;0;17;3;0;
20;0;1;11;0;12;5;0;
```

## Notes

- Files are read in text mode
- Lines are stripped of whitespace
- Empty lines are ignored
- Files can be updated while server is running if reread_on_query is enabled