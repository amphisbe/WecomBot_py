# -*- coding: utf-8 -*-
"""
企业微信智能机器人回调服务 —— FastAPI 应用主入口

启动方式：
  uvicorn app.main:app --host 0.0.0.0 --port 9002

或直接运行本文件：
  python -m app.main
"""

import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.callback import router as callback_router

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FastAPI 应用实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="WecomBot 企业微信智能机器人回调服务",
    description=(
        "基于 FastAPI 实现的企业微信智能机器人 URL 回调接收服务，"
        "支持 URL 有效性验证（GET）和加密消息接收（POST）。"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 允许跨域（按需配置）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(callback_router, tags=["企业微信回调"])


# ---------------------------------------------------------------------------
# 健康检查端点
# ---------------------------------------------------------------------------
@app.get("/health", summary="健康检查", tags=["系统"])
async def health_check():
    """返回服务运行状态。"""
    return {"status": "ok", "service": "WecomBot"}


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(
        "启动 WecomBot 服务，监听 %s:%d",
        settings.APP_HOST,
        settings.APP_PORT,
    )
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
