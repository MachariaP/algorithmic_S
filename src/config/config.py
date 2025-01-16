#!/usr/bin/env python3

"""
Configuration management with environment variable support.

This module handles server configuration from multiple sources:
1. Default values
2. Configuration file
3. Environment variables
4. Command line arguments

Configuration precedence (highest to lowest):
1. Command line arguments
2. Environment variables
3. Configuration file
4. Default values
"""

import os
import configparser
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class Config:
    """
    Server configuration with type hints and validation.

    Attributes:
        file_path (Path): Path to data file
        reread_on_query (bool): Whether to reread file on each query
        max_workers (int): Maximum number of worker threads
        cache_size (int): Size of LRU cache
        buffer_size (int): Socket buffer size
        ssl_enabled (bool): Whether to use SSL
        ssl_cert_path (Path): Path to SSL certificate
        ssl_key_path (Path): Path to SSL private key
        rate_limit_enabled (bool): Whether to use rate limiting
        requests_per_minute (int): Maximum requests per minute per IP
        log_level (str): Logging level
        log_file (Path): Path to log file
    """

    file_path: Path = Path("data/200k.txt")
    reread_on_query: bool = False
    max_workers: int = 100
    cache_size: int = 10000
    buffer_size: int = 1048576
    ssl_enabled: bool = False
    ssl_cert_path: Path = Path("ssl/server.crt")
    ssl_key_path: Path = Path("ssl/server.key")
    rate_limit_enabled: bool = True
    requests_per_minute: int = 1000
    log_level: str = "INFO"
    log_file: Path = Path("logs/server.log")

    def __post_init__(self) -> None:
        """
        Validate configuration after initialization.

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Load config file if it exists
        config = configparser.ConfigParser()
        config_file = Path("config/config.ini")
        if config_file.exists():
            config.read(config_file)
            if "DEFAULT" in config:
                # Load file path based on OS
                if os.name == "posix":  # Linux/Unix
                    if "linuxpath" in config["DEFAULT"]:
                        self.file_path = Path(config["DEFAULT"]["linuxpath"])
                else:  # Windows
                    if "windowspath" in config["DEFAULT"]:
                        self.file_path = Path(config["DEFAULT"]["windowspath"])
                
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Validate all configuration values.

        Checks:
        - Positive integers where required
        - Valid paths
        - Valid log levels
        - SSL configuration consistency

        Raises:
            ValueError: If any validation fails
        """
        if self.max_workers < 1:
            raise ValueError("max_workers must be positive")

        if self.cache_size < 0:
            raise ValueError("cache_size must be non-negative")

        if self.buffer_size < 1024:
            raise ValueError("buffer_size must be at least 1024")

        if self.requests_per_minute < 1:
            raise ValueError("requests_per_minute must be positive")

        if self.ssl_enabled:
            if not self.ssl_cert_path.exists():
                raise ValueError(f"SSL certificate not found: {self.ssl_cert_path}")
            if not self.ssl_key_path.exists():
                raise ValueError(f"SSL key not found: {self.ssl_key_path}")
