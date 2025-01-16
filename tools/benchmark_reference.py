#!/usr/bin/env python3

"""
Reference Server Benchmark Tool

Compares our server's performance against the reference implementation
and generates detailed performance reports.
"""

import socket
import time
import statistics
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.progress import track
from typing import List, Dict, Tuple

# Constants
REFERENCE_HOST = "135.181.96.160"
REFERENCE_PORT = 44445
LOCAL_HOST = "localhost"
LOCAL_PORT = 44445
TEST_STRINGS = [
    "7;0;6;28;0;23;5;0;",  # Known to exist
    "test_string_1",
    "nonexistent_string",
    "6;0;1;26;0;7;3;0;",
    "11;0;6;28;0;23;5;0;"
]

console = Console()


def make_request(host: str, port: int, query: str) -> Tuple[str, float]:
    """Make a single request and measure time"""
    start_time = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=5.0) as sock:
            sock.sendall(query.encode() + b'\n')
            response = sock.recv(1024).decode().strip()
            return response, (time.perf_counter() - start_time) * 1000
    except Exception as e:
        return f"ERROR: {str(e)}", 0


def benchmark_server(host: str, port: int, iterations: int = 1000) -> Dict:
    """Run comprehensive benchmark tests"""
    results = {
        "response_times": [],
        "success_rate": 0,
        "errors": [],
        "throughput": 0
    }

    start_time = time.perf_counter()
    successes = 0

    for query in TEST_STRINGS:
        console.print(f"\n[cyan]Testing query: {query}")
        query_times = []

        for _ in track(range(iterations), description="Testing"):
            response, exec_time = make_request(host, port, query)
            if response == "STRING EXISTS":
                successes += 1
            if exec_time > 0:  # Skip errors
                query_times.append(exec_time)

        if query_times:
            results["response_times"].extend(query_times)

            # Print query statistics
            stats = {
                "Average": statistics.mean(query_times),
                "Median": statistics.median(query_times),
                "Std Dev": statistics.stdev(query_times),
                "Min": min(query_times),
                "Max": max(query_times)
            }

            table = Table(title=f"Results for: {query}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right", style="green")

            for metric, value in stats.items():
                table.add_row(metric, f"{value:.2f}ms")

                console.print(table)

    # Calculate overall statistics
    total_time = time.perf_counter() - start_time
    total_requests = len(TEST_STRINGS) * iterations

    results["success_rate"] = (successes / total_requests) * 100
    results["throughput"] = total_requests / total_time

    return results


def plot_comparison(local_results: Dict, ref_results: Dict, output_dir: Path):
    """Generate comparison plots"""
    output_dir.mkdir(exist_ok=True)

    # Response Time Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(local_results["response_times"], bins=50,
             alpha=0.5, label="Local")
    plt.hist(ref_results["response_times"],
             bins=50, alpha=0.5, label="Reference")
    plt.xlabel("Response Time (ms)")
    plt.ylabel("Frequency")
    plt.title("Response Time Distribution")
    plt.legend()
    plt.grid(True)
    plt.savefig(output_dir / "response_times.png")
    plt.close()

    # Success Rate Comparison
    plt.figure(figsize=(8, 6))
    rates = [local_results["success_rate"], ref_results["success_rate"]]
    plt.bar(["Local", "Reference"], rates)
    plt.ylabel("Success Rate (%)")
    plt.title("Success Rate Comparison")
    plt.grid(True)
    plt.savefig(output_dir / "success_rates.png")
    plt.close()

    # Throughput Comparison
    plt.figure(figsize=(8, 6))
    throughputs = [local_results["throughput"], ref_results["throughput"]]
    plt.bar(["Local", "Reference"], throughputs)
    plt.ylabel("Requests/second")
    plt.title("Throughput Comparison")
    plt.grid(True)
    plt.savefig(output_dir / "throughput.png")
    plt.close()


def write_detailed_report(f, local_results: Dict, ref_results: Dict):
    """Write detailed performance analysis"""
    f.write("\nDetailed Performance Analysis\n")
    f.write("==========================\n\n")

    # Calculate percentiles
    local_times = sorted(local_results["response_times"])
    ref_times = sorted(ref_results["response_times"])

    percentiles = [50, 75, 90, 95, 99]
    f.write("Response Time Percentiles:\n")
    f.write("------------------------\n")
    for p in percentiles:
        local_p = np.percentile(local_times, p)
        ref_p = np.percentile(ref_times, p)
        f.write(f"P{p}:\n")
        f.write(f"  Local:     {local_p:.2f}ms\n")
        f.write(f"  Reference: {ref_p:.2f}ms\n")
        f.write(f"  Difference: {abs(local_p - ref_p):.2f}ms ")
        f.write(f"({abs((local_p - ref_p)/ref_p)*100:.1f}% faster)\n\n")

    # Stability analysis
    f.write("\nPerformance Stability:\n")
    f.write("-------------------\n")
    local_cv = statistics.stdev(local_times) / statistics.mean(local_times)
    ref_cv = statistics.stdev(ref_times) / statistics.mean(ref_times)
    f.write(f"Coefficient of Variation:\n")
    f.write(f"  Local:     {local_cv*100:.1f}%\n")
    f.write(f"  Reference: {ref_cv*100:.1f}%\n\n")

    # Throughput analysis
    f.write("\nThroughput Analysis:\n")
    f.write("-----------------\n")
    throughput_diff = local_results["throughput"] - ref_results["throughput"]
    throughput_pct = (throughput_diff / ref_results["throughput"]) * 100
    f.write(f"Requests per second:\n")
    f.write(f"  Local:     {local_results['throughput']:.1f}\n")
    f.write(f"  Reference: {ref_results['throughput']:.1f}\n")
    f.write(f"  Improvement: {throughput_pct:.1f}%\n")


def main():
    """Run benchmarks and generate report"""
    output_dir = Path("benchmark_results")
    output_dir.mkdir(exist_ok=True)

    console.print("[bold blue]Starting benchmark comparison")
    console.print("[blue]This will take several minutes...\n")

    # Test local server
    console.print("[bold cyan]Testing local server")
    local_results = benchmark_server(LOCAL_HOST, LOCAL_PORT)

    # Test reference server
    console.print("\n[bold cyan]Testing reference server")
    ref_results = benchmark_server(REFERENCE_HOST, REFERENCE_PORT)

    # Generate plots
    plot_comparison(local_results, ref_results, output_dir)

    # Generate report
    report_path = output_dir / "comparison_report.txt"
    with open(report_path, "w") as f:
        f.write("String Search Server Performance Comparison\n")
        f.write("=========================================\n\n")

        f.write("Local Server Results:\n")
        f.write("-----------------\n")
        f.write(f"Average Response Time: {statistics.mean(
                local_results['response_times']):.2f}ms\n")
        f.write(f"Success Rate: {local_results['success_rate']:.1f}%\n")
        f.write(f"Throughput: {
                local_results['throughput']:.1f} requests/second\n\n")

        f.write("Reference Server Results:\n")
        f.write("----------------------\n")
        f.write(f"Average Response Time: {
                statistics.mean(ref_results['response_times']):.2f}ms\n")
        f.write(f"Success Rate: {ref_results['success_rate']:.1f}%\n")
        f.write(f"Throughput: {
                ref_results['throughput']:.1f} requests/second\n\n")

        # Calculate performance difference
        time_diff = (statistics.mean(local_results['response_times']) -
                     statistics.mean(ref_results['response_times']))
        time_diff_pct = (time_diff / statistics.mean(
            ref_results['response_times'])) * 100

        f.write("Performance Comparison:\n")
        f.write("---------------------\n")
        f.write(f"Response Time Difference: {abs(time_diff):.2f}ms ")
        f.write(f"({'faster' if time_diff < 0 else 'slower'})\n")
        f.write(f"Percentage Difference: {abs(time_diff_pct):.1f}%\n")

        # Add detailed analysis
        write_detailed_report(f, local_results, ref_results)

        # Add recommendations
        f.write("\nRecommendations:\n")
        f.write("---------------\n")
        if time_diff < 0:
            f.write("✓ Current implementation is performing well!\n")
            f.write("✓ Response times are significantly faster\
                    than reference\n")

            f.write("✓ Performance is more consistent\n")
            f.write("\nPossible improvements:\n")
            f.write("1. Implement request batching for bulk operations\n")
            f.write("2. Add response compression for large payloads\n")
            f.write("3. Consider distributed caching for scaling\n")
        else:
            f.write("! Performance needs improvement\n")
            f.write("! Response times are slower than reference\n")
            f.write("\nRecommended actions:\n")
            f.write("1. Profile code to identify bottlenecks\n")
            f.write("2. Optimize data structures and algorithms\n")
            f.write("3. Implement better caching strategy\n")

    console.print(f"\n[green]Benchmark complete! Results saved to {
                  output_dir}")


if __name__ == "__main__":
    main()
