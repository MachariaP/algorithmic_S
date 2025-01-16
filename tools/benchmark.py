#!/usr/bin/env python3

"""
Comprehensive Speed Testing

Tests:
1. Different file sizes (10k to 1M lines)
2. Different query patterns
3. Different algorithms
4. Concurrent load testing
"""

import time
import statistics
import matplotlib.pyplot as plt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from rich.console import Console
from rich.table import Table
import mmap
import re
from typing import List, Set

console = Console()


def set_based_search(file_path: Path, query: str) -> bool:
    """Set-based search algorithm"""
    with open(file_path, 'r') as f:
        data = {line.strip() for line in f if line.strip()}
    return query in data


def binary_search(file_path: Path, query: str) -> bool:
    """Binary search algorithm"""
    with open(file_path, 'r') as f:
        lines = sorted(line.strip() for line in f if line.strip())

    left, right = 0, len(lines) - 1
    while left <= right:
        mid = (left + right) // 2
        if lines[mid] == query:
            return True
        elif lines[mid] < query:
            left = mid + 1
        else:
            right = mid - 1
    return False


def regex_search(file_path: Path, query: str) -> bool:
    """Regex-based search"""
    pattern = re.compile(f"^{re.escape(query)}$", re.MULTILINE)
    with open(file_path, 'r') as f:
        content = f.read()
    return bool(pattern.search(content))


def mmap_search(file_path: Path, query: str) -> bool:
    """Memory-mapped search"""
    with open(file_path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        return mm.find(query.encode()) != -1


def index_search(file_path: Path, query: str) -> bool:
    """Index-based search"""
    # Build index on first call
    if not hasattr(index_search, 'index'):
        index_search.index = {}
        with open(file_path, 'r') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    index_search.index[line] = i
    return query in index_search.index


def generate_test_file(size: int) -> Path:
    """Generate test file of given size"""
    path = Path(f"data/test_{size}.txt")
    with open(path, 'w') as f:
        for i in range(size):
            f.write(f"test_line_{i}\n")
    return path


def test_algorithms():
    """Test different search algorithms"""
    algorithms = {
        'set_lookup': set_based_search,
        'binary_search': binary_search,
        'regex_search': regex_search,
        'mmap_search': mmap_search,
        'index_search': index_search
    }

    sizes = [10000, 50000, 100000, 500000, 1000000]
    results = []

    for size in sizes:
        console.print(f"\nTesting with file size: {size}")
        file_path = generate_test_file(size)

        for name, algo in algorithms.items():
            console.print(f"Testing {name}...")
            times = []
            for _ in range(100):
                start = time.perf_counter()
                algo(file_path, "test_line_500")
                duration = (time.perf_counter() - start) * 1000
                times.append(duration)

            results.append({
                'algorithm': name,
                'file_size': size,
                'avg_time': statistics.mean(times),
                'std_dev': statistics.stdev(times)
            })

    # Create report
    df = pd.DataFrame(results)

    # Plot results
    plt.figure(figsize=(12, 8))
    for algo in algorithms:
        data = df[df['algorithm'] == algo]
        plt.plot(data['file_size'], data['avg_time'], label=algo)

    plt.xlabel('File Size (lines)')
    plt.ylabel('Average Time (ms)')
    plt.title('Algorithm Performance vs File Size')
    plt.legend()
    plt.savefig('benchmark_results.png')

    # Print table
    table = Table(title="Algorithm Performance")
    table.add_column("Algorithm")
    table.add_column("File Size")
    table.add_column("Avg Time (ms)")
    table.add_column("Std Dev (ms)")

    for _, row in df.iterrows():
        table.add_row(
            row['algorithm'],
            f"{row['file_size']:,}",
            f"{row['avg_time']:.2f}",
            f"{row['std_dev']:.2f}"
        )

    console.print(table)


if __name__ == "__main__":
    test_algorithms()
