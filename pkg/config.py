import os
import yaml
from pathlib import Path


class Config:
    """全局配置管理器，读取 config.yaml"""

    _instance = None
    _config: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        root = Path(__file__).parent.parent
        config_path = root / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, *keys, default=None):
        """链式获取配置值，例如 config.get('browser', 'type')"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default


config = Config()
