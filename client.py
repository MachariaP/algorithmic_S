#!/usr/bin/env python3

"""String Search Server Client"""

import socket
import ssl
import argparse
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from src.config.config import Config

console = Console()


def create_header() -> Panel:
    """
    Create header panel for the application.

    Returns:
        Panel: A styled panel containing the header text.
    """
    title = Text("String Search Client", style="bold cyan")
    subtitle = Text("High-Performance String Matching", style="italic blue")
    return Panel(
        f"{title}\n{subtitle}",
        border_style="bright_blue",
        padding=(1, 2)
    )


def create_result_panel(query: str, result: str, timestamp: str,
                        server_time: float) -> Panel:
    """
    Create result panel to display search outcomes.

    Args:
        query (str): The search query.
        result (str): The search result.
        timestamp (str): The timestamp of the search.
        server_time (float): The server time taken to process the query.

    Returns:
        Panel: A styled panel containing the search result.
    """
    content = [
        Text(f"{timestamp} | ", style="dim") +
        Text("Query: ", style="bold white") + Text(f"{query} | ",
                                                   style="cyan") +
        Text("Result: ", style="bold white") + Text(
            result,
            style="green" if result == "STRING EXISTS" else "red"
        ) + Text(f" | Time: {server_time:.2f}ms", style="dim")
    ]
    return Panel(
        "\n".join(str(line) for line in content),
        border_style="bright_blue",
        padding=(0, 1),
        expand=False
    )


def create_stats_table(stats: dict) -> Table:
    """
    Create statistics table for displaying metrics.

    Args:
        stats (Dict[str, int]): A dictionary containing the metrics names
                                and value.

    Returns:
        Table: A styled table containing the metrics.
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    for key, value in stats.items():
        table.add_row(key, str(value))

    return table


def search_string(query: str, host: str = 'localhost', port: int = 44445,
                  use_ssl: bool = False) -> tuple[str, float, float]:
    """
    Send search query to server

    Args:
        query (str): Search query
        host (str): Server hostname
        port (int): Server port
        use_ssl (bool): If True, use SSL for the connection.

    Returns:
        Tuple[str, float, float]: A tuple containing the search result,
                                  total duration in ms, and server response
                                  time in ms.
    """
    start = time.perf_counter()
    sock = socket.create_connection((host, port))

    if use_ssl:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        sock = context.wrap_socket(sock, server_hostname=host)

    try:
        sock.sendall(f"{query}\n".encode())
        response = sock.recv(1024).decode().strip()
        total_duration = (time.perf_counter() - start) * 1000

        # Parse server time from response
        if ";" in response:
            result, server_time = response.split(";")
            server_time = float(server_time)
        else:
            result = response
            server_time = 0.0

        return result, total_duration, server_time
    finally:
        sock.close()


def interactive_mode(host: str, port: int, ssl_enabled: bool):
    """
    Run the client in interactive mode.

    Args:
        host (str): Server hostname
        port (int): Server port
        ssl_enabled (bool): If True, use SSL for the connection.
    """
    # Clear screen
    console.clear()

    # Show minimal header
    console.print(
        Panel(
            Text("String Search Client", style="bold cyan"),
            border_style="bright_blue",
            padding=(0, 1),
            expand=False
        )
    )

    # Show connection info
    console.print(
        Text(
            f"Connected to {host}:{port}" + (" (SSL)" if ssl_enabled else ""),
            style="dim"
        )
    )

    while True:
        try:
            # Get query
            query = Prompt.ask("\nEnter search string")
            if not query:
                continue

            # Show "Searching..." while waiting
            with console.status("Searching..."):
                result, _, server_time = search_string(query, host, port,
                                                       ssl_enabled)

            # Get current timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            # Show result
            console.print(create_result_panel(query, result, timestamp,
                                              server_time))

        except KeyboardInterrupt:
            console.print("\nGoodbye!", style="green")
            break
        except Exception as e:
            console.print(f"Error: {e}", style="red")
            break


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="String Search Client",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", default="localhost", help="Server hostname")
    parser.add_argument("--port", type=int, default=44445, help="Server port")
    parser.add_argument("--ssl", action="store_true", help="Use SSL")

    args = parser.parse_args()
    interactive_mode(args.host, args.port, args.ssl)


if __name__ == "__main__":
    main()
