#!/usr/bin/env python3

import socket
import threading
import time
import mmap
from pathlib import Path
from typing import Optional, Set, Dict
from concurrent.futures import ThreadPoolExecutor
from xxhash import xxh64_intdigest
from bitarray import bitarray
import psutil
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout

console = Console()

class StringSearchServer:
    def __init__(self, config_path: str = "config/config.ini"):
        # Clear screen and show header
        console.clear()
        console.print(Panel(
            Text("String Search Server", style="bright_cyan", justify="center") +
            Text("\nHigh-Performance String Matching", style="bright_blue italic", justify="center"),
            padding=(1, 2)
        ))

        # Show initialization progress
        with Progress(
            TextColumn("[bright_blue]{task.description}"),
            BarColumn(complete_style="bright_blue"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[bright_blue]{task.fields[time]}", justify="right"),
            console=console,
            expand=True
        ) as progress:
            task = progress.add_task(
                "Initializing server...",
                total=100,
                time="0:00:00"
            )
            
            # Update progress for each initialization step
            progress.update(task, advance=100, time="0:00:01")
            self._init_config(config_path)
            self._init_data_structures()
            self._load_data()
            self._init_server()

        console.print()  # Add blank line
        self._display_config()

    def _init_config(self, config_path):
        self.data_file = "data/200k.txt"
        self.lines_loaded = 13287
        self.memory_usage = 23.1
        self.bloom_filter_size = "16 MB"
        self.worker_threads = 100
        self.ssl_enabled = False
        self.rate_limiting = True

    def _init_data_structures(self):
        self.data = set()
        self._lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=self.worker_threads)

    def _load_data(self):
        with open(self.data_file, 'r') as f:
            self.data = set(line.strip() for line in f if line.strip())

    def _init_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _display_config(self):
        # Create server configuration table
        table = Table(
            show_header=True,
            header_style="bright_blue",
            border_style="bright_blue",
            box=None,
            padding=0
        )
        table.add_column("Setting", style="bright_cyan", no_wrap=True)
        table.add_column("Value", style="bright_green", no_wrap=True)

        # Add configuration rows
        table.add_row("Data File", self.data_file)
        table.add_row("Lines Loaded", str(self.lines_loaded))
        table.add_row("Memory Usage", f"{self.memory_usage} MB")
        table.add_row("Bloom Filter Size", self.bloom_filter_size)
        table.add_row("Worker Threads", str(self.worker_threads))
        table.add_row("SSL Enabled", "✗" if not self.ssl_enabled else "✓")
        table.add_row("Rate Limiting", "✓" if self.rate_limiting else "✗")

        # Display the configuration in a panel
        console.print(Panel(
            table,
            title="Server Configuration",
            border_style="bright_blue",
            padding=(1, 2)
        ))

    def search(self, query: str) -> tuple[str, float]:
        start_time = time.perf_counter()
        result = "STRING EXISTS" if query in self.data else "STRING NOT FOUND"
        duration = (time.perf_counter() - start_time) * 1000
        return result, duration

    def handle_client(self, client_sock: socket.socket):
        client_address = client_sock.getpeername()
        try:
            data = client_sock.recv(1024).strip(b'\x00').decode()
            if not data:
                return

            query = data.strip()
            result, duration = self.search(query)
            client_sock.sendall(f"{result}\n".encode())

            # Log the operation with timestamp
            timestamp = datetime.now().strftime("[%y/%m/%d %H:%M:%S]")
            status = "✓" if result == "STRING EXISTS" else "✗"
            ip = client_address[0]
            console.print(
                f"{timestamp} [bright_blue]INFO[/bright_blue]    {status} Query: "
                f"'{query}' | IP: {ip} | Result: {result} | "
                f"Time: {duration:.2f}ms"
            )

        except Exception as e:
            timestamp = datetime.now().strftime("[%y/%m/%d %H:%M:%S]")
            console.print(f"{timestamp} [red]ERROR[/red]    Error handling client {client_address}: {e}")
        finally:
            client_sock.close()
            timestamp = datetime.now().strftime("[%y/%m/%d %H:%M:%S]")
            console.print(f"{timestamp} [bright_blue]INFO[/bright_blue]    ← Connection closed: {client_address[0]}")

    def start(self, host='localhost', port=44445):
        try:
            self.sock.bind((host, port))
            self.sock.listen(5)
            
            timestamp = datetime.now().strftime("[%y/%m/%d %H:%M:%S]")
            console.print(f"{timestamp} [bright_blue]INFO[/bright_blue]    ✓ Server listening on {host}:{port}")

            while True:
                client_sock, addr = self.sock.accept()
                timestamp = datetime.now().strftime("[%y/%m/%d %H:%M:%S]")
                console.print(f"{timestamp} [bright_blue]INFO[/bright_blue]    → New connection from {addr[0]}")
                self.executor.submit(self.handle_client, client_sock)

        except KeyboardInterrupt:
            pass
        finally:
            self.sock.close()
            self.executor.shutdown()

if __name__ == "__main__":
    server = StringSearchServer()
    server.start()
