"""Configuration management module"""

from typing import Optional, List

class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass

class ServerConfig:
    """Server configuration class."""
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 44445,
                 cache_size: int = 1000,
                 workers: int = 4,
                 file_path: Optional[str] = None,
                 ssl_enabled: bool = False,
                 rate_limit: int = 100,
                 max_connections: int = 1000,
                 ip_whitelist: Optional[List[str]] = None,
                 ip_blacklist: Optional[List[str]] = None):
        self.host = host
        self.port = port
        self.cache_size = cache_size
        self.workers = workers
        self.file_path = file_path
        self.ssl_enabled = ssl_enabled
        self.rate_limit = rate_limit
        self.max_connections = max_connections
        self.ip_whitelist = ip_whitelist or []
        self.ip_blacklist = ip_blacklist or []
        
    def validate(self) -> None:
        """Validate configuration values."""
        if not isinstance(self.port, int) or self.port < 1 or self.port > 65535:
            raise ConfigError("Port must be between 1 and 65535")
            
        if not isinstance(self.cache_size, int) or self.cache_size < 1:
            raise ConfigError("Cache size must be a positive integer")
            
        if not isinstance(self.workers, int) or self.workers < 1:
            raise ConfigError("Number of workers must be a positive integer")
            
        if not isinstance(self.rate_limit, int) or self.rate_limit < 1:
            raise ConfigError("Rate limit must be a positive integer")
            
        if not isinstance(self.max_connections, int) or self.max_connections < 1:
            raise ConfigError("Max connections must be a positive integer")
