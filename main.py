"""
easyPlayWright 主入口
通过 uvicorn 启动 FastAPI 异步 HTTP 服务。
用法：python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pkg.logger import logger


def main():
    import uvicorn
    # 使用 uvicorn 启动 FastAPI 应用
    # 异步架构：单进程单事件循环，Playwright 异步操作在同一循环中并发执行
    uvicorn.run(
        "api.init:app",
        host="0.0.0.0",
        port=8009,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    logger.info("=== easyPlayWright HTTP Service 启动 ===")
    logger.info("监听地址：http://localhost:8009")
    logger.info("API 端点：POST /api/chat")
    logger.info("API 文档：http://localhost:8009/docs")
    main()
