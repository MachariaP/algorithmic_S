from src.config import Config

class StringSearchServer:
    def __init__(self, config_path: str = "config/config.ini"):
        self.config = Config(config_path)
        # ... rest of initialization 