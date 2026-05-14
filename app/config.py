# -*- coding: utf-8 -*-
"""
应用配置管理

通过环境变量或 .env 文件加载敏感配置。
请勿将真实的 Token / AESKey / CorpID 硬编码在代码中。

所需环境变量：
  WECOM_TOKEN              企业微信后台配置的 Token
  WECOM_ENCODING_AES_KEY   企业微信后台配置的 EncodingAESKey（43位）
  WECOM_CORP_ID            企业 CorpID（以 ww 开头）

可选环境变量：
  APP_HOST                 服务监听地址，默认 0.0.0.0
  APP_PORT                 服务监听端口，默认 9002
  LOG_LEVEL                日志级别，默认 INFO
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 企业微信配置（必填）
    WECOM_TOKEN: str = ""
    WECOM_ENCODING_AES_KEY: str = ""
    WECOM_CORP_ID: str = ""

    # 服务配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 9002
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
