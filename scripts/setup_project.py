#!/usr/bin/env python3

"""Project structure setup script"""

import os
from pathlib import Path


def create_directory_structure():
    """Create project directory structure"""
    directories = [
        "src/config",
        "src/monitoring",
        "src/security",
        "tests/unit",
        "tests/integration",
        "tools",
        "scripts",
        "config",
        "data",
        "docs",
        "logs",
        "ssl"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Create __init__.py for Python packages
        if directory.startswith(("src", "tests")):
            init_file = Path(directory) / "__init__.py"
            init_file.touch()

    # Create .gitkeep files
    for directory in ["logs", "ssl", "data"]:
        gitkeep = Path(directory) / ".gitkeep"
        gitkeep.touch()


def move_files():
    """Move files to their new locations"""
    moves = {
        "rate_limiter.py": "src/",
        "monitoring.py": "src/",
        "generate_cert.py": "src/security/",
        "generate_ssl.py": "src/security/",
        "test_server.py": "tests/unit/",
        "test_setup.sh": "tests/",
        "pytest.ini": "tests/",
        "benchmark.py": "tools/",
        "benchmark_reference.py": "tools/",
        "load_test.py": "tools/",
        "verify_requirements.py": "tools/",
        "load_balancer.py": "tools/",
        "config.ini": "config/",
        "string_search.service": "config/",
        "install.sh": "scripts/",
        "run_tests.sh": "scripts/",
        "server.log": "logs/"
    }

    for source, dest in moves.items():
        if os.path.exists(source):
            os.rename(source, os.path.join(dest, source))


def main():
    """Set up project structure"""
    create_directory_structure()
    move_files()
    print("Project structure setup complete!")


if __name__ == "__main__":
    main()
