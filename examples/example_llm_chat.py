"""
示例：大模型对话
演示三种使用方式：
  1. 单轮文本对话
  2. 多轮连续对话（页面侧维护上下文）
  3. 批量独立问答
底层使用千问（chat.qwen.ai），可通过 model 参数切换其他模型。

前置条件：已运行 tools/save_login_state.py 保存登录态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.chat_api import ChatApi
from pkg.logger import logger

# 登录态文件（运行 tools/save_login_state.py 生成）
STATE_FILE = "../output/qwen_state.json"


def demo_single_turn():
    """示例一：单轮文本对话"""
    logger.info("===== 示例一：单轮文本对话 =====")
    api = ChatApi(model="qwen", storage_state=STATE_FILE)
    response = api.text_chat("用一句话介绍你自己", timeout=60.0)
    logger.info(f"回复: {response}")
    return response


def demo_multi_turn():
    """示例二：多轮连续对话（页面侧维护上下文）"""
    logger.info("===== 示例二：多轮连续对话 =====")
    api = ChatApi(model="qwen", storage_state=STATE_FILE)
    result = api.multi_turn_chat(
        message="白银价格贵吗",
        session_id="今日白银价格查询",
        timeout=120.0,
    )
    answer = result['answer']
    logger.info(f'response：{answer}')
    return result



def demo_model_list():
    """示例四：查看支持的模型列表"""
    logger.info("===== 示例四：支持的模型列表 =====")
    models = ChatApi.supported_models()
    logger.info(f"当前支持的模型: {models}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="大模型对话示例")
    parser.add_argument(
        "--mode",
        choices=["single", "multi", "models"],
        default="multi",
        help="运行模式: single=单轮, multi=多轮, models=查看模型列表",
    )
    args = parser.parse_args()

    if args.mode == "single":
        demo_single_turn()
    elif args.mode == "multi":
        demo_multi_turn()
    elif args.mode == "models":
        demo_model_list()
