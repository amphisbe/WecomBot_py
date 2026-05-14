# -*- coding: utf-8 -*-
"""
企业微信智能机器人消息解析模块

将解密后的 XML 明文解析为结构化的消息对象，
并提供构造被动回复消息 XML 的工具函数。

参考文档：
  https://developer.work.weixin.qq.com/document/path/91116
"""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 消息数据类
# ---------------------------------------------------------------------------

@dataclass
class BaseMessage:
    """所有消息类型的公共字段"""
    to_user_name: str = ""      # 企业微信 CorpID
    from_user_name: str = ""    # 发送者 UserID
    create_time: int = 0        # 消息创建时间（Unix 时间戳）
    msg_type: str = ""          # 消息类型
    msg_id: str = ""            # 消息 ID（用于去重）
    agent_id: str = ""          # 应用 AgentID


@dataclass
class TextMessage(BaseMessage):
    """文本消息"""
    content: str = ""


@dataclass
class ImageMessage(BaseMessage):
    """图片消息"""
    pic_url: str = ""
    media_id: str = ""


@dataclass
class VoiceMessage(BaseMessage):
    """语音消息"""
    media_id: str = ""
    format: str = ""


@dataclass
class VideoMessage(BaseMessage):
    """视频消息"""
    media_id: str = ""
    thumb_media_id: str = ""


@dataclass
class LocationMessage(BaseMessage):
    """位置消息"""
    location_x: str = ""    # 纬度
    location_y: str = ""    # 经度
    scale: str = ""         # 地图缩放大小
    label: str = ""         # 地理位置信息


@dataclass
class LinkMessage(BaseMessage):
    """链接消息"""
    title: str = ""
    description: str = ""
    url: str = ""
    pic_url: str = ""


@dataclass
class EventMessage(BaseMessage):
    """事件消息（如进入会话、模板卡片点击等）"""
    event: str = ""             # 事件类型，如 enter_agent
    event_key: str = ""         # 事件 KEY 值
    task_id: str = ""           # 模板卡片任务 ID
    card_type: str = ""         # 模板卡片类型


# ---------------------------------------------------------------------------
# 解析函数
# ---------------------------------------------------------------------------

def _get_text(tree: ET.Element, tag: str, default: str = "") -> str:
    """安全地从 XML 树中获取指定标签的文本内容。"""
    elem = tree.find(tag)
    if elem is not None and elem.text:
        return elem.text.strip()
    return default


def parse_message(xml_text: str) -> BaseMessage:
    """
    将解密后的 XML 明文解析为对应的消息对象。

    Args:
        xml_text: 解密后的消息明文 XML 字符串

    Returns:
        对应类型的消息数据类实例

    Raises:
        ValueError: XML 格式不合法时抛出
    """
    try:
        tree = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"XML 解析失败: {exc}") from exc

    # 读取公共字段
    base_kwargs = dict(
        to_user_name=_get_text(tree, "ToUserName"),
        from_user_name=_get_text(tree, "FromUserName"),
        create_time=int(_get_text(tree, "CreateTime", "0")),
        msg_type=_get_text(tree, "MsgType"),
        msg_id=_get_text(tree, "MsgId"),
        agent_id=_get_text(tree, "AgentID"),
    )

    msg_type = base_kwargs["msg_type"]

    if msg_type == "text":
        return TextMessage(
            **base_kwargs,
            content=_get_text(tree, "Content"),
        )
    elif msg_type == "image":
        return ImageMessage(
            **base_kwargs,
            pic_url=_get_text(tree, "PicUrl"),
            media_id=_get_text(tree, "MediaId"),
        )
    elif msg_type == "voice":
        return VoiceMessage(
            **base_kwargs,
            media_id=_get_text(tree, "MediaId"),
            format=_get_text(tree, "Format"),
        )
    elif msg_type == "video":
        return VideoMessage(
            **base_kwargs,
            media_id=_get_text(tree, "MediaId"),
            thumb_media_id=_get_text(tree, "ThumbMediaId"),
        )
    elif msg_type == "location":
        return LocationMessage(
            **base_kwargs,
            location_x=_get_text(tree, "Location_X"),
            location_y=_get_text(tree, "Location_Y"),
            scale=_get_text(tree, "Scale"),
            label=_get_text(tree, "Label"),
        )
    elif msg_type == "link":
        return LinkMessage(
            **base_kwargs,
            title=_get_text(tree, "Title"),
            description=_get_text(tree, "Description"),
            url=_get_text(tree, "Url"),
            pic_url=_get_text(tree, "PicUrl"),
        )
    elif msg_type == "event":
        return EventMessage(
            **base_kwargs,
            event=_get_text(tree, "Event"),
            event_key=_get_text(tree, "EventKey"),
            task_id=_get_text(tree, "TaskId"),
            card_type=_get_text(tree, "CardType"),
        )
    else:
        # 未知类型，返回基础消息对象
        return BaseMessage(**base_kwargs)


# ---------------------------------------------------------------------------
# 回复消息构造
# ---------------------------------------------------------------------------

def build_text_reply(
    to_user: str,
    from_user: str,
    content: str,
    agent_id: str = "",
) -> str:
    """
    构造文本类型的被动回复消息 XML。

    Args:
        to_user:   接收方 UserID（即原消息的 FromUserName）
        from_user: 发送方（企业微信 CorpID 或 AgentID）
        content:   回复的文本内容
        agent_id:  应用 AgentID

    Returns:
        符合企业微信规范的回复 XML 字符串（加密前的明文）
    """
    create_time = int(time.time())
    return (
        "<xml>"
        f"<ToUserName><![CDATA[{to_user}]]></ToUserName>"
        f"<FromUserName><![CDATA[{from_user}]]></FromUserName>"
        f"<CreateTime>{create_time}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{content}]]></Content>"
        f"<AgentID>{agent_id}</AgentID>"
        "</xml>"
    )
