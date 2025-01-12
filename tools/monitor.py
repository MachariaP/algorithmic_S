#!/usr/bin/env python3

"""Server monitoring tool"""

import time
import argparse
from rich.live import Live
from rich.table import Table
from rich.console import Console
import socket
import json

console = Console()

def get_metrics(host: str = 'localhost', port: int = 44445) -> dict:
    """Get server metrics"""
    with socket.create_connection((host, port)) as sock:
        sock.sendall(b"METRICS\n")
        data = sock.recv(1024).decode()
        return json.loads(data)

def create_metrics_table(metrics: dict) -> Table:
    """Create metrics display table"""
    table = Table(title="Server Metrics")
    table.add_column("Metric")
    table.add_column("Value")
    
    table.add_row("Average Response Time", f"{metrics['avg_response_time']:.2f}ms")
    table.add_row("Requests/Second", f"{metrics['requests_per_second']:.1f}")
    table.add_row("Memory Usage", f"{metrics['memory_usage_mb']:.1f}MB")
    table.add_row("CPU Usage", f"{metrics['cpu_usage_percent']:.1f}%")
    
    return table

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Server Monitoring Tool")
    parser.add_argument("--host", default="localhost", help="Server hostname")
    parser.add_argument("--port", type=int, default=44445, help="Server port")
    parser.add_argument("--interval", type=float, default=1.0, help="Update interval")
    
    args = parser.parse_args()
    
    with Live(console=console, refresh_per_second=4) as live:
        while True:
            try:
                metrics = get_metrics(args.host, args.port)
                table = create_metrics_table(metrics)
                live.update(table)
                time.sleep(args.interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                break

if __name__ == "__main__":
    main() 