# -*- coding: utf-8 -*-
"""
企业微信智能机器人回调路由

接口路径：/work/bot/callback
  - GET  /work/bot/callback  企业微信验证回调 URL 有效性
  - POST /work/bot/callback  接收企业微信推送的加密消息

验证流程（GET）：
  1. 企业微信发送 GET 请求，携带 msg_signature / timestamp / nonce / echostr
  2. 服务端验证签名，解密 echostr，将明文原样返回（纯文本，无引号、无 BOM、无换行）

消息接收流程（POST）：
  1. 企业微信发送 POST 请求，URL 参数携带 msg_signature / timestamp / nonce
  2. 请求体为 XML 格式的加密消息
  3. 服务端验证签名，解密消息体，解析消息类型，执行业务逻辑
  4. 如需被动回复，将回复消息加密后以 XML 格式返回；否则返回空字符串

参考文档：
  https://developer.work.weixin.qq.com/document/path/91116
"""

import logging

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import PlainTextResponse

from app.core.msg_parser import parse_message
from app.core.wx_crypt import WXBizMsgCrypt, WXCryptError
from app.handlers.message_handler import handle_message
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局加解密实例（在应用启动时初始化，避免每次请求重复创建）
_wx_crypt: WXBizMsgCrypt | None = None


def get_wx_crypt() -> WXBizMsgCrypt:
    """获取（或懒加载初始化）WXBizMsgCrypt 实例。"""
    global _wx_crypt
    if _wx_crypt is None:
        _wx_crypt = WXBizMsgCrypt(
            token=settings.WECOM_TOKEN,
            encoding_aes_key=settings.WECOM_ENCODING_AES_KEY,
            receive_id=settings.WECOM_CORP_ID,
        )
    return _wx_crypt


# ---------------------------------------------------------------------------
# GET  /work/bot/callback  —— URL 有效性验证
# ---------------------------------------------------------------------------

@router.get(
    "/work/bot/callback",
    summary="企业微信回调 URL 有效性验证",
    description=(
        "企业微信在保存回调配置时，会向此接口发送 GET 请求。"
        "服务端需验证签名并将解密后的 echostr 明文原样返回。"
    ),
    response_class=PlainTextResponse,
)
async def verify_callback_url(
    msg_signature: str = Query(..., description="消息体签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机字符串"),
    echostr: str = Query(..., description="加密的随机字符串"),
) -> PlainTextResponse:
    """
    验证回调 URL 有效性。

    企业微信要求在 **1 秒内** 响应，且响应体必须是解密后的 echostr 明文，
    不能包含引号、BOM 头或换行符。
    """
    logger.info(
        "[URL验证] msg_signature=%s, timestamp=%s, nonce=%s",
        msg_signature, timestamp, nonce,
    )
    try:
        crypt = get_wx_crypt()
        echo_plain = crypt.verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info("[URL验证] 验证成功，返回明文 echostr")
        return PlainTextResponse(content=echo_plain)
    except WXCryptError as exc:
        logger.error("[URL验证] 失败，code=%d, msg=%s", exc.code, exc.message)
        return PlainTextResponse(content="", status_code=403)
    except Exception as exc:
        logger.exception("[URL验证] 未知异常: %s", exc)
        return PlainTextResponse(content="", status_code=500)


# ---------------------------------------------------------------------------
# POST /work/bot/callback  —— 接收业务消息
# ---------------------------------------------------------------------------

@router.post(
    "/work/bot/callback",
    summary="接收企业微信智能机器人消息",
    description=(
        "接收企业微信推送的加密消息，解密后解析消息类型，"
        "执行业务逻辑，并在需要时返回加密的被动回复消息。"
    ),
)
async def receive_callback(
    request: Request,
    msg_signature: str = Query(..., description="消息体签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机字符串"),
) -> Response:
    """
    接收并处理企业微信推送的加密消息。

    处理流程：
    1. 读取请求体（XML 格式的加密消息）
    2. 验证签名并解密消息体
    3. 解析消息类型，分发到业务处理器
    4. 若有回复内容，加密后以 XML 格式返回；否则返回空字符串

    企业微信要求在 **5 秒内** 响应，超时会重试（最多 3 次）。
    建议：接收到消息后立即异步处理，立刻返回 "success" 或空字符串。
    """
    # 1. 读取请求体
    try:
        body_bytes = await request.body()
        post_data = body_bytes.decode("utf-8")
    except Exception as exc:
        logger.error("[消息接收] 读取请求体失败: %s", exc)
        return Response(content="", media_type="text/plain")

    logger.info(
        "[消息接收] msg_signature=%s, timestamp=%s, nonce=%s, body_len=%d",
        msg_signature, timestamp, nonce, len(post_data),
    )
    logger.debug("[消息接收] 原始请求体:\n%s", post_data)

    # 2. 验证签名 + 解密消息体
    try:
        crypt = get_wx_crypt()
        plain_xml = crypt.decrypt_msg(post_data, msg_signature, timestamp, nonce)
    except WXCryptError as exc:
        logger.error("[消息解密] 失败，code=%d, msg=%s", exc.code, exc.message)
        return Response(content="", media_type="text/plain")
    except Exception as exc:
        logger.exception("[消息解密] 未知异常: %s", exc)
        return Response(content="", media_type="text/plain")

    logger.debug("[消息解密] 明文:\n%s", plain_xml)

    # 3. 解析消息
    try:
        msg = parse_message(plain_xml)
    except ValueError as exc:
        logger.error("[消息解析] 失败: %s", exc)
        return Response(content="", media_type="text/plain")

    logger.info(
        "[消息解析] type=%s, from=%s, agent=%s",
        msg.msg_type, msg.from_user_name, msg.agent_id,
    )

    # 4. 业务处理
    try:
        reply_plain_xml = handle_message(msg)
    except Exception as exc:
        logger.exception("[业务处理] 异常: %s", exc)
        return Response(content="", media_type="text/plain")

    # 5. 若无需回复，返回空字符串（企业微信接受此响应）
    if not reply_plain_xml:
        return Response(content="", media_type="text/plain")

    # 6. 加密回复消息
    try:
        encrypted_reply = crypt.encrypt_msg(reply_plain_xml, nonce, timestamp)
    except WXCryptError as exc:
        logger.error("[回复加密] 失败，code=%d, msg=%s", exc.code, exc.message)
        return Response(content="", media_type="text/plain")

    logger.info("[回复消息] 加密完成，准备返回")
    return Response(content=encrypted_reply, media_type="application/xml")
