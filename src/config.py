#!/usr/bin/env python3

"""Configuration management with environment variable support"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
import configparser
from dotenv import load_dotenv
from dataclasses import dataclass, asdict


class ConfigError(Exception):
    """Configuration error"""
    pass


@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "127.0.0.1"
    port: int = 44445
    max_connections: int = 100
    connection_timeout: float = 30.0
    max_request_size: int = 1024 * 1024  # 1MB
    search_file: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    rate_limit_window: float = 60.0  # seconds
    monitoring_interval: float = 5.0  # seconds
    monitoring_enabled: bool = True
    log_dir: Optional[str] = None
    metrics_retention: int = 1000  # number of metrics to retain
    alert_retention: int = 1000  # number of alerts to retain
    health_check_interval: float = 10.0  # seconds
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()
        
    def validate(self) -> None:
        """Validate configuration values"""
        if self.port < 1 or self.port > 65535:
            raise ConfigError("Invalid port number")
            
        if self.max_connections < 1:
            raise ConfigError("Invalid max_connections value")
            
        if self.connection_timeout <= 0:
            raise ConfigError("Invalid connection_timeout value")
            
        if self.max_request_size < 1:
            raise ConfigError("Invalid max_request_size value")
            
        if self.rate_limit < 1:
            raise ConfigError("Invalid rate_limit value")
            
        if self.rate_limit_window <= 0:
            raise ConfigError("Invalid rate_limit_window value")
            
        if self.monitoring_interval <= 0:
            raise ConfigError("Invalid monitoring_interval value")
            
        if self.metrics_retention < 1:
            raise ConfigError("Invalid metrics_retention value")
            
        if self.alert_retention < 1:
            raise ConfigError("Invalid alert_retention value")
            
        if self.health_check_interval <= 0:
            raise ConfigError("Invalid health_check_interval value")
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConfig':
        """Create configuration from dictionary"""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        config_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**config_data)
        
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Load configuration from environment variables"""
        env_prefix = "SERVER_"
        env_vars = {
            k[len(env_prefix):].lower(): v
            for k, v in os.environ.items()
            if k.startswith(env_prefix)
        }
        return cls.from_dict(env_vars)
        
    @classmethod
    def from_file(cls, path: str) -> 'ServerConfig':
        """Load configuration from file"""
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")
            
        try:
            with open(path) as f:
                if path.suffix == '.json':
                    data = json.load(f)
                elif path.suffix in ('.yaml', '.yml'):
                    data = yaml.safe_load(f)
                else:
                    raise ConfigError(f"Unsupported configuration format: {path.suffix}")
                    
            return cls.from_dict(data)
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigError(f"Failed to parse configuration file: {e}")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return asdict(self)
        
    def save(self, path: str) -> None:
        """Save configuration to file"""
        path = Path(path)
        data = self.to_dict()
        
        try:
            with open(path, 'w') as f:
                if path.suffix == '.json':
                    json.dump(data, f, indent=2)
                elif path.suffix in ('.yaml', '.yml'):
                    yaml.safe_dump(data, f)
                else:
                    raise ConfigError(f"Unsupported configuration format: {path.suffix}")
                    
        except Exception as e:
            raise ConfigError(f"Failed to save configuration: {e}")


class Config:
    """Configuration manager"""

    def __init__(self, config_path: str = "config/config.ini"):
        load_dotenv()
        self.config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation()
        )
        self.config.read(config_path)

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get config value with environment variable support"""
        value = self.config.get(section, key, fallback=fallback)
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, fallback)
        return value

    @property
    def file_path(self) -> Path:
        """Get search file path"""
        return Path(self.get("DEFAULT", "linuxpath"))

    @property
    def reread_on_query(self) -> bool:
        """Get reread_on_query setting"""
        return self.get("DEFAULT", "reread_on_query").lower() == "true"
