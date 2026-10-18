"""Telegram 群成员变动事件处理。

Telegram 只有在「bot 是群管理员」且「``getUpdates`` 的 ``allowed_updates``
显式包含 ``chat_member``」时才会下发成员变动通知；前者取决于群设置，后者
由 :func:`bot.patch_telegram_allowed_updates` 负责补齐。

本模块把「退群 / 被踢」事件整理成统一载荷后转发给后端。事件通道与
`/api/v1/bot/*` 同向（bot → 后端），因此复用 ``SEN_API_BASE_URL`` 与
``SEN_BOT_SECRET``，不引入额外配置。
"""

from __future__ import annotations

import httpx
from nonebot import logger, on_notice
from nonebot.adapters import Event
from nonebot.adapters.telegram.event import ChatMemberUpdatedEvent

from .config import SenSettings, get_sen_settings

# 视为「已离开群组」的成员状态：主动退群与被移出分开保留，便于后端区分处置。
INACTIVE_STATUSES = {"left", "kicked"}

# 群成员变动事件在后端的相对路径，拼接在 SEN_API_BASE_URL 之后。
MEMBERSHIP_EVENT_PATH = "membership-events"

# 用 notice 类型匹配器接住 Telegram 的所有 notice 事件，再按具体类型过滤；
# block=False 保证不影响其他插件/命令对同一事件的处理。
membership_notice = on_notice(priority=10, block=False)


def build_membership_payload(
    *,
    group_id: str,
    user_id: str,
    status: str,
    occurred_at: int,
    triggered_by: str,
    allowed_group_ids: set[str],
) -> dict[str, object] | None:
    """构建群成员变动事件的上报载荷。

    Args:
        group_id: 发生变动的群 ID。
        user_id: 退群或被移出的用户 ID（取 ``new_chat_member.user.id``）。
        status: 变动后的成员状态，如 ``left`` / ``kicked``。
        occurred_at: 事件时间戳（Unix 秒）。
        triggered_by: 触发本次变动的用户 ID；主动退群时是本人，
            被移出时是操作的管理员，仅用于审计。
        allowed_group_ids: 允许群 ID 集合，用于过滤非目标群的事件。

    Returns:
        需要上报时返回载荷字典；状态不是在群外的情形、或群不在允许列表时
        返回 `None`。
    """

    if status not in INACTIVE_STATUSES:
        return None
    if group_id not in allowed_group_ids:
        return None
    return {
        "platform": "telegram",
        "group_id": group_id,
        "user_id": user_id,
        "status": status,
        "occurred_at": occurred_at,
        "triggered_by": triggered_by,
    }


def build_membership_event_url(settings: SenSettings) -> str:
    """由后端 Bot API 基址推导事件上报地址。

    Args:
        settings: Sen Bot 配置，使用其中的 ``api_base_url``。

    Returns:
        形如 ``<api_base_url>/membership-events`` 的完整地址。
    """

    return f"{settings.api_base_url.rstrip('/')}/{MEMBERSHIP_EVENT_PATH}"


async def post_membership_event(
    payload: dict[str, object],
    settings: SenSettings,
) -> None:
    """把群成员变动事件转发给后端。

    Args:
        payload: :func:`build_membership_payload` 生成的载荷。
        settings: Sen Bot 配置，读取后端地址与鉴权密钥。

    Raises:
        httpx.HTTPStatusError: 后端返回非 2xx 状态码。
    """

    headers: dict[str, str] = {}
    if settings.bot_secret:
        headers["X-Bot-Secret"] = settings.bot_secret
    url = build_membership_event_url(settings)
    async with httpx.AsyncClient(timeout=settings.backend_timeout_seconds) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
    logger.info(f"群成员变动事件已上报: {payload}")


@membership_notice.handle()
async def _(event: Event) -> None:
    """处理 Telegram 群成员变动通知。

    Args:
        event: 当前 notice 事件；非 Telegram 成员变动事件直接忽略。
    """

    if not isinstance(event, ChatMemberUpdatedEvent):
        return

    settings = get_sen_settings()
    member = event.new_chat_member
    payload = build_membership_payload(
        group_id=str(event.chat.id),
        user_id=str(member.user.id),
        status=str(member.status),
        occurred_at=event.date,
        triggered_by=str(event.from_.id),
        allowed_group_ids={group.id for group in settings.allowed_groups},
    )
    if payload is None:
        return

    try:
        await post_membership_event(payload, settings)
    except Exception as exc:
        # 上报失败不影响 bot 其余功能，仅告警；事件未送达由定时校准兜底。
        logger.warning(f"上报群成员变动事件失败: {exc}")
