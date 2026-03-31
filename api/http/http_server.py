"""
api 层 - HTTP 服务入口
职责：将 ChatApi 封装为 HTTP 接口，供外部系统调用
C4 定位：System Interface（HTTP 协议版本）
"""
from flask import Flask, request, jsonify, Blueprint
from pathlib import Path

from api.chat_api import ChatApi
from main import app
from pkg.logger import logger

chat_bp = Blueprint("chat_bp", __name__)

@chat_bp.route("/api/chat", methods=["POST"])
def text_chat():
    """
    文本对话接口（支持附件、自定义模型）
    
    Request Body (JSON):
    {
        "message": "你好，请帮我分析这个文件",  # 必填，对话文本
        "model": "qwen",                       # 可选，模型名称，默认 qwen
        "provider": "aliyun",                  # 可选，服务提供商，默认 None
        "attachments": [                        # 可选，附件路径列表
            "/path/to/file.pdf",
            "/path/to/image.png"
        ],
        "timeout": 60.0                         # 可选，超时秒数，默认 60
    }
    
    Response (JSON):
    {
        "success": true,                        # true 表示成功，false 表示失败
        "data": {
            "answer": "AI 回复的内容...",         # AI 回复文本
            "question": "用户提问",              # 用户问题
            "model": "qwen",                     # 使用的模型
            "provider": "aliyun"                 # 使用的服务提供商
        },
        "error": null                           # 失败时包含错误信息
    }
    """
    try:
        data = request.get_json()
        
        # 参数校验
        if not data or "message" not in data:
            return jsonify({
                "success": False,
                "error": "缺少必填参数：message"
            }), 400
        
        message = data["message"]
        model = data.get("model", "Qwen3.5-Omni-Plus")
        provider = data.get("provider", "qwen")
        attachments = data.get("attachments", [])
        timeout = data.get("timeout", 60.0)
        
        # 校验附件文件是否存在
        for att_path in attachments:
            if not Path(att_path).exists():
                logger.warning(f"[HTTP] 附件文件不存在：{att_path}")
                return jsonify({
                    "success": False,
                    "error": f"附件文件不存在：{att_path}"
                }), 400
        
        logger.info(f"[HTTP] 收到对话请求：message={message[:60]}..., model={model}, provider={provider}, attachments={len(attachments)}")
        
        # 调用 ChatApi（每次使用指定模型和 provider 创建新实例）
        chat_api = ChatApi(model=model, provider=provider)
        answer = chat_api.text_chat(
            message=message,
            attachments=attachments if attachments else None,
            timeout=timeout
        )
        
        response_data = {
            "answer": answer,
            "question": message,
            "model": model,
            "provider": chat_api.provider
        }
        
        logger.info(f"[HTTP] 对话完成，回复长度：{len(answer)}")
        
        return jsonify({
            "success": True,
            "data": response_data,
            "error": None
        })
        
    except Exception as e:
        logger.error(f"[HTTP] 对话失败：{e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"服务器内部错误：{str(e)}"
        }), 500


@chat_bp.route("/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "service": "easyPlayWright Chat API"
    })



