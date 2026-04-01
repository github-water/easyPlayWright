"""
工具脚本：手动登录千问并保存登录态
运行后会打开浏览器，请手动完成登录，登录成功后按 Enter 保存状态。
保存的 state.json 可供后续自动化使用，无需重复登录。

用法：python tools/save_login_state.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from adapter.browser import BrowserAdapter

STATE_FILE = "../output/state/qwen_state.json"
TARGET_URL = "https://chat.qwen.ai/"


async def save_login_state():
    async with async_playwright() as p:
        # 使用有头模式 + 系统 Chrome，让用户手动登录
        from pkg.config import config as app_config
        channel = app_config.get("browser", "channel", default="")

        launch_kwargs = dict(
            headless=False,
            args=BrowserAdapter._get_stealth_args(),
        )
        if channel:
            launch_kwargs["channel"] = channel

        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # 注入反自动化检测脚本
        await context.add_init_script(BrowserAdapter._get_stealth_script())

        page = await context.new_page()
        await page.goto(TARGET_URL, wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("浏览器已打开，请手动完成登录操作...")
        print("登录成功后，回到此终端按 Enter 键保存登录状态")
        print("=" * 60)

        # 在异步环境中等待用户输入（不阻塞事件循环）
        await asyncio.get_event_loop().run_in_executor(None, input)

        # 保存完整浏览器状态（Cookie + localStorage + sessionStorage）
        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=STATE_FILE)
        print(f"✅ 登录状态已保存至: {STATE_FILE}")

        element = page.locator(".chat-layout-input-container")
        # 必须在 count() 前面加上 await
        count = await element.count()
        print(f"是否存在: {count > 0}")

        if count > 0:
            # is_visible() 和 inner_html() 同样需要 await
            visible = await element.is_visible()
            html = await element.inner_html()
            print(f"是否可见: {visible}")
            print(f"内部HTML: {html}")
        else:
            print("DOM 中未找到该元素")

        # 截图排查：看看自动化运行时页面到底长什么样
        await page.screenshot(path="../output/debug.png")



        await browser.close()


if __name__ == "__main__":
    asyncio.run(save_login_state())
