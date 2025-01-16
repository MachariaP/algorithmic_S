#!/usr/bin/env python3

"""Check data file content"""

from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)


def check_data():
    """Check data file content"""
    data_path = Path("data/200k.txt")

    if not data_path.exists():
        logging.error("Data file not found!")
        return

    # Read and print first few lines
    print("\nFirst 10 lines of data file:")
    print("-" * 50)
    with open(data_path, 'r') as f:
        for i, line in enumerate(f):
            if i < 10:
                print(f"{i+1}: '{line.strip()}'")
            else:
                break

    # Count total lines
    with open(data_path, 'r') as f:
        total_lines = sum(1 for _ in f)
    print(f"\nTotal lines: {total_lines}")

    # Check for test string
    test_string = "7;0;6;28;0;23;5;0;"
    with open(data_path, 'r') as f:
        found = any(test_string in line for line in f)
    print(f"\nTest string '{test_string}' found: {found}")


if __name__ == "__main__":
    check_data()
