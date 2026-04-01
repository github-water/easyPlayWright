"""
api 层 - HTTP 服务入口
职责：将 ChatApi 封装为 HTTP 接口，供外部系统调用
C4 定位：System Interface（HTTP 协议版本）

使用 FastAPI 异步框架 + Playwright 异步 API，支持多请求并发。
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path

from api.chat_api import ChatApi
from pkg.logger import logger

chat_router = APIRouter()


# ------------------------------------------------------------------ #
# 请求/响应模型
# ------------------------------------------------------------------ #

class ChatRequest(BaseModel):
    """对话请求体"""
    message: str = Field(..., description="对话文本（必填）")
    model: str = Field(default="Qwen3.5-Omni-Plus", description="模型名称")
    provider: str = Field(default="qwen", description="服务提供商")
    session_id: str = Field(default="", description="会话 ID（首次留空，后续传入以继续多轮对话）")
    attachments: List[str] = Field(default=[], description="附件文件路径列表")
    timeout: float = Field(default=60.0, description="超时秒数")


class ChatResponseData(BaseModel):
    """对话响应数据"""
    answer: str
    question: str
    session_id: str
    timestamp: str
    model: str
    provider: str


class ChatResponse(BaseModel):
    """对话响应体"""
    success: bool
    data:Optional[ChatResponseData] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str


# ------------------------------------------------------------------ #
# 路由
# ------------------------------------------------------------------ #

@chat_router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    统一对话接口（支持单轮/多轮、附件、自定义模型）。
    - 首次对话：session_id 留空
    - 多轮后续：传入上次返回的 session_id
    异步处理，不阻塞其他请求。
    """
    try:
        # 校验附件文件是否存在
        for att_path in req.attachments:
            if not Path(att_path).exists():
                logger.warning(f"[HTTP] 附件文件不存在：{att_path}")
                return ChatResponse(
                    success=False,
                    error=f"附件文件不存在：{att_path}"
                )

        logger.info(
            f"[HTTP] 收到对话请求：message={req.message[:60]}..., "
            f"model={req.model}, provider={req.provider}, "
            f"session_id={req.session_id!r}, "
            f"attachments={len(req.attachments)}"
        )

        # 使用单例模式创建 ChatApi，复用浏览器实例
        chat_api = ChatApi(model=req.model, provider=req.provider, singleton=True)
        result = await chat_api.chat(
            message=req.message,
            session_id=req.session_id,
            attachments=req.attachments if req.attachments else None,
            timeout=req.timeout,
        )

        response_data = ChatResponseData(
            answer=result["answer"],
            question=result["question"],
            session_id=result["session_id"],
            timestamp=result["timestamp"],
            model=req.model,
            provider=chat_api.provider,
        )

        logger.info(f"[HTTP] 对话完成，回复长度：{len(result['answer'])}")

        return ChatResponse(
            success=True,
            data=response_data,
            error=None,
        )

    except Exception as e:
        logger.error(f"[HTTP] 对话失败：{e}", exc_info=True)
        return ChatResponse(
            success=False,
            error=f"服务器内部错误：{str(e)}",
        )


@chat_router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="ok",
        service="easyPlayWright Chat API"
    )
