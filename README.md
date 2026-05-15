# WecomBot_py

基于 **FastAPI** 框架实现的企业微信智能机器人 URL 回调接收服务。

## 功能特性

- **URL 有效性验证**（GET）：响应企业微信配置回调地址时的验证请求，完成签名校验与 echostr 解密。
- **加密消息接收**（POST）：接收企业微信推送的加密消息，完成签名验证、AES-256-CBC 解密、消息解析与业务分发。
- **被动消息回复**：支持将回复消息加密后以 XML 格式返回给企业微信。
- **多消息类型支持**：文本、图片、语音、视频、位置、链接、事件消息。
- **配置安全**：敏感凭证通过环境变量或 `.env` 文件管理，不入代码库。

## 接口说明

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/work/bot/callback` | 企业微信验证回调 URL 有效性 |
| POST | `/work/bot/callback` | 接收企业微信推送的加密消息 |
| GET  | `/health` | 服务健康检查 |
| GET  | `/docs`   | Swagger UI 接口文档 |

**完整回调地址示例：**
```
http://bot.qianjing.tech:9002/work/bot/callback
```

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/amphisbe/WecomBot_py.git
cd WecomBot_py
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例配置文件并填入真实值：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```dotenv
WECOM_TOKEN=your_token_here
WECOM_ENCODING_AES_KEY=your_encoding_aes_key_here
WECOM_CORP_ID=wwxxxxxxxxxxxxxxxxxx
APP_PORT=9002
LOG_LEVEL=INFO
```

> **如何获取这三个值？**
> 登录企业微信管理后台 → 应用管理 → 选择智能机器人 → API 模式 → 设置接收消息回调地址，
> 页面上可生成或查看 Token 和 EncodingAESKey；CorpID 在「我的企业 → 企业信息」中查看。

### 4. 启动服务

**推荐方式（自动读取 `.env` 中的 `APP_HOST` / `APP_PORT`）：**

```bash
# 方式一：使用根目录快捷脚本
python run.py

# 方式二：以模块方式运行
python -m app.main
```

> 以上两种方式均会在启动时自动加载 `.env` 文件，无需手动指定 `--host` 和 `--port`。

**使用 uvicorn 命令行启动（需手动指定参数）：**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9002
```

> `uvicorn` 命令行直接加载 `app` 对象，不执行 `__main__` 块，因此无法自动读取 `.env` 中的 `APP_HOST` / `APP_PORT`，需手动传入。

### 5. 在企业微信后台配置回调地址

在智能机器人的「API 模式 → 设置接收消息回调地址」中填写：

```
http://bot.qianjing.tech:9002/work/bot/callback
```

点击「保存」，企业微信会向该地址发送 GET 验证请求，验证通过后配置生效。

## 项目结构

```
WecomBot_py/
├── app/
│   ├── main.py              # FastAPI 应用入口 + start() 启动函数
│   ├── config.py            # 配置管理（pydantic-settings，自动读取 .env）
│   ├── core/
│   │   ├── wx_crypt.py      # 企业微信消息加解密（AES-256-CBC + SHA1 签名）
│   │   └── msg_parser.py    # 消息 XML 解析与回复构造
│   ├── routers/
│   │   └── callback.py      # GET/POST 回调路由
│   └── handlers/
│       └── message_handler.py  # 消息业务处理分发器
├── tests/
│   └── test_wx_crypt.py     # 加解密单元测试
├── run.py                   # 快捷启动脚本（自动读取 .env）
├── .env.example             # 环境变量配置示例
├── requirements.txt         # Python 依赖
└── README.md
```

## 扩展业务逻辑

在 `app/handlers/message_handler.py` 中修改各类型消息的处理函数，例如接入大语言模型：

```python
def _handle_text(msg: TextMessage) -> Optional[str]:
    # 调用 LLM API 获取回复
    reply = call_llm(msg.content)
    return build_text_reply(
        to_user=msg.from_user_name,
        from_user=msg.to_user_name,
        content=reply,
        agent_id=msg.agent_id,
    )
```

## 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 依赖说明

| 包 | 版本 | 用途 |
|---|---|---|
| fastapi | ≥0.111 | Web 框架 |
| uvicorn | ≥0.29 | ASGI 服务器 |
| pydantic-settings | ≥2.2 | 配置管理 |
| pycryptodome | ≥3.20 | AES-256-CBC 加解密 |

## 参考文档

- [企业微信回调配置说明](https://developer.work.weixin.qq.com/document/path/91116)
- [企业微信加解密库](https://developer.work.weixin.qq.com/document/path/90468)
- [企业微信智能机器人长连接](https://developer.work.weixin.qq.com/document/path/101463)
