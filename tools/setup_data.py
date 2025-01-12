#!/usr/bin/env python3

"""Data setup and verification tool"""

import sys
import os
from pathlib import Path
import logging
import shutil
import requests

logging.basicConfig(level=logging.INFO)

def download_data() -> None:
    """Download test data if not exists"""
    url = "https://www.dropbox.com/s/vx9bvgx3scl5qn4/200k.txt?dl=1"
    data_path = Path("data/200k.txt")
    
    if not data_path.exists():
        logging.info("Downloading test data...")
        response = requests.get(url)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_bytes(response.content)
        logging.info("Download complete")

def verify_data() -> None:
    """Verify data file contents and format"""
    data_path = Path("data/200k.txt")
    
    if not data_path.exists():
        logging.error("Data file not found!")
        sys.exit(1)
        
    # Read and verify file
    with open(data_path, 'r') as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    logging.info(f"Total lines: {total_lines}")
    
    # Verify format
    test_strings = [
        "7;0;6;28;0;23;5;0;",
        "1;0;6;16;0;19;3;0;",
        "18;0;21;26;0;17;3;0;",
        "20;0;1;11;0;12;5;0;"
    ]
    
    found = []
    for test in test_strings:
        if test in [line.strip() for line in lines]:
            found.append(test)
            
    logging.info(f"Found {len(found)}/{len(test_strings)} test strings")
    
    # Fix file if needed
    if len(found) < len(test_strings):
        logging.warning("Missing test strings, fixing file...")
        backup_path = data_path.with_suffix('.bak')
        shutil.copy(data_path, backup_path)
        
        with open(data_path, 'w') as f:
            # Write test strings first
            for test in test_strings:
                f.write(f"{test}\n")
            # Write original content
            for line in lines:
                if line.strip() not in test_strings:
                    f.write(line)
                    
        logging.info("File fixed and backup created")

def main():
    """Main entry point"""
    try:
        download_data()
        verify_data()
        logging.info("Data setup complete!")
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 