"""
easyPlayWright 主入口
通过 api 层（对外接口）调用系统能力。
用法：python main.py
"""
import sys
from pathlib import Path

from flask import Flask

from api.init import app

sys.path.insert(0, str(Path(__file__).parent))

from pkg.logger import logger


def main():
    # 启动 Flask 开发服务器（生产环境建议使用 gunicorn/uwsgi）
    app.run(host="0.0.0.0", port=8888, debug=False, threaded=True)

if __name__ == "__main__":
    logger.info("=== easyPlayWright HTTP Service 启动 ===")
    logger.info("监听地址：http://localhost:8888")
    logger.info("API 端点：POST /api/chat")
    main()

