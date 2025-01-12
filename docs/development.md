# Development Guide

## Setup Development Environment

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Configure pre-commit hooks:
```bash
pre-commit install
```

## Code Style

- Follow PEP 8 and PEP 20
- Use type hints
- Write docstrings for all functions/classes
- Keep functions focused and small

### Code Formatting
```bash
# Format code
black .

# Check types
mypy .

# Lint code
flake8
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Generate coverage report
pytest --cov=src --cov-report=html
```

### Writing Tests
- Test each feature independently
- Cover edge cases
- Mock external dependencies
- Test performance requirements

## Debugging

### Server Debugging
```bash
# Run server in debug mode
DEBUG=1 ./server.py

# Check logs
tail -f logs/server.log
```

### Performance Profiling
```bash
# Profile server
python -m cProfile -o profile.stats server.py

# Analyze profile
python tools/analyze_profile.py
```

## Documentation

### Building Docs
```bash
# Generate API docs
sphinx-build -b html docs/source docs/build
```

### README Updates
Keep README.md updated with:
- New features
- Changed configurations
- Updated examples 