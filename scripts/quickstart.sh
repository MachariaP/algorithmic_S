#!/bin/bash

# Quick Start Script for String Search Server

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}String Search Server Quick Start${NC}"
echo "================================"

# 1. Check Python version
echo -e "\n${GREEN}1. Checking Python version...${NC}"
python3 --version

# 2. Create virtual environment
echo -e "\n${GREEN}2. Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
echo -e "\n${GREEN}3. Installing dependencies...${NC}"
pip install -r requirements.txt

# 4. Generate SSL certificates
echo -e "\n${GREEN}4. Generating SSL certificates...${NC}"
./scripts/generate_cert.sh

# 5. Run tests
echo -e "\n${GREEN}5. Running tests...${NC}"
pytest tests/

# 6. Start server
echo -e "\n${GREEN}6. Starting server...${NC}"
./server.py &
SERVER_PID=$!

# 7. Run quick test
echo -e "\n${GREEN}7. Testing server...${NC}"
sleep 2  # Wait for server to start
./client.py --query "test_string"

# 8. Run benchmark
echo -e "\n${GREEN}8. Running quick benchmark...${NC}"
./client.py --benchmark "test_string" --iterations 100

# Clean up
kill $SERVER_PID

echo -e "\n${GREEN}Quick start complete!${NC}"
echo "Server is ready to use."
echo "Run './server.py' to start the server"
echo "Run './client.py --help' for client options" 