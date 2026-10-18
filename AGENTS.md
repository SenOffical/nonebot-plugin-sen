# Sen NoneBot2 — AI 协作开发指南

## 职责

`nonebot2/` 是 Sen 机器人端的 NoneBot2/Python 实现，用于替代旧 `koishi-bot/` 的运行时。后端 Bot API 为 `/api/v1/bot/*`，鉴权头 `X-Bot-Secret`。

## 目录结构

本仓库在 Forest 中的目录名为 `nonebot-plugin-sen/`；生产机与 `docker-compose.yml` 检出目录名为 `nonebot2/`（见 Forest 根目录 `deploy/AGENTS.md`）。下文树内路径均为仓库内相对路径。

```
nonebot2/
├── bot.py                  # NoneBot2 应用入口，注册 OneBot V11 与 Telegram 适配器；含 Telegram API 硬超时补丁与命令菜单自动配置
├── sen_bot/
│   ├── __init__.py         # 插件元信息（PluginMetadata），末尾导入 commands 注册命令 matcher
│   ├── backend.py          # 后端 API 客户端、错误码映射、日志脱敏
│   ├── config.py           # 环境变量配置、allowedGroups JSON 解析
│   ├── membership.py       # Redis 正向群成员缓存与平台 Bot API 校验
│   ├── membership_watch.py # Telegram 群成员变动事件处理与后端上报
│   ├── models.py           # Pydantic 数据模型，兼容 camelCase/snake_case
│   ├── platform.py         # NoneBot 事件到 Sen 平台上下文的转换
│   └── commands/           # 每个用户命令一个文件，各自用 on_command 注册 matcher
│       ├── __init__.py     # 包初始化，导入所有命令模块以触发 matcher 注册
│       ├── catalog.py      # 命令目录单一数据源（名称/参数/功能说明/样例），纯数据、无 matcher
│       ├── shared.py       # 共享上下文、授权守卫、参数校验工具
│       ├── start.py        # /start 与 /help 帮助引导命令（HELP_TEXT 由 catalog 生成）
│       ├── register.py     # /register 注册命令
│       ├── bind.py         # /bind 绑定 UID 命令
│       ├── unbind.py       # /unbind 解绑 UID 命令
│       ├── secret.py       # /secret 密钥重置命令
│       ├── info.py         # /info 账号信息查询命令
│       ├── sync.py         # /sync 平台绑定同步命令
│       └── merge.py        # /merge 账号合并命令
├── tests/                  # pytest 单元测试
├── Dockerfile              # Python 3.12 + uv 容器构建
├── pyproject.toml          # 依赖、pytest、ruff、pyright、[tool.nonebot] 配置
└── uv.lock                 # uv 依赖锁定文件，Dockerfile 构建时与 pyproject.toml 一起 COPY
```

## 关键设计

- **命令注册**: 每个命令文件在模块顶层使用 `on_command("name")` 定义 `*_matcher`，通过 `@matcher.handle()` 装饰器注册处理函数。`commands/__init__.py` 导入所有命令模块以触发 matcher 注册。
- **插件加载**: `bot.py` 使用 `nonebot.load_plugin("sen_bot")` 加载单一插件；`sen_bot/__init__.py` 导入 `commands` 包，`commands/__init__.py` 再导入各命令模块以触发 matcher 注册。`commands/` 需要 `__init__.py` 才能被识别为合法 Python 包。
- **Matcher 模式**: 每个命令文件分为「纯业务处理函数（可独立测试）」和「NoneBot2 Matcher」两段。Matcher handler 负责构建上下文、权限校验，然后调用纯处理函数。
- **权限守卫**: `shared.py` 提供 `build_command_context()` 构建命令上下文和 `check_authorized()` 执行允许群验证。Matcher handler 负责调用守卫，处理函数保持纯逻辑。
- 所有私聊命令都通过 `check_authorized()` 统一执行允许群守卫。
- 允许群配置只使用 `SEN_ALLOWED_GROUPS` JSON 数组，字段为 `id` 与可选 `desc`；业务只使用 `id`。
- Redis 只缓存正向群成员结果，值为 `active:v3`，key 为 `SEN_MEMBERSHIP_CACHE_KEY_PREFIX`（默认 `sen:membership`）+ 平台、群 ID、用户 ID。
- Telegram 群成员状态只接受 `creator`、`administrator`、`member`，以及 `restricted` 且 `is_member=true`；`left` / `kicked` 必须拒绝。
- API 日志必须通过 `redact_for_log()` 脱敏，不能记录 secret/password/token 明文。
- 每个生产函数和方法都保留中文 docstring，新增函数时同步补齐参数说明，避免 IDE 与 lint 体验退化。
- **命令目录单一数据源**: `commands/catalog.py` 以纯数据 `CommandSpec`（`name`/`args`/`summary`/`example`）定义全部用户命令；`start.py` 的 `HELP_TEXT` 与 `bot.py` 的 Telegram 命令菜单均由它生成，避免命令文案多处重复。新增/修改命令时需同步更新该目录。
- `pyproject.toml` 的 `[tool.nonebot]` 区段声明了适配器和插件目录。
- **Telegram 命令菜单**: `bot.py` 通过 `on_bot_connect` 钩子在 Telegram Bot 连接成功后调用 `setMyCommands` 自动写入命令菜单，菜单条目由 `build_telegram_command_menu()` 从 `commands/catalog.py` 单一数据源生成，与 `/start` 帮助文本天然一致。
- **群成员变动事件**: Telegram 的 `allowed_updates` 默认**不含** `chat_member`，因此 `bot.py` 的 `patch_telegram_allowed_updates()` 包装 `TelegramAdapter._call_api`，为 `get_updates` 补充白名单；`membership_watch.py` 再用 `on_notice` 接住 `ChatMemberUpdatedEvent`，把 `left` / `kicked` 整理成载荷 POST 给 `<SEN_API_BASE_URL>/membership-events`。前提是 bot 必须是群管理员。

## 群成员变动事件

- **订阅前提**: 两件事缺一不可——bot 是群管理员（Telegram 侧限制）、`getUpdates` 的 `allowed_updates` 显式包含 `chat_member`（适配器默认不传）。后者由 `patch_telegram_allowed_updates()` 在 `register_adapter` 之前打补丁完成。
- **取用户 ID**: 必须用 `event.new_chat_member.user.id`。`event.from_` 是「触发变化的人」，被移出时它是操作的管理员而非被移出者，误用会封错账号。
- **过滤条件**: 只处理 `left` / `kicked`，且群 ID 必须在 `SEN_ALLOWED_GROUPS` 中；入群、提权等其他状态一律忽略。
- **上报**: 事件通道与 `/api/v1/bot/*` 同向（bot → 后端），因此复用 `SEN_API_BASE_URL` 与 `SEN_BOT_SECRET`，不引入任何额外配置。收到 `left` / `kicked` 后无条件 POST 到 `<SEN_API_BASE_URL>/membership-events`，由后端决定封禁或删除；上报失败只告警，不影响命令功能。
- **不能替代定时校验**: `getUpdates` 只保留 24 小时，bot 停机超过一天事件永久丢失，因此事件是加速通道，仍需定时脚本兜底。

## 验证

```bash
uv run pytest -q
uv run ruff check .
uv run pyright
```

## 文档同步

修改 `nonebot2/` 下代码、配置、Docker 或测试后，必须同步更新本文件。

## Docker 部署

- **多阶段构建**：builder 阶段用 `COPY --from=ghcr.io/astral-sh/uv:latest` 装 uv + `uv sync --frozen --no-dev` 装依赖；runtime 阶段只拷贝 `.venv`、源码目录和入口脚本。镜像体积小、无构建工具残留。
- **一致模式**：backend 和 bot 使用完全相同的 Dockerfile 结构（`FROM python:3.12-slim AS builder` → `FROM python:3.12-slim`），仅拷贝的源码路径不同。
- **运行时不含 uv**：venv 已加入 `PATH`，CMD 直接执行 `python <入口>`，无需 `uv run`；镜像与 `docker-compose.yml` 同样未定义 HEALTHCHECK。
- 敏感配置通过 `.env` 卷挂载注入（`SEN_BOT_SECRET`，兼容旧 `KOISHI_SECRET` 等），`docker-compose.yml` 的 `environment` 只设置容器内必须覆盖的变量（`HOST`、`PORT`、`SEN_API_BASE_URL`）。
- Telegram 代理通过 `TELEGRAM_PROXY` 环境变量 / `.env` 配置（由 `nonebot-adapter-telegram` 适配器读取，非本仓库代码定义），Adapter 原生支持 `proxy` 字段（别名 `telegram_proxy`）。格式如 `socks5://host:port`。
- 单个 bot 可配置独立 API 服务器：`TELEGRAM_BOTS`（JSON 数组，由 nonebot-adapter-telegram 适配器读取，非本仓库 config.py 定义）中每个对象可含 `api_server`。

## CI/CD（GitHub Actions）

- **工作流文件**：`.github/workflows/docker-publish.yml`，仅在推送 `v*` 格式 tag 时触发（如 `v1.2.3`），构建镜像并推送至私有仓库 `registry.19960222.xyz/sen/nonebot2`。非 tag push（含 main 分支）不会触发。
- **镜像标签**：由 `docker/metadata-action` 依据 git tag 自动生成 `v1.2.3`、`1.2.3`、`1.2` 与 `latest` 四种标签，指向同一镜像。
- **凭据**：私有仓库账号密码通过仓库 Secrets `REGISTRY_USERNAME` / `REGISTRY_PASSWORD` 注入，切勿硬编码。首次使用需在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置。
- **构建缓存**：使用 `type=gha` 的 GitHub Actions 缓存，加速依赖层与 uv sync 的复用；Dockerfile 保持多阶段结构不变。

## Telegram 假死防护（bot.py 硬超时补丁）

- **问题背景**：Telegram 适配器 `poll()` 使用 `getUpdates(timeout=30)` 长轮询，经 HTTP 代理（`TELEGRAM_PROXY`）转发时，代理或 NAT 可能静默丢弃 CONNECT 隧道（无 FIN/RST）。适配器构造请求不带 timeout，NoneBot httpx 驱动回退超时中 `write`/`pool` 为无限，导致该次 await 永久挂起——进程与端口仍存活（当前未配置任何 healthcheck），但轮询死亡，表现为机器人"假死"且容器不重启。
- **修复方式**：`bot.py` 的 `patch_telegram_api_timeout()` 在 `register_adapter` 之前包装 `TelegramAdapter._call_api`，用 `asyncio.wait_for(90s)` 限时。超时抛出的 `TimeoutError` 会被轮询循环 `except Exception` 捕获并自动重试，实现自愈。
- **参数约定**：硬超时常量 `TELEGRAM_API_HARD_TIMEOUT = 90.0`，约为长轮询参数 30 秒的 3 倍；调整 getUpdates 轮询时长时必须同步评估该值。
- **注意事项**：升级 nonebot-adapter-telegram 后如 `_call_api` 签名变化，需同步调整补丁包装签名；不要在补丁内做重试（外层 poll 循环已负责重试）。

## Telegram 命令菜单（bot.py 自动配置）

- **目的**：Telegram 客户端默认不展示 Bot 命令菜单，需主动调用 Bot API `setMyCommands` 写入，用户才能通过菜单按钮查看并触发命令。
- **实现方式**：`bot.py` 的 `setup_telegram_command_menu(driver)` 在 `main()` 中通过 `driver.on_bot_connect` 注册钩子；钩子在每个 Bot 连接成功后触发，用 `isinstance` 判定仅对 Telegram `Bot` 生效（OneBot 等其他适配器跳过），随后调用 `bot.set_my_commands(...)`。
- **命令来源**：命令与描述来自单一数据源 `sen_bot/commands/catalog.py`（`HELP_COMMAND` 与 `COMMAND_CATALOG`），`bot.py` 的 `build_telegram_command_menu()` 延迟导入并组装（帮助命令置顶）。`command` 不含前导斜杠且须满足 Telegram 约束（1-32 字符，仅小写字母/数字/下划线），`description`（即 `summary`）为 1-256 字符纯文本。新增或删除用户命令时，只需改 `catalog.py`，`HELP_TEXT` 与菜单会自动同步，并需同步补充 `tests/test_bot_menu.py`。
- **延迟导入原因**：`sen_bot` 包导入会执行各命令模块顶层的 `on_command()`，而 `on_command` 依赖 `get_driver()`，必须在 `nonebot.init()` 之后。因此 `bot.py` 不在模块顶层导入 `sen_bot.*`，而是在运行时钩子内延迟导入 `catalog`。
- **容错**：`set_my_commands` 失败仅记录 `logger.warning`，不中断启动与轮询。
- **测试**：`tests/test_bot_menu.py` 校验命令名合法性、描述长度、命令名唯一性、菜单与 `catalog` 一致性及 `HELP_TEXT` 渲染覆盖，无需真实 Telegram 连接。
