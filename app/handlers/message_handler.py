# -*- coding: utf-8 -*-
"""
消息业务处理器

接收解析后的消息对象，执行业务逻辑，并返回回复消息的明文 XML 字符串。
开发者可在此模块中扩展各类消息的处理逻辑。
"""

import logging
from typing import Optional

from app.core.msg_parser import (
    BaseMessage,
    EventMessage,
    ImageMessage,
    LinkMessage,
    LocationMessage,
    TextMessage,
    VoiceMessage,
    build_text_reply,
)

logger = logging.getLogger(__name__)


def handle_message(msg: BaseMessage) -> Optional[str]:
    """
    根据消息类型分发到对应的处理函数。

    Args:
        msg: 解析后的消息对象

    Returns:
        回复消息的明文 XML 字符串；若无需回复则返回 None
    """
    msg_type = msg.msg_type

    if msg_type == "text":
        return _handle_text(msg)  # type: ignore[arg-type]
    elif msg_type == "image":
        return _handle_image(msg)  # type: ignore[arg-type]
    elif msg_type == "voice":
        return _handle_voice(msg)  # type: ignore[arg-type]
    elif msg_type == "location":
        return _handle_location(msg)  # type: ignore[arg-type]
    elif msg_type == "link":
        return _handle_link(msg)  # type: ignore[arg-type]
    elif msg_type == "event":
        return _handle_event(msg)  # type: ignore[arg-type]
    else:
        logger.warning("收到未知消息类型: %s，来自: %s", msg_type, msg.from_user_name)
        return None


# ---------------------------------------------------------------------------
# 各类型消息处理函数（开发者在此处实现业务逻辑）
# ---------------------------------------------------------------------------

def _handle_text(msg: TextMessage) -> Optional[str]:
    """
    处理文本消息。
    当前实现：原样回显用户发送的内容（Echo 模式）。
    开发者可在此接入 LLM、知识库或指令路由逻辑。
    """
    logger.info(
        "[文本消息] from=%s, agent=%s, content=%s",
        msg.from_user_name, msg.agent_id, msg.content,
    )
    reply_content = f"您好，您发送了：{msg.content}"
    return build_text_reply(
        to_user=msg.from_user_name,
        from_user=msg.to_user_name,
        content=reply_content,
        agent_id=msg.agent_id,
    )


def _handle_image(msg: ImageMessage) -> Optional[str]:
    """处理图片消息。"""
    logger.info(
        "[图片消息] from=%s, media_id=%s",
        msg.from_user_name, msg.media_id,
    )
    return build_text_reply(
        to_user=msg.from_user_name,
        from_user=msg.to_user_name,
        content="已收到您发送的图片。",
        agent_id=msg.agent_id,
    )


def _handle_voice(msg: VoiceMessage) -> Optional[str]:
    """处理语音消息。"""
    logger.info(
        "[语音消息] from=%s, media_id=%s, format=%s",
        msg.from_user_name, msg.media_id, msg.format,
    )
    return build_text_reply(
        to_user=msg.from_user_name,
        from_user=msg.to_user_name,
        content="已收到您发送的语音消息。",
        agent_id=msg.agent_id,
    )


def _handle_location(msg: LocationMessage) -> Optional[str]:
    """处理位置消息。"""
    logger.info(
        "[位置消息] from=%s, lat=%s, lng=%s, label=%s",
        msg.from_user_name, msg.location_x, msg.location_y, msg.label,
    )
    return build_text_reply(
        to_user=msg.from_user_name,
        from_user=msg.to_user_name,
        content=f"已收到您的位置：{msg.label}（{msg.location_x}, {msg.location_y}）。",
        agent_id=msg.agent_id,
    )


def _handle_link(msg: LinkMessage) -> Optional[str]:
    """处理链接消息。"""
    logger.info(
        "[链接消息] from=%s, title=%s, url=%s",
        msg.from_user_name, msg.title, msg.url,
    )
    return build_text_reply(
        to_user=msg.from_user_name,
        from_user=msg.to_user_name,
        content=f"已收到您分享的链接：{msg.title}",
        agent_id=msg.agent_id,
    )


def _handle_event(msg: EventMessage) -> Optional[str]:
    """
    处理事件消息。
    常见事件类型：
      - enter_agent    用户进入应用
      - CLICK          点击菜单
      - template_card_event  模板卡片点击
    """
    logger.info(
        "[事件消息] from=%s, event=%s, event_key=%s",
        msg.from_user_name, msg.event, msg.event_key,
    )
    event_type = msg.event.lower()

    if event_type == "enter_agent":
        return build_text_reply(
            to_user=msg.from_user_name,
            from_user=msg.to_user_name,
            content="欢迎使用智能机器人！请输入您的问题。",
            agent_id=msg.agent_id,
        )
    elif event_type == "click":
        return build_text_reply(
            to_user=msg.from_user_name,
            from_user=msg.to_user_name,
            content=f"您点击了菜单：{msg.event_key}",
            agent_id=msg.agent_id,
        )
    else:
        # 其他事件类型，仅记录日志，不回复
        logger.info("未处理的事件类型: %s", msg.event)
        return None
