#!/usr/bin/env python3

"""Configuration management with environment variable support"""

import os
from pathlib import Path
from typing import Any, Dict
import configparser
from dotenv import load_dotenv

class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: str = "config/config.ini"):
        # Load environment variables
        load_dotenv()
        
        self.config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation()
        )
        self.config.read(config_path)
        
    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get config value with environment variable support"""
        value = self.config.get(section, key, fallback=fallback)
        
        # Check if value references an env var
        if value.startswith("${") and value.endswith("}"):
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