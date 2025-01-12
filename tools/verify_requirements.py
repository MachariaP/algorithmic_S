#!/usr/bin/env python3

"""Requirements Verification Tool"""

import socket
import time
import statistics
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import track
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import configparser

console = Console()

# Test configuration
TEST_QUERY = "7;0;6;28;0;23;5;0;"  # Known existing string
HOST = 'localhost'
PORT = 44445

def make_request(query: str, reread: bool = False) -> Tuple[str, float]:
    """Make a single request and measure time"""
    start_time = time.perf_counter()
    try:
        with socket.create_connection((HOST, PORT), timeout=5.0) as sock:
            # Update config if needed
            if reread:
                sock.sendall(b"SET REREAD_ON_QUERY TRUE\n")
                sock.recv(1024)  # Get response
            else:
                sock.sendall(b"SET REREAD_ON_QUERY FALSE\n")
                sock.recv(1024)  # Get response
                
            # Send actual query
            sock.sendall(query.encode() + b'\n')
            response = sock.recv(1024).decode().strip()
            exec_time = (time.perf_counter() - start_time) * 1000
            return response, exec_time
    except Exception as e:
        return f"ERROR: {str(e)}", 0

def generate_test_file(size: int) -> Path:
    """Generate test file of given size"""
    path = Path(f"test_data_{size}.txt")
    
    with open(path, 'w') as f:
        # Write known test string
        f.write(f"{TEST_QUERY}\n")
        
        # Fill rest with random strings
        for i in range(size - 1):
            f.write(f"test_string_{i};{i}\n")
            
    return path

def test_reread_performance(reread: bool, file_sizes: List[int]) -> Dict[int, float]:
    """Test performance with different file sizes"""
    results = {}
    
    for size in file_sizes:
        console.print(f"\nTesting file size: {size:,} lines")
        
        # Generate test file
        test_file = generate_test_file(size)
        
        # Update server config
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'linuxpath': str(test_file.absolute()),
            'REREAD_ON_QUERY': str(reread)
        }
        with open('config.ini', 'w') as f:
            config.write(f)
            
        # Restart server to load new config
        console.print("[yellow]Please restart server with new config...")
        input("Press Enter when ready...")
        
        times = []
        # Test with 1000 queries
        for _ in track(range(1000), description="Testing"):
            response, exec_time = make_request(TEST_QUERY, reread)
            if exec_time > 0:  # Skip errors
                times.append(exec_time)
                
        if times:
            results[size] = statistics.mean(times)
        else:
            console.print("[red]No valid results for this file size!")
            
        # Cleanup
        test_file.unlink()
        
    return results

def main():
    """Verify all requirements"""
    console.print("[bold blue]Verifying Server Requirements")
    
    # Test file sizes
    sizes = [10000, 50000, 100000, 250000, 500000, 1000000]
    
    # Test REREAD_ON_QUERY=False
    console.print("\n[cyan]Testing with REREAD_ON_QUERY=False")
    normal_results = test_reread_performance(False, sizes)
    
    # Test REREAD_ON_QUERY=True
    console.print("\n[cyan]Testing with REREAD_ON_QUERY=True")
    reread_results = test_reread_performance(True, sizes)
    
    # Create results table
    table = Table(title="Performance Requirements")
    table.add_column("File Size", style="cyan")
    table.add_column("Normal Mode", style="green")
    table.add_column("Reread Mode", style="yellow")
    table.add_column("Requirements Met", style="bold green")
    
    for size in sizes:
        normal_time = normal_results.get(size, float('inf'))
        reread_time = reread_results.get(size, float('inf'))
        meets_req = normal_time <= 0.5 and reread_time <= 40.0
        
        table.add_row(
            f"{size:,}",
            f"{normal_time:.2f}ms",
            f"{reread_time:.2f}ms",
            "✓" if meets_req else "✗"
        )
    
    console.print(table)
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(sizes, [normal_results.get(s, 0) for s in sizes], 'g-', label='Normal Mode')
    plt.plot(sizes, [reread_results.get(s, 0) for s in sizes], 'b-', label='Reread Mode')
    plt.axhline(y=0.5, color='r', linestyle='--', label='Normal Requirement (0.5ms)')
    plt.axhline(y=40, color='y', linestyle='--', label='Reread Requirement (40ms)')
    plt.xlabel("File Size (lines)")
    plt.ylabel("Response Time (ms)")
    plt.title("Performance vs File Size")
    plt.legend()
    plt.grid(True)
    plt.savefig("requirements_verification.png")
    
    console.print("\n[green]Requirements verification complete!")

if __name__ == "__main__":
    main() 