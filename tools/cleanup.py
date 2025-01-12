#!/usr/bin/env python3

"""Cleanup script for String Search Server"""

import os
import subprocess
from pathlib import Path
from rich.console import Console

console = Console()

def cleanup():
    """Clean up server and temporary files"""
    # Stop server
    console.print("[yellow]Stopping server...[/yellow]")
    subprocess.run("pkill -f server.py", shell=True, check=False)
    
    # Remove socket if exists
    try:
        os.unlink("/tmp/string_search.sock")
    except FileNotFoundError:
        pass
    
    # Clear logs
    log_dir = Path("logs")
    if log_dir.exists():
        for log in log_dir.glob("*.log"):
            log.unlink()
    
    console.print("[green]Cleanup complete![/green]")

if __name__ == "__main__":
    cleanup() 