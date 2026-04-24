"""
API 初始化模块
职责：创建并配置 FastAPI 应用，注册所有路由，管理应用生命周期
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI

from adapter.browser import BrowserAdapter
from pkg.logger import logger


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """应用生命周期管理：启动时初始化，关闭时清理浏览器资源"""
    logger.info("[App] FastAPI 应用启动")
    yield
    # 应用关闭时清理所有浏览器实例
    logger.info("[App] 清理浏览器资源...")
    await BrowserAdapter.close_all()
    logger.info("[App] 清理完成")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="easyPlayWright Chat API",
    description="基于 Playwright + Python 的大模型对话自动化 HTTP 服务",
    version="1.0.0",
    lifespan=lifespan,
)


def register_routers(fastapi_app: FastAPI):
    """注册所有路由到 FastAPI 应用"""
    from api.http.chat_controller import chat_router
    from api.http.video_controller import video_router

    fastapi_app.include_router(chat_router)
    fastapi_app.include_router(video_router)


# 初始化路由
register_routers(app)
