"""
domain 层 - 大模型对话业务域
职责：定义对话业务用例语义，支持多模型切换，编排 component 完成对话流程。
      历史记忆由浏览器页面侧维护，domain 层不做本地历史管理。
C4 定位：System Context（描述"做什么"，屏蔽模型差异）
"""
from typing import List, Dict, Type
from playwright.sync_api import Page

from adapter.llm.base import BaseLLMAdapter
from adapter.llm.qwen import QwenAdapter
from component.chat import ChatComponent
from pkg.models import ChatRequest
from pkg.logger import logger


# 已支持的模型注册表：模型名 -> 适配器类
MODEL_REGISTRY: Dict[str, Type[BaseLLMAdapter]] = {
    "qwen": QwenAdapter,
    # 扩展示例（后续新增适配器后在此注册）:
    # "chatgpt": ChatGPTAdapter,
    # "deepseek": DeepSeekAdapter,
}


class ChatDomain:
    """
    大模型对话业务域。
    支持多模型切换，提供文本对话、多轮对话等业务用例。
    会话上下文记忆由浏览器页面侧天然维护。
    """

    def __init__(self, page: Page, model: str = "Qwen3.5-Omni-Plus", provider: str = "qwen"):
        """
        :param page: Playwright Page 对象
        :param model: 模型名称，对应 MODEL_REGISTRY 中的 key
        """
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


    def start(self) -> "ChatDomain":
        """启动对话：打开模型页面"""
        self._chat.start()
        return self

    def text_chat(self, request: ChatRequest) -> str:
        """
        单轮对话（支持文本 + 附件）。
        :param request: ChatRequest 对象
        :return: AI 回复文本
        """
        logger.info(f"[Domain][Chat] 文本对话: {request.message[:60]}...")
        return self._chat.send(request)

    def multi_turn_chat(self, request: ChatRequest) -> Dict:
        """
        多轮对话——发送单条消息，通过 request.session_id 定位端侧已有会话。
        会话记忆由浏览器页面侧天然维护，无需传递历史列表。

        :param request: ChatRequest（含 session_id，首次为空字符串）
        :return: {
            "session_id": 会话 ID（首次由端侧 URL 生成，后续保持不变），
            "question": 本轮问题,
            "answer": 本轮 AI 回复,
            "timestamp": 回复时间戳
        }
        """
        logger.info(f"[Domain][Chat] 多轮对话，session_id={request.session_id!r}")
        return self._chat.send_in_session(request)

    def reset(self) -> "ChatDomain":
        """新建对话，重置页面上下文"""
        self._chat.reset()
        return self

    @staticmethod
    def supported_models() -> List[str]:
        """返回当前已注册的模型列表"""
        return list(MODEL_REGISTRY.keys())

    def select_model(self, model):
        """选择指定的模型"""
        return self._chat.select_model(model)
