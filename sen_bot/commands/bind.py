"""支付宝 UID 绑定命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..backend import err_msg
from ..models import AccountDetail
from .shared import (
    escape_md_v2,
    send_reply,
    CommandContext,
    build_command_context,
    check_authorized,
    is_alipay_uid,
)

# ── 纯业务处理函数（可独立测试）───────────────────────────────


async def handle_bind(ctx: CommandContext, alipay_uid: str | None) -> str | None:
    """处理 /bind 命令。

    Args:
        ctx: 命令处理上下文。
        alipay_uid: 用户输入的支付宝 UID。

    Returns:
        用户可见回复。
    """

    if not is_alipay_uid(alipay_uid):
        return "⚠️ 用法：/bind xxxxxxxxxxxxxxxx"

    event = ctx.event_context
    response = await ctx.api.post(
        "/bind-alipay",
        data={
            "platform": event.platform,
            "platform_user_id": event.user_id,
            "alipayUid": alipay_uid,
        },
        data_type=AccountDetail,
    )
    if response.code != 200:
        return err_msg(response.code, "绑定失败，请稍后重试。")
    return f"✅ UID {alipay_uid} 绑定成功。"


# ── NoneBot2 Matcher ──────────────────────────────────────────

bind_matcher = on_command("bind", aliases={"/bind"}, priority=10)


@bind_matcher.handle()
async def _(
    bot: Bot,
    event: Event,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    """接收 /bind 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    result = await handle_bind(ctx, str(args).strip() or None)
    if result is not None:
        await send_reply(matcher, event, result)

