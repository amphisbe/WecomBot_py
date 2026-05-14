# -*- coding: utf-8 -*-
"""
企业微信消息加解密模块
基于官方 WXBizMsgCrypt 库重写，适配 Python 3 及 PyCryptodome。

参考文档：
  https://developer.work.weixin.qq.com/document/path/91116
  https://developer.work.weixin.qq.com/document/path/90468
"""

import base64
import hashlib
import random
import socket
import string
import struct
import time
import xml.etree.ElementTree as ET
from typing import Tuple

from Crypto.Cipher import AES


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class WXCryptError(Exception):
    """加解密过程中的业务异常"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


ERR_OK = 0
ERR_VALIDATE_SIGNATURE = -40001   # 签名验证失败
ERR_PARSE_XML = -40002            # XML 解析失败
ERR_COMPUTE_SIGNATURE = -40003    # SHA1 计算签名失败
ERR_ILLEGAL_AES_KEY = -40004      # AESKey 非法
ERR_VALIDATE_CORPID = -40005      # ReceiveId 校验错误
ERR_ENCRYPT_AES = -40006          # AES 加密失败
ERR_DECRYPT_AES = -40007          # AES 解密失败
ERR_ILLEGAL_BUFFER = -40008       # 解密后 buffer 非法
ERR_BASE64_ENCODE = -40009        # base64 加密失败
ERR_BASE64_DECODE = -40010        # base64 解密失败
ERR_GEN_XML = -40011              # 生成 XML 失败


# ---------------------------------------------------------------------------
# PKCS7 填充
# ---------------------------------------------------------------------------
class PKCS7Encoder:
    BLOCK_SIZE = 32

    @classmethod
    def encode(cls, text: bytes) -> bytes:
        amount_to_pad = cls.BLOCK_SIZE - (len(text) % cls.BLOCK_SIZE)
        if amount_to_pad == 0:
            amount_to_pad = cls.BLOCK_SIZE
        pad = bytes([amount_to_pad]) * amount_to_pad
        return text + pad

    @classmethod
    def decode(cls, decrypted: bytes) -> bytes:
        pad = decrypted[-1]
        if pad < 1 or pad > 32:
            pad = 0
        return decrypted[:-pad]


# ---------------------------------------------------------------------------
# SHA1 签名
# ---------------------------------------------------------------------------
class SHA1:
    @staticmethod
    def get_sha1(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
        """
        计算消息签名：对 [token, timestamp, nonce, encrypt] 排序后 SHA1。
        """
        sort_list = [token, timestamp, nonce, encrypt]
        sort_list.sort()
        sha = hashlib.sha1()
        sha.update("".join(sort_list).encode("utf-8"))
        return sha.hexdigest()


# ---------------------------------------------------------------------------
# XML 解析 / 生成
# ---------------------------------------------------------------------------
AES_TEXT_RESPONSE_TEMPLATE = (
    "<xml>"
    "<Encrypt><![CDATA[{encrypt}]]></Encrypt>"
    "<MsgSignature><![CDATA[{signature}]]></MsgSignature>"
    "<TimeStamp>{timestamp}</TimeStamp>"
    "<Nonce><![CDATA[{nonce}]]></Nonce>"
    "</xml>"
)


def extract_encrypt_from_xml(xml_text: str) -> str:
    """从 POST 请求体 XML 中提取 <Encrypt> 内容。"""
    try:
        tree = ET.fromstring(xml_text)
        return tree.find("Encrypt").text
    except Exception as exc:
        raise WXCryptError(ERR_PARSE_XML, f"XML 解析失败: {exc}") from exc


def build_response_xml(encrypt: str, signature: str, timestamp: str, nonce: str) -> str:
    """构造加密回复 XML。"""
    return AES_TEXT_RESPONSE_TEMPLATE.format(
        encrypt=encrypt,
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )


# ---------------------------------------------------------------------------
# AES 加解密
# ---------------------------------------------------------------------------
class Prpcrypt:
    def __init__(self, key: bytes):
        # key 长度必须为 32 字节（AES-256）
        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, text: str, receive_id: str) -> str:
        """
        加密明文消息。
        明文结构：16字节随机串 + 4字节消息长度(网络字节序) + 消息体 + ReceiveId
        """
        text_bytes = text.encode("utf-8")
        receive_id_bytes = receive_id.encode("utf-8")
        random_str = self._get_random_str().encode("utf-8")
        msg_len = struct.pack("!I", len(text_bytes))  # 网络字节序（大端）

        plain = random_str + msg_len + text_bytes + receive_id_bytes
        plain = PKCS7Encoder.encode(plain)

        cryptor = AES.new(self.key, self.mode, self.key[:16])
        cipher_bytes = cryptor.encrypt(plain)
        return base64.b64encode(cipher_bytes).decode("utf-8")

    def decrypt(self, text: str, receive_id: str) -> str:
        """
        解密密文消息，返回明文 XML 字符串。
        """
        try:
            cipher_bytes = base64.b64decode(text)
        except Exception as exc:
            raise WXCryptError(ERR_BASE64_DECODE, f"base64 解码失败: {exc}") from exc

        try:
            cryptor = AES.new(self.key, self.mode, self.key[:16])
            plain = cryptor.decrypt(cipher_bytes)
        except Exception as exc:
            raise WXCryptError(ERR_DECRYPT_AES, f"AES 解密失败: {exc}") from exc

        plain = PKCS7Encoder.decode(plain)

        # 去掉前 16 字节随机串，读取 4 字节长度
        content = plain[16:]
        xml_len = struct.unpack("!I", content[:4])[0]
        xml_content = content[4: xml_len + 4]
        from_receive_id = content[xml_len + 4:]

        if from_receive_id.decode("utf-8") != receive_id:
            raise WXCryptError(ERR_VALIDATE_CORPID, "ReceiveId 校验失败")

        return xml_content.decode("utf-8")

    @staticmethod
    def _get_random_str(length: int = 16) -> str:
        chars = string.ascii_letters + string.digits
        return "".join(random.sample(chars, length))


# ---------------------------------------------------------------------------
# 主接口类
# ---------------------------------------------------------------------------
class WXBizMsgCrypt:
    """
    企业微信消息加解密接口类。

    参数：
        token          企业微信后台配置的 Token
        encoding_aes_key  企业微信后台配置的 EncodingAESKey（43位）
        receive_id     企业 CorpID 或第三方 SuiteID
    """

    def __init__(self, token: str, encoding_aes_key: str, receive_id: str):
        if len(encoding_aes_key) != 43:
            raise WXCryptError(ERR_ILLEGAL_AES_KEY, "EncodingAESKey 长度必须为 43 位")
        self.token = token
        self.receive_id = receive_id
        self.key = base64.b64decode(encoding_aes_key + "=")
        if len(self.key) != 32:
            raise WXCryptError(ERR_ILLEGAL_AES_KEY, "AESKey 解码后长度必须为 32 字节")

    def verify_url(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        echostr: str,
    ) -> str:
        """
        验证回调 URL 有效性（处理 GET 请求）。

        企业微信在保存回调配置时，会发送 GET 请求携带加密的 echostr，
        服务端需验证签名并解密 echostr，将明文原样返回。

        返回：解密后的 echostr 明文字符串
        """
        # 1. 验证签名
        expected = SHA1.get_sha1(self.token, timestamp, nonce, echostr)
        if expected != msg_signature:
            raise WXCryptError(ERR_VALIDATE_SIGNATURE, "签名验证失败")

        # 2. 解密 echostr
        pc = Prpcrypt(self.key)
        return pc.decrypt(echostr, self.receive_id)

    def decrypt_msg(
        self,
        post_data: str,
        msg_signature: str,
        timestamp: str,
        nonce: str,
    ) -> str:
        """
        解密 POST 请求中的加密消息体。

        返回：解密后的消息明文 XML 字符串
        """
        # 1. 从 XML 中提取 Encrypt 字段
        encrypt = extract_encrypt_from_xml(post_data)

        # 2. 验证签名
        expected = SHA1.get_sha1(self.token, timestamp, nonce, encrypt)
        if expected != msg_signature:
            raise WXCryptError(ERR_VALIDATE_SIGNATURE, "签名验证失败")

        # 3. 解密
        pc = Prpcrypt(self.key)
        return pc.decrypt(encrypt, self.receive_id)

    def encrypt_msg(
        self,
        reply_msg: str,
        nonce: str,
        timestamp: str | None = None,
    ) -> str:
        """
        加密回复消息，返回可直接作为响应体的 XML 字符串。

        参数：
            reply_msg  待加密的明文 XML 消息
            nonce      随机字符串（可使用请求中的 nonce）
            timestamp  时间戳，为 None 时自动使用当前时间
        """
        if timestamp is None:
            timestamp = str(int(time.time()))

        pc = Prpcrypt(self.key)
        encrypt = pc.encrypt(reply_msg, self.receive_id)

        signature = SHA1.get_sha1(self.token, timestamp, nonce, encrypt)
        return build_response_xml(encrypt, signature, timestamp, nonce)
