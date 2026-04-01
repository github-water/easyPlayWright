"""
component 层 - 对话编排组件
职责：系统主动驱动 LLM adapter，编排单轮/多轮对话流程。
      历史记忆由浏览器中的大模型页面自身维护，无需本地冗余存储。
C4 定位：Component（系统内编排，主动调用外部 adapter）
"""
from datetime import datetime

from adapter.llm.base import BaseLLMAdapter
from pkg.models import ChatRequest
from pkg.logger import logger


class ChatComponent:
    """
    对话编排组件（异步版）。
    专注于请求发送与回复获取，不维护本地对话历史。
    浏览器页面侧天然保持会话上下文记忆。
    """

    def __init__(self, adapter: BaseLLMAdapter):
        self._adapter = adapter

    async def start(self) -> "ChatComponent":
        """初始化：打开模型页面"""
        logger.info("[Component][Chat] 初始化对话")
        await self._adapter.open()
        return self

    async def send(self, request: ChatRequest) -> str:
        """
        发送一条对话请求并获取回复。
        :param request: ChatRequest 对象（含文本消息和可选附件）
        :return: AI 回复文本
        """
        logger.info(
            f"[Component][Chat] 发送: {request.message[:60]}"
            + (f"，附件 {len(request.attachments)} 个" if request.has_attachments else "")
        )
        response = await self._adapter.chat(request)
        logger.info(f"[Component][Chat] 收到回复: {response[:60]}...")
        return response

    async def send_in_session(self, request: ChatRequest) -> dict:
        """
        发送单条消息，通过 request.session_id 定位端侧已有会话。
        - session_id 为空：新建会话，发送后从 URL 提取 session_id 返回
        - session_id 非空：导航到已有会话页面后再发送，保持端侧上下文记忆
        """
        await self._adapter.open_session(request.session_id)

        response = await self.send(request)

        session_id = await self._adapter.get_session_id()
        logger.info(f"[Component][Chat] 当前 session_id={session_id}")

        return {
            "session_id": session_id,
            "question": request.message,
            "answer": response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def reset(self) -> "ChatComponent":
        """新建对话，重置页面上下文"""
        logger.info("[Component][Chat] 重置对话上下文")
        await self._adapter.new_chat()
        return self

    async def select_model(self, model):
        """选择模型"""
        logger.info(f"[Component][Chat] 选择模型: {model}")
        await self._adapter.select_model(model)
        return model
