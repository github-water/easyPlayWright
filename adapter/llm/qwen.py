"""
adapter 层 - 千问大模型页面适配器
职责：对接 https://chat.qwen.ai/ 页面，封装输入、附件上传、发送、等待回复的原子操作。
C4 定位：External System Adapter（对接千问外部系统）
"""
import time
from playwright.sync_api import Page

from adapter.llm.base import BaseLLMAdapter
from pkg.models import ChatRequest, AttachmentType
from pkg.logger import logger

# 千问对话页面地址
QWEN_URL = "https://chat.qwen.ai/"

# 页面元素选择器（基于 DOM 分析结果，可通过 update_selectors 动态覆盖）
SELECTORS = {
    # 输入框：textarea.message-input-textarea
    "input": ".message-input-container textarea",
    # 发送按钮：
    "send_btn": ".message-input-right-button-send button",
    # 新建对话：#sidebar > div > div.sidebar-entry-fixed-list > div.sidebar-entry-fixed-list-content > div
    "new_chat": ".sidebar-entry-fixed-list-content div",
    # 模式选择 input：#dropzone-container > div.message-input > div > div.message-input-container > div > div > div.mode-select > span > div
    "model_select": ".message-input-container .mode-select div",
    # 文件上传 input：
    "file_input": "li.ant-dropdown-menu-item.mode-select-common-item:text('上传附件')",
    # ---- 以下选择器在对话发生后才存在，需登录后实测校准 ----
    # 最后一条 AI 回复内容块（流式输出结束后）#chat-response-message-e3eba65c-96f3-4d84-a08f-fc083bb49954 > div > div:nth-child(1) > div.response-message-content.t2t.phase-answer
    "t2t_response_list": "div.response-message-content.t2t.phase-answer",
    # 回复流式输出进行中指示器:
    "loading": ".chat-prompt-send-button stop-button",
    # 停止生成按钮（流式输出中出现）
    "stop_btn": ".chat-prompt-send-button send-button disabled",
    # 会话前缀
    "session_prefix": "div.chat-item-drag-link-content-tip-text.chat-item-drag-link-content-tip",
    # 当前会话
    "cur_session": "a.chat-item-drag-link.chat-item-drag-active div.chat-item-drag-link-content-tip-text.chat-item-drag-link-content-tip",
    # 模型下拉箭头 #root > div > div > div.desktop-layout-content > div > div > div > div > div > header > div > div.header-left > div.index-module__mobile-model-selector___-iaic > div > span
    "model_arrow":'span[role="img"] use[xlink:href="#icon-line-chevron-down"]',
    # 模型选择菜单
    "model_menu": "div.index-module__model-item-content___ydaoe.ant-flex.css-mncuj7.ant-flex-align-stretch.ant-flex-vertical",
}


class QwenAdapter(BaseLLMAdapter):
    """
    千问页面适配器。
    封装与 chat.qwen.ai 页面交互的所有原子操作，支持文本+附件上传。
    """

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self) -> "QwenAdapter":
        """打开千问对话页面并等待输入框就绪"""
        logger.info(f"[Adapter][Qwen] 打开页面: {QWEN_URL}")
        self.page.goto(QWEN_URL, wait_until="domcontentloaded")
        self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=30000)
        logger.info("[Adapter][Qwen] 页面就绪")
        return self

    def type_message(self, text: str) -> "QwenAdapter":
        """在输入框中输入文本消息"""
        logger.debug(f"[Adapter][Qwen] 输入消息: {text[:50]}...")
        input_el = self.page.locator(SELECTORS["input"])
        input_el.click()
        input_el.fill(text)
        return self

    def upload_attachments(self, request: ChatRequest) -> "QwenAdapter":
        """
        上传附件列表（图片/视频/文件）。
        千问使用隐藏的 <input id="filesUpload"> 接收文件，
        通过 set_input_files 直接注入，无需点击按钮。
        """
        if not request.has_attachments:
            return self

        file_paths = [a.abs_path for a in request.attachments]
        logger.info(f"[Adapter][Qwen] 上传附件 {len(file_paths)} 个: {[a.name for a in request.attachments]}")

        file_input = self.page.locator(SELECTORS["file_input"])

        # 按附件类型分组上传（部分模型对图片/文件有不同的 input）
        image_paths = [
            a.abs_path for a in request.attachments
            if a.type == AttachmentType.IMAGE
        ]
        other_paths = [
            a.abs_path for a in request.attachments
            if a.type != AttachmentType.IMAGE
        ]

        if image_paths:
            logger.debug(f"[Adapter][Qwen] 上传图片: {image_paths}")
            file_input.set_input_files(image_paths)
            time.sleep(1.0)  # 等待预览渲染

        if other_paths:
            logger.debug(f"[Adapter][Qwen] 上传文件: {other_paths}")
            file_input.set_input_files(other_paths)
            time.sleep(1.0)

        return self

    def send(self) -> "QwenAdapter":
        """点击发送按钮"""
        logger.debug("[Adapter][Qwen] 发送消息")
        self.page.locator(SELECTORS["send_btn"]).click()
        return self

    def send_by_enter(self) -> "QwenAdapter":
        """通过回车键发送消息"""
        logger.debug("[Adapter][Qwen] 回车发送消息")
        self.page.locator(SELECTORS["input"]).press("Enter")
        return self

    def wait_for_response(self, timeout: float = 60.0, poll_interval: float = 1.0) -> str:
        """
        等待 AI 回复完成并返回回复文本。
        策略：等待 loading 消失后读取最后一条回复内容。
        """
        logger.info("[Adapter][Qwen] 等待 AI 回复...")
        deadline = time.time() + timeout

        # 先等待 loading 出现（流式输出开始）
        loading_appeared = False
        while time.time() < deadline:
            if self.page.locator(SELECTORS["loading"]).count() > 0:
                logger.info("[Adapter][Qwen] 流式输出开始")
                loading_appeared = True
                break
            time.sleep(0.3)

        if loading_appeared:
            # 等待 loading 消失（流式输出结束）
            while time.time() < deadline:
                if self.page.locator(SELECTORS["loading"]).count() == 0:
                    logger.info("[Adapter][Qwen] 流式输出结束")
                    break
                time.sleep(poll_interval)

        # 给页面额外渲染时间
        time.sleep(0.8)

        response = self._get_last_response()
        logger.info(f"[Adapter][Qwen] 收到回复: {response[:80]}...")
        return response

    def _get_last_response(self) -> str:
        """获取最后一条 AI 回复文本"""
        items = self.page.locator(SELECTORS["t2t_response_list"]).last
        count = items.count()
        if count == 0:
            return ""
        return items.nth(count - 1).inner_text().strip()

    def new_chat(self) -> "QwenAdapter":
        """点击新建对话"""
        logger.info("[Adapter][Qwen] 新建对话")
        btn = self.page.locator(SELECTORS["new_chat"])
        if btn.is_visible():
            btn.click()
            self.page.wait_for_selector(SELECTORS["input"], state="visible", timeout=10000)
        return self

    def get_session_id(self) -> str:
        """
        取出当前会话的文本
        """
        text = self.page.locator(SELECTORS["cur_session"]).text_content()
        return text

    def open_session(self, session_id: str) -> "QwenAdapter":
        """
        找到指定会话并打开
        """
        logger.info(f"[Adapter][Qwen] 打开会话: {session_id}")
        self.page.locator(SELECTORS["session_prefix"]+f':text("{session_id}")').click()
        logger.info(f"[Adapter][Qwen] 会话已恢复，session_id={session_id}")
        return self

    def select_model(self, model):
        """
        选择模型
        """
        # 点击模型下拉箭头
        self.page.locator(SELECTORS["model_arrow"]).click()
        self.page.locator("div", has_text=model)
        logger.info(f"[Adapter][Qwen] 已选择模型: {model}")

    def update_selectors(self, **kwargs) -> "QwenAdapter":
        """动态更新选择器（适配页面 DOM 变更）"""
        SELECTORS.update(kwargs)
        logger.debug(f"[Adapter][Qwen] 选择器已更新: {kwargs}")
        return self
