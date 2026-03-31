"""
API 初始化模块
职责：创建并配置 Flask 应用，注册所有 Blueprint
"""
from flask import Flask

# 创建 Flask 应用实例
app = Flask(__name__)

# 注册 Blueprint（延迟导入避免循环依赖）
def register_blueprints(flask_app: Flask):
    """注册所有 Blueprint 到 Flask 应用"""
    from api.http.http_server import chat_bp
    
    flask_app.register_blueprint(chat_bp)
    
    # 如果有其他 blueprint，在这里继续注册
    # flask_app.register_blueprint(other_bp)

# 初始化蓝图
register_blueprints(app)
