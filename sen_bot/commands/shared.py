"""命令共享上下文与守卫。"""

from __future__ import annotations

from dataclasses import dataclass

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher

from ..backend import BackendApiClient
from ..config import SenSettings, get_sen_settings
from ..membership import (
    MembershipCache,
    check_group_membership,
    create_membership_cache,
)
from ..platform import EventContext, extract_event_context


@dataclass
class CommandContext:
    """命令处理所需依赖。"""

    bot: Bot
    event_context: EventContext
    settings: SenSettings
    api: BackendApiClient
    membership_cache: MembershipCache | None


def build_command_context(bot: Bot, event: Event) -> CommandContext | None:
    """从 NoneBot 事件构建命令上下文。

    仅私聊事件会返回上下文；群聊事件返回 `None` 以静默忽略。

    Args:
        bot: 当前平台 Bot。
        event: 当前事件。

    Returns:
        私聊事件返回命令上下文；群聊返回 `None`。
    """

    event_context = extract_event_context(event)
    if event_context is None:
        return None
    settings = get_sen_settings()
    return CommandContext(
        bot=bot,
        event_context=event_context,
        settings=settings,
        api=BackendApiClient(settings),
        membership_cache=create_membership_cache(settings),
    )


async def check_authorized(ctx: CommandContext) -> str | None:
    """校验用户是否在允许的群组中。

    如果未配置允许群组，直接通过。如果用户不在任何允许群中，返回错误提示。

    Args:
        ctx: 命令处理上下文。

    Returns:
        通过授权时返回 `None`；未授权时返回用户提示文本。
    """

    allowed_groups = ctx.settings.allowed_groups
    if not allowed_groups:
        return None
    in_group = await check_group_membership(
        ctx.bot,
        ctx.event_context,
        allowed_groups,
        ctx.membership_cache,
        ctx.settings,
    )
    if in_group:
        return None
    return "你不在允许的群组中，无法使用该命令。请先加入指定群组后再试。"


def is_alipay_uid(value: str | None) -> bool:
    """判断字符串是否为 16 位支付宝 UID。

    Args:
        value: 待检查字符串。

    Returns:
        是 16 位数字返回 `True`。
    """

    return bool(value and len(value) == 16 and value.isdigit())


def is_secret(value: str | None) -> bool:
    """判断字符串是否为 Sen secret。

    Args:
        value: 待检查字符串。

    Returns:
        以 `sk-` 开头返回 `True`。
    """

    return bool(value and value.startswith("sk-"))



import re as _re

_MDV2_ESC = r'_*[]()~`>#+-=|{}.!'

def escape_md_v2(text: str) -> str:
    """转义 Telegram MarkdownV2 特殊字符。

    Args:
        text: 待转义文本。

    Returns:
        转义后的安全文本。
    """

    return _re.sub(r'([%s])' % _re.escape(_MDV2_ESC), r'\\\1', text)


def md_bold(text: str) -> str:
    """包裹为 MarkdownV2 粗体。

    Args:
        text: 已转义文本。

    Returns:
        粗体标记包裹的文本。
    """

    return f'*{text}*'


def md_code(text: str) -> str:
    """包裹为 MarkdownV2 行内代码。

    Args:
        text: 已转义文本。

    Returns:
        代码标记包裹的文本。
    """

    return f'`{text}`'


async def send_reply(matcher: Matcher, event: Event, msg: str) -> None:
    """发送回复消息；Telegram 平台自动使用 Markdown 格式。

    Args:
        matcher: 当前事件 Matcher。
        event: 当前事件。
        msg: 回复消息文本。
    """

    if "telegram" in event.__class__.__module__.lower():
        await matcher.finish(msg, parse_mode="MarkdownV2")
    else:
        await matcher.finish(msg)
