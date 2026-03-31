import sys
from pathlib import Path
from loguru import logger as _logger

from pkg.config import config


def setup_logger():
    """初始化 loguru 日志配置"""
    _logger.remove()

    level = config.get("log", "level", default="INFO")
    rotation = config.get("log", "rotation", default="10 MB")
    retention = config.get("log", "retention", default="7 days")

    # 控制台输出
    _logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # 文件输出
    log_dir = Path(__file__).parent.parent / config.get("output", "log_dir", default="output/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    _logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    )

    return _logger


logger = setup_logger()
