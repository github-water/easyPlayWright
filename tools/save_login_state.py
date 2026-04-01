"""
工具脚本：手动登录并保存登录态
运行后会打开浏览器，请手动完成登录，登录成功后按 Enter 保存状态。
保存的 state.json 可供后续自动化使用，无需重复登录。

用法：
  python tools/save_login_state.py              # 默认保存千问登录态
  python tools/save_login_state.py qwen         # 保存千问登录态
  python tools/save_login_state.py doubao       # 保存豆包登录态
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from adapter.browser import BrowserAdapter

# 支持的 provider 配置：provider -> (目标 URL, 登录态文件路径)
PROVIDER_CONFIG = {
    "qwen": {
        "url": "https://chat.qwen.ai/",
        "state_file": "output/state/qwen_state.json",
    },
    "doubao": {
        "url": "https://www.doubao.com/chat/",
        "state_file": "output/state/doubao_state.json",
    },
}


async def save_login_state(provider: str = "qwen"):
    if provider not in PROVIDER_CONFIG:
        supported = list(PROVIDER_CONFIG.keys())
        print(f"❌ 不支持的 provider: '{provider}'，当前支持: {supported}")
        return

    config = PROVIDER_CONFIG[provider]
    target_url = config["url"]
    state_file = config["state_file"]

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
            no_viewport=True,
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
        await page.goto(target_url, wait_until="domcontentloaded")

        print(f"\n{'=' * 60}")
        print(f"浏览器已打开 [{provider}]: {target_url}")
        print("请手动完成登录操作...")
        print("登录成功后，回到此终端按 Enter 键保存登录状态")
        print(f"{'=' * 60}")

        # 在异步环境中等待用户输入（不阻塞事件循环）
        await asyncio.get_event_loop().run_in_executor(None, input)

        # 保存完整浏览器状态（Cookie + localStorage + sessionStorage）
        Path(state_file).parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=state_file)
        print(f"✅ [{provider}] 登录状态已保存至: {state_file}")

        await browser.close()


if __name__ == "__main__":
    # 从命令行参数获取 provider，默认 qwen
    target_provider = sys.argv[1] if len(sys.argv) > 1 else "qwen"
    asyncio.run(save_login_state(target_provider))
