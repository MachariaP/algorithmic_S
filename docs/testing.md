# Testing Guide

## Overview
This guide covers different types of tests and how to run them effectively.

## Unit Tests

### Basic Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_server.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Test Categories
1. Server Functionality (`test_server.py`)
   - Basic connectivity
   - String matching
   - Error handling

2. Performance Tests (`test_performance.py`)
   - Response times
   - Concurrent connections
   - Memory usage

3. Security Tests (`test_security.py`)
   - SSL functionality
   - Rate limiting
   - Input validation

## Performance Testing

### Benchmark Tool
```bash
# Run comprehensive benchmarks
python tools/benchmark.py

# Test specific file size
python tools/benchmark.py --size 100000

# Test concurrent load
python tools/benchmark.py --concurrent 1000
```

### Reference Server Comparison
```bash
# Compare with reference implementation
python tools/compare_performance.py

# Compare specific scenarios
python tools/compare_performance.py --scenario reread
```

### Metrics Tested
- Response time (normal mode)
- Response time (reread mode)
- Memory usage
- CPU usage
- Network throughput

## Load Testing

### Concurrent Connections
```bash
# Test with increasing load
python tools/load_test.py --start 100 --end 10000 --step 100
```

### Long-running Tests
```bash
# Run 24-hour stability test
python tools/stability_test.py --duration 24h
```

## Test Data

### Generate Test Data
```bash
# Create test data
python tools/create_test_data.py

# Verify data format
python tools/verify_format.py
```

### Test String Examples
```
7;0;6;28;0;23;5;0;
1;0;6;16;0;19;3;0;
18;0;21;26;0;17;3;0;
20;0;1;11;0;12;5;0;
``` 