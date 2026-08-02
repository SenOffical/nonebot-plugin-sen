"""账号信息查询命令。"""

from __future__ import annotations

from nonebot import on_command
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher

from ..backend import err_msg
from ..models import AccountDetail, PlatformBindingDetail, UserInfoDetail
from .shared import send_reply, escape_md_v2, md_bold, md_code, CommandContext, build_command_context, check_authorized

# ── 纯业务处理函数（可独立测试）───────────────────────────────


async def handle_info(ctx: CommandContext) -> str | None:
    """处理 /info 命令。

    Args:
        ctx: 命令处理上下文。

    Returns:
        用户可见回复。
    """

    event = ctx.event_context
    response = await ctx.api.post(
        "/info",
        data={
            "platform": event.platform,
            "platform_user_id": event.user_id,
            "displayName": event.display_name,
            "extra": event.extra,
        },
        data_type=UserInfoDetail,
    )
    if response.code != 200:
        return err_msg(response.code, "查询失败，请稍后重试。")
    assert response.data is not None
    return format_user_info(response.data)


def format_user_info(user: UserInfoDetail) -> str:
    """格式化当前用户完整信息。

    Args:
        user: 后端返回的当前用户完整信息。

    Returns:
        用户可见的多行账号信息（MarkdownV2 格式）。
    """

    alipay_accounts = [account for account in user.accounts if account.provider == "alipay"]
    sid = escape_md_v2(str(user.id))
    sstatus = escape_md_v2("正常" if user.status == 0 else "异常")
    ssecret = escape_md_v2(user.secret)
    lines = [
        "📋 " + md_bold("当前账号信息"),
        f"用户 ID: {md_code(sid)}",
        f"状态: {sstatus}",
        f"密钥: {md_code(ssecret)}",
        "",
        "💳 " + md_bold("UID"),
        format_alipay_accounts(alipay_accounts),
        "",
        "🔗 " + md_bold("平台绑定"),
        format_platform_bindings(user.platform_bindings),
        "",
        r"💡 /bind 绑定 UID \| /secret 重新生成密钥",
    ]
    return "\n".join(lines)


def format_alipay_accounts(accounts: list[AccountDetail]) -> str:
    """格式化支付宝 UID 列表。

    Args:
        accounts: 支付宝账户列表。

    Returns:
        多行支付宝 UID 文本（MarkdownV2 格式）。
    """

    if not accounts:
        return r"\- 未绑定"
    return "\n".join(
        f"\- {md_code(escape_md_v2(account.external_uid))}（状态: {escape_md_v2('正常' if account.status == 0 else '异常')}）"
        for account in accounts
    )


def format_platform_bindings(bindings: list[PlatformBindingDetail]) -> str:
    """格式化平台绑定列表。

    Args:
        bindings: 平台绑定列表。

    Returns:
        多行平台绑定文本（MarkdownV2 格式）。
    """

    if not bindings:
        return r"\- 未绑定"
    return "\n".join(
        rf"\- {escape_md_v2(binding.platform)}: {md_code(escape_md_v2(binding.platform_user_id))}（{escape_md_v2(binding.display_name or '未设置')}）"
        for binding in bindings
    )


# ── NoneBot2 Matcher ──────────────────────────────────────────

info_matcher = on_command("info", aliases={"/info"}, priority=10)


@info_matcher.handle()
async def _(bot: Bot, event: Event, matcher: Matcher) -> None:
    """接收 /info 命令事件。"""

    ctx = build_command_context(bot, event)
    if ctx is None:
        return
    blocked = await check_authorized(ctx)
    if blocked is not None:
        await send_reply(matcher, event, blocked)
        return
    result = await handle_info(ctx)
    if result is not None:
        await send_reply(matcher, event, result)

