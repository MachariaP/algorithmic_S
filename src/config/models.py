"""Configuration models"""

class ConfigError(Exception):
    """Configuration error"""
    pass

from pathlib import Path
from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,
    model_validator,
    field_validator,
    ValidationError
)


class LogConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    directory: Path = Field(default=Path("/var/log/search_server"))
    format: str = Field(
        default="%(levelname)s %(name)s:%(filename)s:%(lineno)d %(message)s"
    )


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090, ge=1024, le=65535)
    metrics_retention: int = Field(default=3600)  # seconds
    alert_retention: int = Field(default=86400)  # seconds
    health_check_interval: float = Field(default=60.0)  # seconds


class SecurityConfig(BaseModel):
    """Security configuration"""
    ssl_enabled: bool = Field(default=True)
    cert_file: Optional[Path] = None
    key_file: Optional[Path] = None
    client_auth: bool = Field(default=False)
    allowed_ips: List[str] = Field(default=["127.0.0.1"])
    rate_limit: int = Field(default=1000)
    rate_limit_burst: int = Field(default=2000)

    @model_validator(mode="after")
    def validate_ssl_files(self) -> "SecurityConfig":
        """Validate SSL certificate files"""
        if self.ssl_enabled:
            if not self.cert_file or not self.key_file:
                raise ValueError("SSL certificate and key files are required when SSL is enabled")
            if not self.cert_file.exists():
                raise ValueError(f"SSL certificate file not found: {self.cert_file}")
            if not self.key_file.exists():
                raise ValueError(f"SSL key file not found: {self.key_file}")
        return self


class ResourceConfig(BaseModel):
    """Resource configuration"""
    max_connections: int = Field(default=1000, gt=0)
    connection_timeout: float = Field(default=30.0, gt=0)
    max_request_size: int = Field(default=1024 * 1024, gt=0)  # 1MB
    worker_threads: int = Field(default=4, gt=0)
    connection_pool_size: int = Field(default=100, gt=0)
    max_file_descriptors: int = Field(default=1024, gt=0)


class SearchConfig(BaseModel):
    """Search configuration"""
    cache_size: int = Field(default=1000, gt=0)
    max_pattern_length: int = Field(default=1000, gt=0)
    default_case_sensitive: bool = Field(default=False)
    index_type: str = Field(default="hash", pattern="^(hash|trie|suffix)$")


class ServerConfig(BaseModel):
    """Server configuration"""
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=44445, ge=1024, le=65535)
    data_file: Path
    log: LogConfig = Field(default_factory=LogConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

    @field_validator("data_file")
    @classmethod
    def validate_data_file(cls, v: Path) -> Path:
        """Validate data file exists"""
        if not v.exists():
            raise ValueError(f"Data file not found: {v}")
        if not v.is_file():
            raise ValueError(f"Data file is not a regular file: {v}")
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> "ServerConfig":
        """Load configuration from YAML file"""
        import yaml
        
        if not path.exists():
            raise ValueError(f"Configuration file not found: {path}")
            
        with open(path) as f:
            data = yaml.safe_load(f)
            
        return cls(**data)