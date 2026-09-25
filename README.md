# Sen NoneBot2 Bot

这是 Sen 机器人端的 NoneBot2 实现，覆盖旧 Koishi 插件的用户注册、平台绑定、支付宝 UID 绑定、账号信息查询、secret 更新和账号合并命令。

## 命令

- `/start` / `/help` — 显示帮助与命令列表
- `/register` — 注册 Sen 账号
- `/bind <16位支付宝UID>` — 绑定支付宝 UID
- `/unbind <16位支付宝UID>` — 解绑支付宝 UID
- `/secret` — 重新生成 secret
- `/info` — 查询用户 ID、secret、支付宝 UID 和平台绑定
- `/sync <secret>` — 将当前平台绑定到已有用户
- `/merge <secret>` — 合并当前平台账号到目标用户

## 运行

```bash
uv sync
uv run python bot.py
```

## 配置

- `SEN_API_BASE_URL`：后端 `/api/v1/bot` 地址。
- `SEN_BOT_SECRET`：后端 `X-Bot-Secret` 鉴权密钥（兼容旧 `KOISHI_SECRET`）。
- `SEN_ALLOWED_GROUPS`：允许群 JSON 数组，例如 `[{"id":"-1001","desc":"主群"}]`。
- `SEN_MEMBERSHIP_CACHE_ENABLED`：是否启用 Redis 正向群成员缓存。
- `SEN_REDIS_HOST` / `SEN_REDIS_PORT` / `SEN_REDIS_PASSWORD` / `SEN_REDIS_DB`：Redis 连接参数。
- `SEN_MEMBERSHIP_CACHE_TTL_DAYS`：正向成员缓存 TTL，默认 7 天。
- `SEN_MEMBERSHIP_CACHE_KEY_PREFIX`：Redis 群成员缓存 key 前缀，默认 `sen:membership`。
- `SEN_BACKEND_TIMEOUT_SECONDS`：后端 HTTP 请求超时时间，默认 10 秒。
- `SEN_PLATFORM_API_RETRY_TIMES`：平台 Bot API 临时失败后的重试次数，默认 2 次。
- `SEN_PLATFORM_API_RETRY_INTERVAL_SECONDS`：平台 Bot API 重试间隔秒数，默认 1.0 秒。

## Docker

根目录 `docker-compose.yml` 的 `bot` 服务构建本目录。生产环境至少需要配置 `.env` 中的 `SEN_BOT_SECRET` 和适配器自身需要的 token / 连接参数。

