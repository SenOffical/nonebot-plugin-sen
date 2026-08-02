"""账号合并命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..backend import err_msg
from ..models import UserInfoDetail
from .shared import (
    escape_md_v2,
    send_reply,
    CommandContext,
    build_command_context,
    check_authorized,
    is_secret,
)

# ── 纯业务处理函数（可独立测试）───────────────────────────────


async def handle_merge(ctx: CommandContext, target_secret: str | None) -> str | None:
    """处理 /merge 命令。

    Args:
        ctx: 命令处理上下文。
        target_secret: 目标用户 secret。

    Returns:
        用户可见回复。
    """

    if not is_secret(target_secret):
        return "⚠️ 用法：/merge sk-xxxx-xxxx-xxxx-xxxx"

    event = ctx.event_context
    response = await ctx.api.post(
        "/merge-user",
        data={
            "targetSecret": target_secret,
            "sourcePlatform": event.platform,
            "sourcePlatformUserId": event.user_id,
        },
        data_type=UserInfoDetail,
    )
    if response.code != 200:
        return err_msg(response.code, "合并失败，请稍后重试。")
    return "✅ 账号合并成功！当前平台绑定和账户已迁移到目标用户。"


# ── NoneBot2 Matcher ──────────────────────────────────────────

merge_matcher = on_command("merge", aliases={"/merge"}, priority=10)


@merge_matcher.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    """接收 /merge 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    result = await handle_merge(ctx, str(args).strip() or None)
    if result is not None:
        await send_reply(matcher, event, result)

