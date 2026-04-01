"""
domain 层 - 大模型对话业务域
职责：定义对话业务用例语义，支持多模型切换，编排 component 完成对话流程。
      历史记忆由浏览器页面侧维护，domain 层不做本地历史管理。
C4 定位：System Context（描述"做什么"，屏蔽模型差异）
"""
from typing import List, Dict, Type
from playwright.async_api import Page

from adapter.llm.base import BaseLLMAdapter
from adapter.llm.qwen import QwenAdapter
from adapter.llm.doubao import DoubaoAdapter
from component.chat import ChatComponent
from pkg.models import ChatRequest
from pkg.logger import logger


# 已支持的模型注册表：provider 名 -> 适配器类
MODEL_REGISTRY: Dict[str, Type[BaseLLMAdapter]] = {
    "qwen": QwenAdapter,
    "doubao": DoubaoAdapter,
    # 扩展示例（后续新增适配器后在此注册）:
    # "chatgpt": ChatGPTAdapter,
    # "deepseek": DeepSeekAdapter,
}


class ChatDomain:
    """
    大模型对话业务域（异步版）。
    支持多模型切换，提供文本对话、多轮对话等业务用例。
    会话上下文记忆由浏览器页面侧天然维护。
    """

    def __init__(self, page: Page, model: str = "Qwen3.5-Omni-Plus", provider: str = "qwen"):
        self._page = page
        self._provider = provider
        self._adapter = self._build_adapter(self._provider)
        self._chat = ChatComponent(self._adapter)
        self._model_name = model

    def _build_adapter(self, provider: str) -> BaseLLMAdapter:
        """根据模型名构建对应适配器"""
        if provider not in MODEL_REGISTRY:
            supported = list(MODEL_REGISTRY.keys())
            raise ValueError(
                f"不支持的模型: '{provider}'，当前支持: {supported}。"
                f"请在 MODEL_REGISTRY 中注册新适配器。"
            )
        adapter_cls = MODEL_REGISTRY[provider]
        logger.info(f"[Domain][Chat] 使用模型: {provider} -> {adapter_cls.__name__}")
        return adapter_cls(self._page)

    async def start(self) -> "ChatDomain":
        """启动对话：打开模型页面"""
        await self._chat.start()
        return self

    async def chat(self, request: ChatRequest) -> Dict:
        """
        统一对话入口（支持单轮/多轮、文本 + 附件）。
        - session_id 为空：新建会话（单轮/多轮首轮）
        - session_id 非空：恢复已有会话（多轮后续轮次）
        返回包含 session_id 的完整结果，调用方可据此发起后续轮次。
        :param request: ChatRequest 对象
        :return: {"session_id", "question", "answer", "timestamp"}
        """
        logger.info(
            f"[Domain][Chat] 对话: {request.message[:60]}..., "
            f"session_id={request.session_id!r}"
        )
        return await self._chat.send_in_session(request)

    async def reset(self) -> "ChatDomain":
        """新建对话，重置页面上下文"""
        await self._chat.reset()
        return self

    @staticmethod
    def supported_models() -> List[str]:
        """返回当前已注册的模型列表"""
        return list(MODEL_REGISTRY.keys())

    async def select_model(self, model):
        """选择指定的模型"""
        return await self._chat.select_model(model)
