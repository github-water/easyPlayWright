"""
pkg 层 - 公共数据模型
定义跨层复用的请求/响应数据类，各层统一使用，避免重复定义。
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class AttachmentType(str, Enum):
    """附件类型枚举"""
    IMAGE = "image"       # 图片：jpg/png/gif/webp 等
    VIDEO = "video"       # 视频：mp4/mov/avi 等
    FILE = "file"         # 通用文件：pdf/txt/docx/xlsx 等
    AUDIO = "audio"       # 音频：mp3/wav 等


# 各类型支持的扩展名映射
ATTACHMENT_EXT_MAP = {
    AttachmentType.IMAGE: {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"},
    AttachmentType.VIDEO: {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"},
    AttachmentType.AUDIO: {".mp3", ".wav", ".ogg", ".m4a", ".flac"},
    AttachmentType.FILE:  {".pdf", ".txt", ".md", ".docx", ".xlsx", ".pptx", ".csv", ".json", ".zip"},
}


def infer_attachment_type(path: str) -> AttachmentType:
    """根据文件扩展名自动推断附件类型"""
    ext = Path(path).suffix.lower()
    for att_type, exts in ATTACHMENT_EXT_MAP.items():
        if ext in exts:
            return att_type
    return AttachmentType.FILE  # 未知扩展名默认为通用文件


@dataclass
class Attachment:
    """
    附件数据类。
    :param path: 文件本地路径（绝对路径或相对路径）
    :param type: 附件类型，为 None 时根据扩展名自动推断
    :param name: 附件显示名称，为 None 时使用文件名
    """
    path: str
    type: Optional[AttachmentType] = None
    name: Optional[str] = None

    def __post_init__(self):
        if not Path(self.path).exists():
            raise FileNotFoundError(f"附件文件不存在: {self.path}")
        if self.type is None:
            self.type = infer_attachment_type(self.path)
        if self.name is None:
            self.name = Path(self.path).name

    @property
    def abs_path(self) -> str:
        """返回绝对路径"""
        return str(Path(self.path).resolve())


@dataclass
class ChatRequest:
    """
    对话请求数据类。
    封装一次对话的完整请求：文本消息 + 可选附件列表 + 可选会话 ID。

    session_id 用于多轮对话时指定已有会话，首次发起时留空，
    后续轮次由调用方从上一次响应中取得并传入。

    示例：
        # 纯文本（新会话）
        req = ChatRequest(message="你好")

        # 继续已有会话
        req = ChatRequest(message="继续", session_id="a1b2c3d4-...")

        # 带图片
        req = ChatRequest(
            message="分析这张图片",
            attachments=[Attachment(path="images/chart.png")]
        )

        # 多附件
        req = ChatRequest(
            message="对比这两个文件",
            attachments=[
                Attachment(path="doc1.pdf"),
                Attachment(path="doc2.pdf"),
            ]
        )
    """
    message: str
    attachments: List[Attachment] = field(default_factory=list)
    timeout: float = 60.0
    session_id: str = ""
    provider: str = "qwen"
    model: str = "Qwen3.5-Omni-Plus"

    @property
    def has_attachments(self) -> bool:
        """是否包含附件"""
        return len(self.attachments) > 0

    @property
    def attachment_types(self) -> List[AttachmentType]:
        """返回所有附件类型列表"""
        return [a.type for a in self.attachments]

    def add_attachment(self, path: str, att_type: AttachmentType = None) -> "ChatRequest":
        """链式添加附件"""
        self.attachments.append(Attachment(path=path, type=att_type))
        return self


@dataclass
class ChatResponse:
    """
    对话响应数据类。
    封装一次对话的回复结果。
    """
    question: str
    answer: str
    timestamp: str = ""
    model: str = ""

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp,
            "model": self.model,
        }
