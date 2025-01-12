#!/bin/bash

# Master test script for String Search Server
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# 1. Check prerequisites
log "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || error "Python 3 is required"
command -v pip >/dev/null 2>&1 || error "pip is required"
command -v systemctl >/dev/null 2>&1 || error "systemctl is required"

# 2. Create test environment
log "Setting up test environment..."
TEST_DIR="/tmp/string_search"
sudo rm -rf "$TEST_DIR"  # Clean previous test directory
sudo mkdir -p "$TEST_DIR"/{data,logs,ssl}
sudo chown -R $USER:$USER "$TEST_DIR"  # Change ownership to current user

# 3. Install dependencies
log "Installing dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

# 4. Generate SSL certificates
log "Generating SSL certificates..."
chmod +x generate_ssl.py
./generate_ssl.py -o "$TEST_DIR/ssl" -n localhost || error "Failed to generate SSL certificates"

# 5. Copy files to test directory
log "Copying files..."
cp server.py "$TEST_DIR/"
cp config.ini "$TEST_DIR/"
cp -r data/* "$TEST_DIR/data/"

# 6. Set up service user
log "Setting up service user..."
if ! id -u string_search >/dev/null 2>&1; then
    sudo useradd -r -s /bin/false string_search
fi

# 7. Set permissions
log "Setting permissions..."
sudo chown -R string_search:string_search "$TEST_DIR"
sudo chmod -R 755 "$TEST_DIR"
sudo chmod 644 "$TEST_DIR/config.ini"
sudo chmod 644 "$TEST_DIR/server.py"
sudo chmod -R 755 "$TEST_DIR/ssl"  # Make SSL directory accessible

# 8. Install service
log "Installing systemd service..."
sudo cp string_search.service /etc/systemd/system/
sudo systemctl daemon-reload

# 9. Start service
log "Starting service..."
sudo systemctl stop string_search 2>/dev/null || true  # Stop if running
sudo systemctl start string_search || error "Failed to start service"
sleep 2  # Wait for service to start

# 10. Run unit tests
log "Running unit tests..."
pytest -v tests/ || error "Unit tests failed"

# 11. Run benchmark tests
log "Running benchmark tests..."
chmod +x benchmark.py
./benchmark.py || error "Benchmark tests failed"

# 12. Run load tests
log "Running load tests..."
chmod +x load_test.py
./load_test.py -c 50 -r 100 -b 5 -d 0.2 || error "Load tests failed"

# 13. Test basic functionality
log "Testing basic functionality..."
echo "test_string_1" | nc localhost 44445 | grep "STRING EXISTS" || error "Basic functionality test failed"

# 14. Test SSL connection
log "Testing SSL connection..."
if [ "$(grep -c "USE_SSL = True" config.ini)" -eq 1 ]; then
    echo "test_string_1" | openssl s_client -connect localhost:44445 -CAfile "$TEST_DIR/ssl/server.crt" -quiet || error "SSL test failed"
fi

# 15. Check logs
log "Checking logs..."
if ! sudo test -f "$TEST_DIR/logs/server.out"; then
    error "Log file not found"
fi

# 16. Test cleanup
log "Cleaning up..."
sudo systemctl stop string_search
sudo rm -rf "$TEST_DIR"
deactivate

success "All tests completed successfully!"

# Print summary
echo
echo "Test Summary:"
echo "============="
echo "✓ Environment setup"
echo "✓ SSL certificate generation"
echo "✓ Service installation"
echo "✓ Unit tests"
echo "✓ Benchmark tests"
echo "✓ Load tests"
echo "✓ Basic functionality"
echo "✓ SSL connection (if enabled)"
echo "✓ Log verification"
echo
echo "Check detailed results in:"
echo "- benchmark_results/"
echo "- results/"
echo "- logs/"