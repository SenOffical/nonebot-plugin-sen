"""帮助与引导命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher

from .shared import build_command_context, check_authorized, md_bold, send_reply

HELP_TEXT = "\n".join([
    "本机器人提供 Sen 账号注册、支付宝 UID 绑定与账号信息查询服务。",
    "你可以通过此机器人自助完成以下操作：",
    "",
    "📖 " + md_bold("可用命令列表"),
    "",
    r"\- /register",
    "    功能说明: 注册 Sen 账号并获取访问密钥",
    "    使用样例: /register",
    "",
    r"\- /info",
    "    功能说明: 查询当前账号信息（绑定 UID / 平台关联 / 密钥）",
    "    使用样例: /info",
    "",
    r"\- /bind \<支付宝UID\>",
    "    功能说明: 将支付宝 UID 绑定到当前账号",
    "    使用样例: /bind xxxxxxxxxxxxxxxx",
    "",
    r"\- /unbind \<支付宝UID\>",
    "    功能说明: 解绑已关联的支付宝 UID",
    "    使用样例: /unbind xxxxxxxxxxxxxxxx",
    "",
    r"\- /secret",
    "    功能说明: 重新生成访问密钥（旧密钥立即失效）",
    "    使用样例: /secret",
    "",
    r"\- /sync \<密钥\>",
    "    功能说明: 用密钥同步当前平台账号到已有 Sen 账号",
    "    使用样例: /sync sk\-xxxx\-xxxx\-xxxx\-xxxx",
    "",
    r"\- /merge \<密钥\>",
    "    功能说明: 将当前平台账号合并到密钥对应的 Sen 账号",
    "    使用样例: /merge sk\-xxxx\-xxxx\-xxxx\-xxxx",
    "",
    "💡 请在群内私聊此机器人使用以上命令。",
])


# ── NoneBot2 Matcher ──────────────────────────────────────────

start_matcher = on_command("start", aliases={"help", "/start", "/help"}, priority=10)


@start_matcher.handle()
async def _(bot: Bot, event: Event, matcher: Matcher) -> None:
    """接收 /start 或 /help 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    await send_reply(matcher, event, HELP_TEXT)
