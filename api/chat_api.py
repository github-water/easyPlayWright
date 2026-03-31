"""
api 层 - 大模型对话系统对外接口
职责：作为系统唯一入口，被外部调用者（测试/脚本/CI）使用。
      屏蔽内部 domain/component/adapter 实现细节。
C4 定位：System Interface（Container 对外边界）
"""
from typing import List, Dict, Optional

from adapter.browser import BrowserAdapter
from adapter.page import PageAdapter
from domain.llm.chat_domain import ChatDomain
from pkg.models import ChatRequest, Attachment
from pkg.logger import logger


class ChatApi:
    """
    大模型对话系统对外接口。
    支持单轮/多轮对话，每条消息可携带图片、视频、文件等附件。
    会话记忆由浏览器页面侧（端侧）天然维护，通过 session_id 关联。
    """

    def __init__(self, model: str = "qwen", storage_state: str = None):
        """
        :param model: 模型名称，当前支持 'qwen'
        :param storage_state: 登录态文件路径，如 'output/qwen_state.json'
                              为 None 时读取 config.yaml 中 browser.storage_state
        """
        self._model = model
        self._storage_state = storage_state

    def text_chat(
        self,
        message: str,
        attachments: Optional[List[str]] = None,
        timeout: float = 60.0,
    ) -> str:
        """
        单轮对话（支持文本 + 附件）。

        :param message: 用户消息文本
        :param attachments: 附件文件路径列表，如 ['image.png', 'doc.pdf']，类型自动推断
        :param timeout: 等待回复超时秒数
        :return: AI 回复文本
        """
        request = self._build_request(message, attachments, timeout)
        logger.info(f"[API][Chat] text_chat，model={self._model}")

        with BrowserAdapter(storage_state=self._storage_state) as context:
            page = PageAdapter(context).new_page()
            domain = ChatDomain(page, model=self._model)
            domain.start()
            response = domain.text_chat(request)

        return response

    def multi_turn_chat(
        self,
        message: str,
        session_id: str = "",
        attachments: Optional[List[str]] = None,
        timeout: float = 60.0,
    ) -> Dict:
        """
        多轮对话——每次调用发送一条消息，通过 session_id 定位端侧已有会话。
        端侧浏览器自动维护上下文记忆，无需调用方传递历史消息列表。

        首次调用无需传 session_id（新建会话），返回值中包含本次会话的 session_id，
        后续调用传入该 session_id 即可在同一会话内继续对话。

        :param message: 本轮用户消息文本
        :param session_id: 会话 ID（首次调用传空字符串或省略）
        :param attachments: 附件文件路径列表，类型自动推断
        :param timeout: 等待回复超时秒数
        :return: {
            "session_id": 会话 ID（首次调用时由端侧 URL 生成，后续保持不变），
            "question": 本轮问题,
            "answer": 本轮 AI 回复,
            "timestamp": 回复时间戳
        }
        """
        request = self._build_request(message, attachments, timeout, session_id)
        logger.info(f"[API][Chat] multi_turn_chat，model={self._model}，session_id={session_id!r}")

        with BrowserAdapter(storage_state=self._storage_state) as context:
            page = PageAdapter(context).new_page()
            domain = ChatDomain(page, model=self._model)
            domain.start()
            result = domain.multi_turn_chat(request)

        return result

    @staticmethod
    def supported_models() -> List[str]:
        """返回当前支持的模型列表"""
        return ChatDomain.supported_models()

    # ------------------------------------------------------------------ #
    # 内部工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_request(
        message: str,
        attachment_paths: Optional[List[str]],
        timeout: float,
        session_id: str = "",
    ) -> ChatRequest:
        """构建单条 ChatRequest"""
        attachments = [Attachment(path=p) for p in (attachment_paths or [])]
        return ChatRequest(
            message=message,
            attachments=attachments,
            timeout=timeout,
            session_id=session_id,
        )
