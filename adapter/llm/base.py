"""
adapter 层 - 大模型页面适配器抽象基类
职责：定义所有 LLM 页面适配器必须实现的统一接口，支持多模型切换。
C4 定位：External System Adapter 抽象契约
"""
import asyncio
from abc import ABC, abstractmethod

from playwright.async_api import Page

from pkg.models import ChatRequest


class BaseLLMAdapter(ABC):
    """所有大模型页面适配器的抽象基类（异步版）"""

    def __init__(self, page: Page):
        self.page = page

    @abstractmethod
    async def open(self) -> "BaseLLMAdapter":
        """打开模型对话页面并等待就绪"""
        ...

    @abstractmethod
    async def type_message(self, text: str) -> "BaseLLMAdapter":
        """在输入框中输入文本消息"""
        ...

    @abstractmethod
    async def upload_attachments(self, request: ChatRequest) -> "BaseLLMAdapter":
        """
        上传附件（图片/视频/文件等）。
        无附件时直接返回 self，子类必须实现但可为空操作。
        """
        ...

    @abstractmethod
    async def send(self) -> "BaseLLMAdapter":
        """触发发送（点击按钮或回车）"""
        ...

    @abstractmethod
    async def wait_for_response(self, timeout: float = 60.0, poll_interval: float = 1.0) -> str:
        """等待 AI 回复完成并返回回复文本"""
        ...

    @abstractmethod
    async def new_chat(self) -> "BaseLLMAdapter":
        """新建对话（重置页面上下文）"""
        ...

    @abstractmethod
    async def get_session_id(self) -> str:
        """
        获取当前对话的会话 ID。
        通常从页面 URL 中解析（如 /c/{session_id}）。
        未进入对话时返回空字符串。
        """
        ...

    @abstractmethod
    async def open_session(self, session_id: str) -> "BaseLLMAdapter":
        """
        导航到指定 session_id 对应的已有会话页面。
        用于多轮对话时恢复端侧上下文记忆。
        """
        ...

    async def chat(self, request: ChatRequest) -> str:
        """
        一步完成：上传附件（如有）-> 输入消息 -> 发送 -> 等待回复。
        子类可复用此模板方法，无需重复编写流程。
        """
        if request.has_attachments:
            await self.upload_attachments(request)
        await self.type_message(request.message)
        await self.send()
        await asyncio.sleep(1.5)
        return await self.wait_for_response(timeout=request.timeout)

    @abstractmethod
    async def select_model(self, model):
        """
        选择指定模型
        """
