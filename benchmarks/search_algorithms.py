#!/usr/bin/env python3

"""
Search Algorithm Benchmarks

This module compares different string search algorithms:
1. Hash Table + Bloom Filter (Current Implementation)
2. Simple Set Lookup
3. Linear Search
4. Binary Search (on sorted data)
5. Suffix Array
6. Aho-Corasick Algorithm
7. Boyer-Moore Algorithm
"""

import time
import mmap
import random
from pathlib import Path
from typing import List, Callable, Dict, Set
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from xxhash import xxh64_intdigest
from bitarray import bitarray
from ahocorasick import Automaton
from suffix_array import SuffixArray


def generate_test_data(size: int) -> tuple[List[str], List[str]]:
    """Generate test data and queries"""
    data = [f"{random.randint(0, 20)};{random.randint(0, 1)};{random.randint(1, 30)}" 
            for _ in range(size)]
    queries = random.sample(data, min(1000, size // 10))  # 10% of data for queries
    return data, queries


class SearchBenchmark:
    """Benchmark different search algorithms"""
    
    def __init__(self, data: List[str], queries: List[str]):
        self.data = data
        self.queries = queries
        self.results: Dict[str, List[float]] = defaultdict(list)
    
    def benchmark_hash_bloom(self) -> None:
        """Benchmark Hash Table + Bloom Filter"""
        # Create bloom filter
        bloom = bitarray(2 ** 24)
        bloom.setall(0)
        
        # Create hash table
        hash_table = {}
        for line in self.data:
            hash_val = xxh64_intdigest(line.encode())
            hash_table[hash_val] = line
            bloom[hash_val % len(bloom)] = 1
        
        # Benchmark searches
        times = []
        for query in self.queries:
            start = time.perf_counter()
            hash_val = xxh64_intdigest(query.encode())
            if bloom[hash_val % len(bloom)]:
                _ = hash_val in hash_table
            times.append((time.perf_counter() - start) * 1000)
        
        self.results["Hash + Bloom"] = times
    
    def benchmark_set_lookup(self) -> None:
        """Benchmark Simple Set Lookup"""
        data_set = set(self.data)
        times = []
        for query in self.queries:
            start = time.perf_counter()
            _ = query in data_set
            times.append((time.perf_counter() - start) * 1000)
        
        self.results["Set Lookup"] = times
    
    def benchmark_linear_search(self) -> None:
        """Benchmark Linear Search"""
        times = []
        for query in self.queries:
            start = time.perf_counter()
            _ = query in self.data
            times.append((time.perf_counter() - start) * 1000)
        
        self.results["Linear Search"] = times
    
    def benchmark_binary_search(self) -> None:
        """Benchmark Binary Search"""
        sorted_data = sorted(self.data)
        times = []
        for query in self.queries:
            start = time.perf_counter()
            _ = binary_search(sorted_data, query)
            times.append((time.perf_counter() - start) * 1000)
        
        self.results["Binary Search"] = times
    
    def benchmark_suffix_array(self) -> None:
        """Benchmark Suffix Array"""
        sa = SuffixArray('\n'.join(self.data))
        times = []
        for query in self.queries:
            start = time.perf_counter()
            _ = sa.search(query)
            times.append((time.perf_counter() - start) * 1000)
        
        self.results["Suffix Array"] = times
    
    def benchmark_aho_corasick(self) -> None:
        """Benchmark Aho-Corasick Algorithm"""
        # Build automaton
        A = Automaton()
        for word in self.data:
            A.add_word(word, word)
        A.make_automaton()
        
        times = []
        for query in self.queries:
            start = time.perf_counter()
            _ = query in A
            times.append((time.perf_counter() - start) * 1000)
        
        self.results["Aho-Corasick"] = times
    
    def run_all_benchmarks(self) -> None:
        """Run all benchmarks"""
        self.benchmark_hash_bloom()
        self.benchmark_set_lookup()
        self.benchmark_linear_search()
        self.benchmark_binary_search()
        self.benchmark_suffix_array()
        self.benchmark_aho_corasick()
    
    def plot_results(self, output_file: str = "benchmarks/results.png") -> None:
        """Plot benchmark results"""
        plt.figure(figsize=(12, 6))
        
        # Create box plots
        data = [times for times in self.results.values()]
        labels = list(self.results.keys())
        
        plt.boxplot(data, labels=labels)
        plt.yscale('log')
        plt.ylabel('Search Time (ms)')
        plt.title('Search Algorithm Performance Comparison')
        plt.xticks(rotation=45)
        plt.grid(True)
        
        # Save plot
        plt.tight_layout()
        plt.savefig(output_file)
    
    def print_statistics(self) -> None:
        """Print statistical summary"""
        print("\nSearch Algorithm Performance Summary")
        print("=" * 50)
        print(f"{'Algorithm':<20} {'Avg (ms)':<10} {'Min (ms)':<10} {'Max (ms)':<10}")
        print("-" * 50)
        
        for algo, times in self.results.items():
            avg = np.mean(times)
            min_time = np.min(times)
            max_time = np.max(times)
            print(f"{algo:<20} {avg:<10.3f} {min_time:<10.3f} {max_time:<10.3f}")


def binary_search(arr: List[str], target: str) -> bool:
    """Binary search implementation"""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return True
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return False


if __name__ == "__main__":
    # Test with different data sizes
    sizes = [10000, 50000, 100000, 250000, 500000]
    
    for size in sizes:
        print(f"\nBenchmarking with {size} lines...")
        data, queries = generate_test_data(size)
        
        benchmark = SearchBenchmark(data, queries)
        benchmark.run_all_benchmarks()
        benchmark.print_statistics()
        benchmark.plot_results(f"benchmarks/results_{size}.png") 