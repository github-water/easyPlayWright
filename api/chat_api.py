"""
api 层 - 大模型对话系统对外接口
职责：作为系统唯一入口，被外部调用者（测试/脚本/CI）使用。
      屏蔽内部 domain/component/adapter 实现细节。
C4 定位：System Interface（Container 对外边界）

支持两种浏览器管理模式：
1. 一次性模式（默认）：每次调用创建/销毁浏览器，适用于脚本和示例
2. 单例模式（singleton=True）：复用浏览器实例和页面，适用于 HTTP 服务

异步架构：基于 Playwright async API，支持多请求并发。
"""
import asyncio
from typing import List, Dict, Optional

from adapter.browser import BrowserAdapter
from adapter.page import PageAdapter
from domain.llm.chat_domain import ChatDomain
from pkg.models import ChatRequest, Attachment
from pkg.logger import logger


def get_storage_state(provider, storage_state):
    if storage_state:
        return storage_state
    return f"output/state/{provider}_state.json"


class ChatApi:
    """
    大模型对话系统对外接口（异步版）。
    提供统一的 chat 方法，支持单轮/多轮对话，每条消息可携带图片、视频、文件等附件。
    会话记忆由浏览器页面侧（端侧）天然维护，通过 session_id 关联。
    """

    def __init__(self, model: str = "Qwen3.5-Omni-Plus", provider: str = "qwen",
                 storage_state: str = None, singleton: bool = True):
        """
        :param model: 模型名称，当前支持 'qwen'
        :param provider: 服务提供商，如 'qwen', 'chatgpt' 等
        :param storage_state: 登录态文件路径
        :param singleton: 是否使用单例浏览器（HTTP 服务场景设为 True）
        """
        self._model = model
        self._provider = provider
        self._storage_state = get_storage_state(self._provider, storage_state)
        self._singleton = singleton

    @property
    def provider(self) -> str:
        """返回当前使用的服务提供商"""
        return self._provider or "default"

    async def chat(
        self,
        message: str,
        session_id: str = "",
        attachments: Optional[List[str]] = None,
        timeout: float = 60.0,
    ) -> Dict:
        """
        统一对话入口（支持单轮/多轮、文本 + 附件）。

        - session_id 为空：新建会话（单轮 / 多轮首轮）
        - session_id 非空：恢复已有会话（多轮后续轮次）

        :param message: 用户消息文本
        :param session_id: 会话 ID（首次调用传空或省略，后续从返回值中获取）
        :param attachments: 附件文件路径列表
        :param timeout: 等待回复超时秒数
        :return: {"session_id", "question", "answer", "timestamp"}
        """
        request = self._build_request(message, attachments, timeout, session_id, self.provider, self._model)
        logger.info(
            f"[API][Chat] chat，model={self._model}，"
            f"session_id={session_id!r}，singleton={self._singleton}"
        )

        if self._singleton:
            return await self._chat_singleton(request)
        else:
            return await self._chat_disposable(request)

    @staticmethod
    def supported_models() -> List[str]:
        """返回当前支持的模型列表"""
        return ChatDomain.supported_models()

    # ------------------------------------------------------------------ #
    # 单例模式实现（复用浏览器实例和页面，支持并发）
    # ------------------------------------------------------------------ #

    async def _get_singleton_resources(self) -> tuple:
        """
        获取单例模式下的 (adapter, domain, is_new_page, page_key)。
        复用已缓存的 Page，避免重复创建和导航。
        """
        adapter = await BrowserAdapter.get_instance(storage_state=self._storage_state)
        page_key = self._provider
        is_new = not adapter.has_cached_page(page_key)
        page = await adapter.get_or_create_page(page_key)
        domain = ChatDomain(page, model=self._model)
        return adapter, domain, is_new, page_key

    async def _chat_singleton(self, request: ChatRequest) -> Dict:
        adapter, domain, is_new, page_key = await self._get_singleton_resources()
        page_lock = adapter.get_page_lock(page_key)
        async with page_lock:
            logger.debug(f"[API][Chat] 获取 Page 锁: {page_key}")
            if is_new:
                await domain.start()
            return await domain.chat(request)

    # ------------------------------------------------------------------ #
    # 一次性模式实现（每次创建/销毁，向后兼容）
    # ------------------------------------------------------------------ #

    async def _chat_disposable(self, request: ChatRequest) -> Dict:
        async with BrowserAdapter(storage_state=self._storage_state) as context:
            page = await PageAdapter(context).new_page()
            domain = ChatDomain(page, model=self._model)
            await domain.start()
            await domain.select_model(self._model)
            return await domain.chat(request)

    # ------------------------------------------------------------------ #
    # 内部工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_request(
        message: str,
        attachment_paths: Optional[List[str]],
        timeout: float,
        session_id: str = "",
        provider: str = "",
        model: str = ""
    ) -> ChatRequest:
        """构建单条 ChatRequest"""
        attachments = [Attachment(path=p) for p in (attachment_paths or [])]
        return ChatRequest(
            message=message,
            attachments=attachments,
            timeout=timeout,
            session_id=session_id,
            provider=provider,
            model=model
        )
