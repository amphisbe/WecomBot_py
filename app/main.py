# -*- coding: utf-8 -*-
"""
企业微信智能机器人回调服务 —— FastAPI 应用主入口

启动方式（推荐，自动读取 .env 中的 APP_HOST / APP_PORT）：
  python -m app.main
  python run.py

使用 uvicorn 命令行启动时，host/port 须手动指定（uvicorn 不执行
__main__ 块，无法自动读取 .env 中的 APP_HOST/APP_PORT）：
  uvicorn app.main:app --host 0.0.0.0 --port 9002

若希望 uvicorn 命令行也能读取 .env，可借助 python-dotenv 在 shell
中预先导出环境变量，或直接使用 `python run.py`。
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
# 启动函数（供 run.py 和 python -m app.main 复用）
# ---------------------------------------------------------------------------
def start() -> None:
    """从 settings（.env 文件或环境变量）读取 host/port 并启动 uvicorn。"""
    logger.info(
        "启动 WecomBot 服务，监听 %s:%d（来源：.env / 环境变量）",
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


# ---------------------------------------------------------------------------
# 直接运行入口：python -m app.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    start()
