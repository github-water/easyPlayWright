"""
工具脚本：手动登录千问并保存登录态
运行后会打开浏览器，请手动完成登录，登录成功后按 Enter 保存状态。
保存的 state.json 可供后续自动化使用，无需重复登录。

用法：python tools/save_login_state.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright

STATE_FILE = "../output/state/qwen_state.json"
TARGET_URL = "https://chat.qwen.ai/"


def save_login_state():
    with sync_playwright() as p:
        # 使用有头模式，让用户手动登录
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("浏览器已打开，请手动完成登录操作...")
        print("登录成功后，回到此终端按 Enter 键保存登录状态")
        print("=" * 60)
        input()

        # 保存完整浏览器状态（Cookie + localStorage + sessionStorage）
        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=STATE_FILE)
        print(f"✅ 登录状态已保存至: {STATE_FILE}")

        browser.close()


if __name__ == "__main__":
    save_login_state()
