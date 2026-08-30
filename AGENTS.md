# Sen NoneBot2 — AI 协作开发指南

## 职责

`nonebot2/` 是 Sen 机器人端的 NoneBot2/Python 实现，用于替代旧 `koishi-bot/` 的运行时。后端仍沿用 `/api/v1/koishi/*` 兼容 API 和 `X-Koishi-Secret` 鉴权头。

## 目录结构

```
nonebot2/
├── bot.py                  # NoneBot2 应用入口，注册 OneBot V11 与 Telegram 适配器；含 Telegram API 硬超时补丁
├── sen_bot/
│   ├── __init__.py         # 插件元信息（PluginMetadata），无主动加载逻辑
│   ├── backend.py          # 后端 API 客户端、错误码映射、日志脱敏
│   ├── config.py           # 环境变量配置、allowedGroups JSON 解析
│   ├── membership.py       # Redis 正向群成员缓存与平台 Bot API 校验
│   ├── models.py           # Pydantic 数据模型，兼容 camelCase/snake_case
│   ├── platform.py         # NoneBot 事件到 Sen 平台上下文的转换
│   └── commands/           # 每个用户命令一个文件，各自用 on_command 注册 matcher
│       ├── __init__.py     # 包初始化，导入所有命令模块以触发 matcher 注册
│       ├── shared.py       # 共享上下文、授权守卫、参数校验工具
│       ├── register.py     # /register 注册命令
│       ├── bind.py         # /bind 绑定 UID 命令
│       ├── unbind.py       # /unbind 解绑 UID 命令
│       ├── secret.py       # /secret 密钥重置命令
│       ├── info.py         # /info 账号信息查询命令
│       ├── sync.py         # /sync 平台绑定同步命令
│       └── merge.py        # /merge 账号合并命令
├── tests/                  # pytest 单元测试
├── Dockerfile              # Python 3.12 + uv 容器构建
└── pyproject.toml          # 依赖、pytest、ruff、pyright、[tool.nonebot] 配置
```

## 关键设计

- **命令注册**: 每个命令文件在模块顶层使用 `on_command("name")` 定义 `*_matcher`，通过 `@matcher.handle()` 装饰器注册处理函数。`commands/__init__.py` 导入所有命令模块以触发 matcher 注册。
- **插件加载**: `bot.py` 使用 `load_plugins("sen_bot")`，NoneBot2 自动发现 `sen_bot/` 下所有模块（含子目录）为插件。`commands/` 需要 `__init__.py` 才能被识别为合法 Python 包。
- **Matcher 模式**: 每个命令文件分为「纯业务处理函数（可独立测试）」和「NoneBot2 Matcher」两段。Matcher handler 负责构建上下文、权限校验，然后调用纯处理函数。
- **权限守卫**: `shared.py` 提供 `build_command_context()` 构建命令上下文和 `check_authorized()` 执行允许群验证。Matcher handler 负责调用守卫，处理函数保持纯逻辑。
- 所有私聊命令都通过 `check_authorized()` 统一执行允许群守卫。
- 允许群配置只使用 `SEN_ALLOWED_GROUPS` JSON 数组，字段为 `id` 与可选 `desc`；业务只使用 `id`。
- Redis 只缓存正向群成员结果，值为 `active:v3`，key 包含平台、群 ID、用户 ID。
- Telegram 群成员状态只接受 `creator`、`administrator`、`member`，以及 `restricted` 且 `is_member=true`；`left` / `kicked` 必须拒绝。
- API 日志必须通过 `redact_for_log()` 脱敏，不能记录 secret/password/token 明文。
- 每个生产函数和方法都保留中文 docstring，新增函数时同步补齐参数说明，避免 IDE 与 lint 体验退化。
- `pyproject.toml` 的 `[tool.nonebot]` 区段声明了适配器和插件目录。

## 验证

```bash
uv run pytest -q
uv run ruff check .
uv run pyright
```

## 文档同步

修改 `nonebot2/` 下代码、配置、Docker 或测试后，必须同步更新本文件；如新增 Claude 专用规则，同步更新 `CLAUDE.md`。


## Docker 部署

- **多阶段构建**：builder 阶段用 `COPY --from=ghcr.io/astral-sh/uv:latest` 装 uv + `uv sync --frozen --no-dev` 装依赖；runtime 阶段只拷贝 `.venv`、源码目录和入口脚本。镜像体积小、无构建工具残留。
- **一致模式**：backend 和 bot 使用完全相同的 Dockerfile 结构（`FROM python:3.12-slim AS builder` → `FROM python:3.12-slim`），仅拷贝的源码路径不同。
- **运行时不含 uv**：venv 已加入 `PATH`，CMD 直接执行 `python <入口>`，无需 `uv run`。healthcheck 同理。
- 敏感配置通过 `.env` 卷挂载注入（`KOISHI_SECRET` 等），`docker-compose.yml` 的 `environment` 只设置容器内必须覆盖的变量（`HOST`、`PORT`、`SEN_API_BASE_URL`）。
- Telegram 代理通过 `TELEGRAM_PROXY` 环境变量 / `.env` 配置，NoneBot2 Telegram Adapter 原生支持 `proxy` 字段（别名 `telegram_proxy`）。格式如 `socks5://host:port`。
- 单个 bot 可配置独立 API 服务器：`TELEGRAM_BOTS`（JSON 数组）中每个对象可含 `api_server`。

## Telegram 假死防护（bot.py 硬超时补丁）

- **问题背景**：Telegram 适配器 `poll()` 使用 `getUpdates(timeout=30)` 长轮询，经 HTTP 代理（`TELEGRAM_PROXY`）转发时，代理或 NAT 可能静默丢弃 CONNECT 隧道（无 FIN/RST）。适配器构造请求不带 timeout，NoneBot httpx 驱动回退超时中 `write`/`pool` 为无限，导致该次 await 永久挂起——进程与端口仍存活（healthcheck 仅探测 TCP），但轮询死亡，表现为机器人"假死"且容器不重启。
- **修复方式**：`bot.py` 的 `patch_telegram_api_timeout()` 在 `register_adapter` 之前包装 `TelegramAdapter._call_api`，用 `asyncio.wait_for(90s)` 限时。超时抛出的 `TimeoutError` 会被轮询循环 `except Exception` 捕获并自动重试，实现自愈。
- **参数约定**：硬超时常量 `TELEGRAM_API_HARD_TIMEOUT = 90.0`，约为长轮询参数 30 秒的 3 倍；调整 getUpdates 轮询时长时必须同步评估该值。
- **注意事项**：升级 nonebot-adapter-telegram 后如 `_call_api` 签名变化，需同步调整补丁包装签名；不要在补丁内做重试（外层 poll 循环已负责重试）。

