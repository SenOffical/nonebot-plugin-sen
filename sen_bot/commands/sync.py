"""平台绑定同步命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..backend import err_msg
from ..models import PlatformBindingDetail
from .shared import (
    escape_md_v2,
    send_reply,
    CommandContext,
    build_command_context,
    check_authorized,
    is_secret,
)

# ── 纯业务处理函数（可独立测试）───────────────────────────────


async def handle_sync(ctx: CommandContext, secret: str | None) -> str | None:
    """处理 /sync 命令。

    Args:
        ctx: 命令处理上下文。
        secret: 目标用户 secret。

    Returns:
        用户可见回复。
    """

    if not is_secret(secret):
        return "⚠️ 用法：/sync sk-xxxx-xxxx-xxxx-xxxx"

    event = ctx.event_context
    response = await ctx.api.post(
        "/bind-platform",
        data={
            "secret": secret,
            "platform": event.platform,
            "platform_user_id": event.user_id,
            "displayName": event.display_name,
            "extra": event.extra,
        },
        data_type=PlatformBindingDetail,
    )
    if response.code != 200:
        return err_msg(response.code, "绑定失败，请稍后重试。")
    return "✅ 当前平台已成功绑定到目标用户。"


# ── NoneBot2 Matcher ──────────────────────────────────────────

sync_matcher = on_command("sync", aliases={"/sync"}, priority=10)


@sync_matcher.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    """接收 /sync 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    result = await handle_sync(ctx, str(args).strip() or None)
    if result is not None:
        await send_reply(matcher, event, result)

