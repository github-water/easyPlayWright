"""
adapter 层 - 豆包大模型页面适配器
职责：对接 https://www.doubao.com/chat/ 页面，封装输入、附件上传、发送、等待回复的原子操作。
C4 定位：External System Adapter（对接豆包外部系统）
"""
import asyncio
import time

from playwright.async_api import Page

from adapter.llm.base import BaseLLMAdapter
from pkg.models import ChatRequest, AttachmentType
from pkg.logger import logger

# 豆包对话页面地址
DOUBAO_URL = "https://www.doubao.com/chat/"

# 页面元素选择器（基于豆包页面 DOM 结构）
SELECTORS = {
    # 输入框
    "input": '[data-testid="chat_input_input"]',
    # 发送按钮
    "send_btn": '[data-testid="chat_input_send_button"]',
    # 新建对话
    "new_chat": '[data-testid="create_conversation_button"]',
    # 附件选择器
    "attachment": 'button:has(svg path[d^="M17.3977"])',
    # 文件上传 input
    "file_upload": '[data-testid="upload_file_panel_upload_item"]',
    # AI 回复内容块
    "response": '[data-testid="receive_message"]',
    # 停止生成按钮
    "loading": '[data-testid="chat_input_local_break_button"]',
    # 会话列表项
    "session_item": '[data-testid="chat_list_thread_item"]',
    # 当前激活会话
    "cur_session": '[data-testid="chat_list_bot_item"]',
}




class DoubaoAdapter(BaseLLMAdapter):
    """
    豆包页面适配器（异步版）。
    封装与 doubao.com 页面交互的所有原子操作，支持文本+附件上传。

    注意：豆包页面 DOM 结构可能随版本更新变化，
    如选择器失效，请通过 update_selectors() 动态覆盖或修改 SELECTORS 字典。
    """

    def __init__(self, page: Page):
        super().__init__(page)

    async def open(self) -> "DoubaoAdapter":
        """打开豆包对话页面并等待输入框就绪"""
        logger.info(f"[Adapter][Doubao] 打开页面: {DOUBAO_URL}")
        await self.page.goto(DOUBAO_URL, wait_until="domcontentloaded")
        await self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=30000)
        logger.info("[Adapter][Doubao] 页面就绪")
        return self

    async def type_message(self, text: str) -> "DoubaoAdapter":
        """在输入框中输入文本消息"""
        logger.debug(f"[Adapter][Doubao] 输入消息: {text[:50]}...")
        input_el = self.page.locator(SELECTORS["input"])
        await input_el.click()
        await input_el.fill(text)
        return self

    async def upload_attachments(self, request: ChatRequest) -> "DoubaoAdapter":
        """
        上传附件列表（图片/视频/文件）。
        豆包上传流程：点击附件按钮 → 等待上传面板展开 → 点击"上传文件" → 触发文件选择器。
        通过监听 filechooser 事件注入文件路径。
        """
        if not request.has_attachments:
            return self

        file_paths = [a.abs_path for a in request.attachments]
        logger.info(f"[Adapter][Doubao] 上传附件 {len(file_paths)} 个: {[a.name for a in request.attachments]}")

        # 1. 点击附件按钮，弹出上传面板
        attachment_btn = self.page.locator(SELECTORS["attachment"])
        await attachment_btn.click()
        logger.info("[Adapter][Doubao] 已点击附件按钮，等待上传面板展开...")

        # 2. 等待上传面板中的"上传文件"按钮可见
        upload_btn = self.page.locator(SELECTORS["file_upload"])
        await upload_btn.wait_for(state="visible", timeout=10000)
        await asyncio.sleep(0.3)

        # 3. 先注册 filechooser 监听，再点击"上传文件"触发文件选择器
        async with self.page.expect_file_chooser(timeout=10000) as fc_info:
            await upload_btn.click()
            logger.info("[Adapter][Doubao] 已点击上传文件按钮，等待文件选择器...")
        file_chooser = await fc_info.value

        # 4. 通过 file_chooser 注入文件
        logger.info(f"[Adapter][Doubao] 通过 FileChooser 注入文件: {file_paths}")
        await file_chooser.set_files(file_paths)

        # 5. 等待上传完成（预览出现）
        await asyncio.sleep(2.0)
        await self.exist_preview_file()
        logger.info("[Adapter][Doubao] 附件上传完成")

        return self

    async def exist_preview_file(self):
        # 预览图片
        await self.page.wait_for_selector('[data-testid="mdbox_image"]', state="visible", timeout=20000)

    async def send(self) -> "DoubaoAdapter":
        """点击发送按钮（等待按钮可用后再点击）"""
        logger.debug("[Adapter][Doubao] 等待发送按钮可用...")
        send_btn = self.page.locator(SELECTORS["send_btn"])
        # 等待按钮不再是 disabled 状态（超时 30 秒）
        deadline = time.time() + 30
        while await send_btn.is_disabled():
            if time.time() > deadline:
                raise TimeoutError("[Adapter][Doubao] 发送按钮超过 30 秒仍为 disabled")
            await asyncio.sleep(2)
        logger.debug("[Adapter][Doubao] 发送消息")
        await send_btn.click()
        return self

    async def wait_for_response(self, timeout: float = 180.0, poll_interval: float = 1.0) -> str:
        """
        等待 AI 回复完成并返回回复文本。
        策略：等待 loading 消失后读取最后一条回复内容。
        """
        logger.info("[Adapter][Doubao] 等待 AI 回复...")
        deadline = time.time() + timeout

        # 先等待 loading 出现（流式输出开始）
        loading_appeared = False
        while time.time() < deadline:
            if await self.page.locator(SELECTORS["loading"]).count() > 0:
                logger.info("[Adapter][Doubao] 流式输出开始")
                loading_appeared = True
                break
            await asyncio.sleep(0.3)

        answer_end = False
        if loading_appeared:
            # 等待 loading 消失（流式输出结束）
            while time.time() < deadline:
                if await self.page.locator(SELECTORS["loading"]).count() == 0:
                    logger.info("[Adapter][Doubao] 流式输出结束")
                    answer_end = True
                    break
                await asyncio.sleep(poll_interval)

        if not answer_end:
            logger.error("[Adapter][Doubao] 生成超时，进行内容截断！")

        # 给页面额外渲染时间
        await asyncio.sleep(2)

        response = await self._get_last_response()
        return response

    async def _get_last_response(self) -> str:
        """获取最后一条 AI 回复文本"""
        items = self.page.locator(SELECTORS["response"])
        count = await items.count()
        if count == 0:
            return ""
        return (await items.nth(count - 1).inner_text()).strip()

    async def new_chat(self) -> "DoubaoAdapter":
        """点击新建对话"""
        logger.info("[Adapter][Doubao] 新建对话")
        btn = self.page.locator(SELECTORS["new_chat"])
        if await btn.count() > 0 and await btn.first.is_visible():
            await btn.first.click()
            await self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=10000)
        return self

    async def get_session_id(self) -> str:
        """从当前 URL 或页面元素中获取会话 ID"""
        # 豆包的会话 ID 通常在 URL 中，如 /chat/{session_id}
        url = self.page.url
        if "/chat/" in url:
            parts = url.rstrip("/").split("/chat/")
            if len(parts) > 1 and parts[1]:
                return parts[1].split("?")[0]
        return ""

    async def open_session(self, session_id: str) -> "DoubaoAdapter":
        """导航到指定会话"""
        if not session_id:
            logger.warning("[Adapter][Doubao] 未提供会话 ID，将新建对话")
            await self.new_chat()
        else:
            logger.info(f"[Adapter][Doubao] 打开会话: {session_id}")
            # 尝试通过 URL 直接导航
            target_url = f"{DOUBAO_URL}/{session_id}"
            await self.page.goto(target_url, wait_until="domcontentloaded")
            await self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=30000)
            logger.info(f"[Adapter][Doubao] 会话已恢复，session_id={session_id}")
        return self

    async def select_model(self, model):
        """选择模型：点击模型选择器，等待菜单出现，点击目标模型项"""
        logger.info(f"[Adapter][Doubao] 默认选择模型")

