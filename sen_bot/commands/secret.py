"""访问密钥重置命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher

from ..backend import err_msg
from ..models import RegisterDetail
from .shared import send_reply, escape_md_v2, CommandContext, build_command_context, check_authorized

# ── 纯业务处理函数（可独立测试）───────────────────────────────


async def handle_secret(ctx: CommandContext) -> str | None:
    """处理 /secret 命令。

    Args:
        ctx: 命令处理上下文。

    Returns:
        用户可见回复。
    """

    event = ctx.event_context
    response = await ctx.api.post(
        "/update-secret",
        params={"platform": event.platform, "platform_user_id": event.user_id},
        data_type=RegisterDetail,
    )
    if response.code != 200:
        return err_msg(response.code, "操作失败，请稍后重试。")
    assert response.data is not None
    return (
        "🔄 密钥已重新生成，旧密钥立即失效。\n"
        f"🔑 新密钥：{escape_md_v2(response.data.secret)}\n\n"
        "请妥善保管。"
    )


# ── NoneBot2 Matcher ──────────────────────────────────────────

secret_matcher = on_command("secret", aliases={"/secret"}, priority=10)


@secret_matcher.handle()
async def _(bot: Bot, event: Event, matcher: Matcher) -> None:
    """接收 /secret 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    result = await handle_secret(ctx)
    if result is not None:
        await send_reply(matcher, event, result)

