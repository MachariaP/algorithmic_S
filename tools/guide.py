#!/usr/bin/env python3

"""
Interactive Guide for String Search Server

This script guides users through:
1. Setup and installation
2. Running tests
3. Performance benchmarking
4. Common operations
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
import time

console = Console()


def run_command(cmd: str, check: bool = True) -> bool:
    """Run shell command and return success"""
    try:
        console.print(f"\n[cyan]Running:[/cyan] {cmd}")
        subprocess.run(cmd, shell=True, check=check)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running command:[/red] {e}")
        return False


def setup_environment():
    """Setup the environment"""
    console.print(Panel.fit("Setting up environment", style="blue"))

    # Install dependencies
    console.print("\n[yellow]Installing dependencies...[/yellow]")
    run_command("pip install -r requirements.txt")

    # Create directories
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)


def create_test_data():
    """Create and verify test data"""
    console.print(Panel.fit("Creating test data", style="blue"))

    # Create test data
    run_command("python tools/create_test_data.py")

    # Verify format
    run_command("python tools/verify_format.py")


def run_tests():
    """Run unit tests"""
    console.print(Panel.fit("Running tests", style="blue"))

    # Run server tests
    console.print("\n[yellow]Running server tests...[/yellow]")
    run_command("python -m pytest tests/test_server.py -v")


def run_benchmark():
    """Run performance benchmark"""
    console.print(Panel.fit("Running benchmark", style="blue"))

    test_string = "7;0;6;28;0;23;5;0;"

    # Run benchmark
    console.print(f"\n[yellow]Running benchmark with '{test_string}'[/yellow]")
    run_command(f"./client.py --benchmark '{test_string}' --iterations 1000")


def stop_server():
    """Stop any running server instances"""
    console.print("\n[yellow]Stopping existing server instances...[/yellow]")
    run_command("pkill -f server.py", check=False)
    # Wait for server to stop
    time.sleep(1)


def start_server():
    """Start the server"""
    console.print("\n[yellow]Starting server...[/yellow]")
    # First stop any existing instances
    stop_server()
    # Start new server
    run_command("./server.py &")
    # Wait for server to start
    time.sleep(2)


def interactive_guide():
    """Interactive guide through all operations"""
    console.print(Panel.fit(
        "Welcome to String Search Server Guide\n"
        "This guide will help you set up and test the server",
        style="green"
    ))

    # Setup
    if Confirm.ask("\nWould you like to set up the environment?"):
        setup_environment()

    # Create test data
    if Confirm.ask("\nWould you like to create test data?"):
        create_test_data()

    # Run tests
    if Confirm.ask("\nWould you like to run the tests?"):
        run_tests()

    # Start server
    if Confirm.ask("\nWould you like to start the server?"):
        start_server()

    # Run benchmark
    if Confirm.ask("\nWould you like to run a benchmark?"):
        run_benchmark()

    console.print(Panel.fit(
        "Guide complete!\n\n"
        "Common commands:\n"
        "- Start server: ./server.py\n"
        "- Interactive client: ./client.py\n"
        "- Run tests: python -m pytest tests/\n"
        "- Create test data: python tools/create_test_data.py",
        style="green"
    ))


def main():
    """Main entry point"""
    try:
        interactive_guide()
    except KeyboardInterrupt:
        console.print("\n[yellow]Guide interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
