"""注册命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher

from ..backend import err_msg
from ..models import RegisterDetail
from .shared import send_reply, escape_md_v2, CommandContext, build_command_context, check_authorized

# ── 纯业务处理函数（可独立测试）───────────────────────────────


async def handle_register(ctx: CommandContext) -> str | None:
    """处理 /register 命令。

    Args:
        ctx: 命令处理上下文。

    Returns:
        用户可见回复。
    """

    event = ctx.event_context
    response = await ctx.api.post(
        "/register",
        data={
            "platform": event.platform,
            "platform_user_id": event.user_id,
            "displayName": event.display_name,
            "extra": event.extra,
        },
        data_type=RegisterDetail,
    )
    if response.code != 200:
        return err_msg(response.code, "注册失败，请稍后重试。")
    assert response.data is not None
    return (
        "✅ 注册成功！\n"
        f"🔑 你的注册密钥：{escape_md_v2(response.data.secret)}\n\n"
        "请妥善保管此密钥，后续客户端绑定和账号操作均需使用。"
    )


# ── NoneBot2 Matcher ──────────────────────────────────────────

register_matcher = on_command("register", aliases={"/register"}, priority=10)


@register_matcher.handle()
async def _(bot: Bot, event: Event, matcher: Matcher) -> None:
    """接收 /register 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    result = await handle_register(ctx)
    if result is not None:
        await send_reply(matcher, event, result)

