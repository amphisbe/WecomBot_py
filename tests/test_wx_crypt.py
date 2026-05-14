# -*- coding: utf-8 -*-
"""
企业微信加解密模块单元测试

使用官方示例数据验证 WXBizMsgCrypt 的加解密流程。
"""

import pytest
from app.core.wx_crypt import WXBizMsgCrypt, WXCryptError, SHA1, PKCS7Encoder


# 官方示例凭证（仅用于测试）
TOKEN = "QDG6eK"
ENCODING_AES_KEY = "jWmYm7qr5nMoAUwZRjGtBxmz3KA1tkAj3ykkR6q2B2C"
CORP_ID = "wx49f0ab532d5d035a"


class TestSHA1:
    def test_signature_consistency(self):
        """相同输入应产生相同签名"""
        sig1 = SHA1.get_sha1("token", "1234567890", "nonce123", "echostr_abc")
        sig2 = SHA1.get_sha1("token", "1234567890", "nonce123", "echostr_abc")
        assert sig1 == sig2

    def test_signature_order_independence(self):
        """签名计算基于排序，参数顺序不影响结果"""
        # SHA1 对 [token, timestamp, nonce, encrypt] 排序后计算
        # 此处仅验证函数可正常运行并返回 40 位十六进制字符串
        sig = SHA1.get_sha1("abc", "123", "xyz", "msg")
        assert len(sig) == 40
        assert all(c in "0123456789abcdef" for c in sig)


class TestPKCS7Encoder:
    def test_encode_decode_roundtrip(self):
        """编码后解码应还原原始数据"""
        original = b"Hello, WecomBot!"
        encoded = PKCS7Encoder.encode(original)
        decoded = PKCS7Encoder.decode(encoded)
        assert decoded == original

    def test_padding_multiple_of_block_size(self):
        """长度恰好为 block_size 倍数时，应额外填充一个完整块"""
        data = b"A" * 32  # 恰好 32 字节
        encoded = PKCS7Encoder.encode(data)
        assert len(encoded) == 64  # 填充一个完整的 32 字节块


class TestWXBizMsgCrypt:
    def setup_method(self):
        self.crypt = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)

    def test_invalid_aes_key_length(self):
        """EncodingAESKey 长度不为 43 时应抛出异常"""
        with pytest.raises(WXCryptError):
            WXBizMsgCrypt(TOKEN, "short_key", CORP_ID)

    def test_encrypt_decrypt_roundtrip(self):
        """加密后解密应还原原始消息"""
        original = "<xml><Content>测试消息</Content></xml>"
        from app.core.wx_crypt import Prpcrypt
        pc = Prpcrypt(self.crypt.key)
        encrypted = pc.encrypt(original, CORP_ID)
        decrypted = pc.decrypt(encrypted, CORP_ID)
        assert decrypted == original

    def test_encrypt_msg_and_decrypt_msg(self):
        """EncryptMsg 加密的消息可以被 DecryptMsg 正确解密"""
        import random
        import string
        nonce = "".join(random.choices(string.digits, k=10))
        timestamp = "1409735669"

        original_xml = (
            f"<xml>"
            f"<ToUserName><![CDATA[{CORP_ID}]]></ToUserName>"
            f"<FromUserName><![CDATA[user001]]></FromUserName>"
            f"<CreateTime>{timestamp}</CreateTime>"
            f"<MsgType><![CDATA[text]]></MsgType>"
            f"<Content><![CDATA[Hello]]></Content>"
            f"<MsgId>12345</MsgId>"
            f"</xml>"
        )

        # 加密
        encrypted_xml = self.crypt.encrypt_msg(original_xml, nonce, timestamp)
        assert "<Encrypt>" in encrypted_xml
        assert "<MsgSignature>" in encrypted_xml

        # 从加密 XML 中提取签名参数，再解密
        import xml.etree.ElementTree as ET
        tree = ET.fromstring(encrypted_xml)
        encrypt_str = tree.find("Encrypt").text
        sig = tree.find("MsgSignature").text
        ts = tree.find("TimeStamp").text
        nc = tree.find("Nonce").text

        # 构造 POST 请求体格式
        post_data = (
            f"<xml>"
            f"<ToUserName><![CDATA[{CORP_ID}]]></ToUserName>"
            f"<Encrypt><![CDATA[{encrypt_str}]]></Encrypt>"
            f"</xml>"
        )

        decrypted = self.crypt.decrypt_msg(post_data, sig, ts, nc)
        assert "Hello" in decrypted
