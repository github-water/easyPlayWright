"""
adapter 层 - 千问大模型页面适配器
职责：对接 https://chat.qwen.ai/ 页面，封装输入、附件上传、发送、等待回复的原子操作。
C4 定位：External System Adapter（对接千问外部系统）
"""
import asyncio

from playwright.async_api import Page

from adapter.llm.base import BaseLLMAdapter
from pkg.models import ChatRequest, AttachmentType
from pkg.logger import logger

# 千问对话页面地址
QWEN_URL = "https://chat.qwen.ai/"

# 页面元素选择器（基于 DOM 分析结果，可通过 update_selectors 动态覆盖）
SELECTORS = {
    # 输入框
    "input": ".message-input-container textarea",
    # 发送按钮
    "send_btn": ".message-input-right-button-send button",
    # 新建对话
    "new_chat": ".sidebar-entry-fixed-list-content div",
    # 模式选择
    "mode_select": ".mode-select-open",
    # 文件上传 input
    "file_input": "text=上传附件",
    # 最后一条 AI 回复内容块（流式输出结束后）
    "t2t_response_list": "div.response-message-content.t2t.phase-answer",
    # 停止生成按钮
    "loading": ".stop-button",
    # 会话前缀
    "session_prefix": "div.chat-item-drag-link-content-tip-text.chat-item-drag-link-content-tip",
    # 当前会话
    "cur_session": "a.chat-item-drag-link.chat-item-drag-active div.chat-item-drag-link-content-tip-text.chat-item-drag-link-content-tip",
    # 模型下拉箭头（header 区域的模型选择器）
    "model_arrow": "#qwen-chat-header-left",
    # 模型选择菜单
    "model_menu": "text=",
    # 预览文件
    "preview_file": ".vision-item-container"
}


class QwenAdapter(BaseLLMAdapter):
    """
    千问页面适配器（异步版）。
    封装与 chat.qwen.ai 页面交互的所有原子操作，支持文本+附件上传。
    """

    def __init__(self, page: Page):
        super().__init__(page)

    async def open(self) -> "QwenAdapter":
        """打开千问对话页面并等待输入框就绪"""
        logger.info(f"[Adapter][Qwen] 打开页面: {QWEN_URL}")
        await self.page.goto(QWEN_URL, wait_until="domcontentloaded")
        await self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=30000)
        logger.info("[Adapter][Qwen] 页面就绪")
        return self

    async def type_message(self, text: str) -> "QwenAdapter":
        """在输入框中输入文本消息"""
        logger.debug(f"[Adapter][Qwen] 输入消息: {text[:50]}...")
        input_el = self.page.locator(SELECTORS["input"])
        await input_el.click()
        await input_el.fill(text)
        return self

    async def upload_attachments(self, request: ChatRequest) -> "QwenAdapter":
        """
        上传附件列表（图片/视频/文件）。
        千问上传流程：点击"+"按钮 → 弹出菜单 → 点击"上传附件" → 触发文件选择器。
        通过监听 filechooser 事件注入文件路径。
        """
        if not request.has_attachments:
            return self

        file_paths = [a.abs_path for a in request.attachments]
        logger.info(f"[Adapter][Qwen] 上传附件 {len(file_paths)} 个: {[a.name for a in request.attachments]}")

        # 1. 点击"+"按钮弹出功能菜单
        await self.page.locator(SELECTORS["mode_select"]).click()
        await asyncio.sleep(0.5)

        # 2. 监听 filechooser 事件，同时点击"上传附件"菜单项触发文件选择器
        async with self.page.expect_file_chooser() as fc_info:
            await self.page.locator(SELECTORS["file_input"]).click()
        file_chooser = await fc_info.value

        # 3. 通过 file_chooser 注入所有文件
        logger.info(f"[Adapter][Qwen] 通过 FileChooser 注入文件: {file_paths}")
        await file_chooser.set_files(file_paths)

        # 4. 等待上传完成（文件预览出现）
        await asyncio.sleep(2.0)
        preview_file = self.page.locator(SELECTORS["preview_file"])
        await preview_file.wait_for(state="visible", timeout=30000)
        logger.info("[Adapter][Qwen] 附件上传完成")

        return self

    async def send(self) -> "QwenAdapter":
        """点击发送按钮（等待按钮可用后再点击）"""
        logger.debug("[Adapter][Qwen] 等待发送按钮可用...")
        send_btn = self.page.locator(SELECTORS["send_btn"])
        # 等待按钮不再是 disabled 状态（超时 30 秒）
        import time
        deadline = time.time() + 30
        while await send_btn.is_disabled():
            if time.time() > deadline:
                raise TimeoutError("[Adapter][Qwen] 发送按钮超过 30 秒仍为 disabled")
            await asyncio.sleep(0.3)
        logger.debug("[Adapter][Qwen] 发送消息")
        await send_btn.click()
        return self

    async def send_by_enter(self) -> "QwenAdapter":
        """通过回车键发送消息"""
        logger.debug("[Adapter][Qwen] 回车发送消息")
        await self.page.locator(SELECTORS["input"]).press("Enter")
        return self

    async def wait_for_response(self, timeout: float = 180.0, poll_interval: float = 1.0) -> str:
        """
        等待 AI 回复完成并返回回复文本。
        策略：等待 loading 消失后读取最后一条回复内容。
        使用 asyncio.sleep 替代 time.sleep，不阻塞事件循环。
        """
        logger.info("[Adapter][Qwen] 等待 AI 回复...")
        import time
        deadline = time.time() + timeout

        # 先等待 loading 出现（流式输出开始）
        loading_appeared = False
        while time.time() < deadline:
            if await self.page.locator(SELECTORS["loading"]).count() > 0:
                logger.info("[Adapter][Qwen] 流式输出开始")
                loading_appeared = True
                break
            await asyncio.sleep(0.3)

        answer_end = False
        if loading_appeared:
            # 等待 loading 消失（流式输出结束）
            while time.time() < deadline:
                if await self.page.locator(SELECTORS["loading"]).count() == 0:
                    logger.info("[Adapter][Qwen] 流式输出结束")
                    answer_end = True
                    break
                await asyncio.sleep(poll_interval)

        if not answer_end:
            logger.error(f"[Adapter][Qwen] 生成超时，进行内容截断！")
        # 给页面额外渲染时间
        await asyncio.sleep(2)

        response = await self._get_last_response()
        return response

    async def _get_last_response(self) -> str:
        """获取最后一条 AI 回复文本"""
        items = self.page.locator(SELECTORS["t2t_response_list"]).last
        count = await items.count()
        if count == 0:
            return ""
        return (await items.nth(count - 1).inner_text()).strip()

    async def new_chat(self) -> "QwenAdapter":
        """点击新建对话"""
        logger.info("[Adapter][Qwen] 新建对话")
        btn = self.page.locator(SELECTORS["new_chat"])
        if await btn.is_visible():
            await btn.click()
            await self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=10000)
        return self

    async def get_session_id(self) -> str:
        """取出当前会话的文本"""
        text = await self.page.locator(SELECTORS["cur_session"]).text_content()
        return text

    async def open_session(self, session_id: str) -> "QwenAdapter":
        """找到指定会话并打开"""
        if not session_id:
            logger.warning("[Adapter][Qwen] 未提供会话 ID，将新建对话")
            await self.page.locator(SELECTORS["new_chat"]).click()
        else:
            logger.info(f"[Adapter][Qwen] 打开会话: {session_id}")
            await self.page.locator(SELECTORS["session_prefix"] + f':text("{session_id}")').click()
            logger.info(f"[Adapter][Qwen] 会话已恢复，session_id={session_id}")
        return self

    async def select_model(self, model):
        """选择模型：点击下拉箭头，等待菜单出现，点击目标模型项"""
        logger.info(f"[Adapter][Qwen] 选择模型: {model}")
        await self.page.locator(SELECTORS["model_arrow"]).click()
        await asyncio.sleep(0.5)
        await self.page.locator(SELECTORS["model_menu"]+f'{model}').first.click()
        await asyncio.sleep(0.3)

    def update_selectors(self, **kwargs) -> "QwenAdapter":
        """动态更新选择器（适配页面 DOM 变更）"""
        SELECTORS.update(kwargs)
        logger.debug(f"[Adapter][Qwen] 选择器已更新: {kwargs}")
        return self
