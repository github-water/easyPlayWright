import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import Page

from pkg.config import config


def take_screenshot(page: Page, name: str = "") -> str:
    """截图并保存到 output/screenshots 目录"""
    screenshot_dir = Path(__file__).parent.parent / config.get(
        "output", "screenshot_dir", default="output/screenshots"
    )
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png" if name else f"screenshot_{timestamp}.png"
    path = screenshot_dir / filename

    page.screenshot(path=str(path), full_page=True)
    return str(path)



def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
