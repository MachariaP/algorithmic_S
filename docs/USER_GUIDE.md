# String Search Server - User Guide

## Quick Start
```bash
# Install from pip
pip install string-search-server

# Start the server
search-server --config /path/to/config.ini

# Use the client
search-client --query "your search string"
```

## Installation

### Method 1: Using pip
```bash
pip install string-search-server
```

### Method 2: From source
```bash
git clone https://github.com/yourusername/string-search-server.git
cd string-search-server
./scripts/install.sh
```

## Configuration

### Server Configuration
1. Create a config file:
```ini
[DEFAULT]
linuxpath = /path/to/data/file.txt
reread_on_query = false
ssl_enabled = true
```

2. Set environment variables (optional):
```bash
export SEARCH_SERVER_HOST=0.0.0.0
export SEARCH_SERVER_PORT=44445
```

### Client Configuration
```bash
# Basic usage
search-client --query "search string"

# Advanced options
search-client --host remote.server --port 44445 --ssl
```

## Usage Examples

### Basic Search
```bash
# Single search
search-client --query "test_string"

# Batch search from file
search-client --file queries.txt

# Benchmark mode
search-client --benchmark "test_string" --iterations 1000
```

### Advanced Features
1. SSL Authentication
2. Rate Limiting
3. Performance Monitoring
4. Load Testing

## Troubleshooting
Common issues and solutions... 