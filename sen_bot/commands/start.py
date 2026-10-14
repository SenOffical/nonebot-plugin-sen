"""帮助与引导命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher

from .catalog import COMMAND_CATALOG
from .shared import build_command_context, check_authorized, escape_md_v2, md_bold, send_reply


def _build_help_text() -> str:
    """根据命令目录生成 /start 帮助文本（Telegram MarkdownV2）。

    命令签名、功能说明与使用样例均取自 `COMMAND_CATALOG` 单一数据源，
    其中的 MarkdownV2 特殊字符经 `escape_md_v2` 转义。

    Returns:
        拼接后的帮助文本。
    """

    lines = [
        "本机器人提供 Sen 账号注册、支付宝 UID 绑定与账号信息查询服务。",
        "你可以通过此机器人自助完成以下操作：",
        "",
        "📖 " + md_bold("可用命令列表"),
        "",
    ]
    for cmd in COMMAND_CATALOG:
        signature = f"/{cmd.name}" + (f" {escape_md_v2(cmd.args)}" if cmd.args else "")
        example = f"/{cmd.name}" + (f" {escape_md_v2(cmd.example)}" if cmd.example else "")
        lines.append(rf"\- {signature}")
        lines.append(f"    功能说明: {escape_md_v2(cmd.summary)}")
        lines.append(f"    使用样例: {example}")
        lines.append("")
    lines.append("💡 请在群内私聊此机器人使用以上命令。")
    return "\n".join(lines)


HELP_TEXT = _build_help_text()


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
