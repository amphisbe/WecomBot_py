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
import os
import sys
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.callback import router as callback_router


# ---------------------------------------------------------------------------
# 日志配置（同时输出到控制台和滚动日志文件）
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    """
    初始化日志系统：
      - 控制台（stdout）：实时查看运行状态
      - 文件（logs/wecombot.log）：持久化记录，按大小轮转（10 MB × 5 个备份）
    日志目录不存在时自动创建。
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "wecombot.log")

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    # 文件 Handler（按大小轮转：单文件最大 10 MB，保留最近 5 个备份）
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler],
    )

    logging.getLogger(__name__).info(
        "日志系统已初始化，日志文件：%s，级别：%s",
        log_file,
        settings.LOG_LEVEL.upper(),
    )


_setup_logging()
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
