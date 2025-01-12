#!/usr/bin/env python3

"""Data verification tool"""

import sys
from pathlib import Path

def verify_data(file_path: str) -> None:
    """Verify data file contents"""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        print(f"Total lines: {len(lines)}")
        
        # Check for test string
        test_string = "7;0;6;28;0;23;5;0;"
        found = test_string in [line.strip() for line in lines]
        print(f"Test string '{test_string}' found: {found}")
        
        # Show first few lines
        print("\nFirst 5 lines:")
        for line in lines[:5]:
            print(line.strip())
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    data_path = "data/200k.txt"
    verify_data(data_path) 