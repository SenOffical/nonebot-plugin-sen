"""群成员 Redis 缓存和平台 API 校验。"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from nonebot import logger
from nonebot.adapters import Bot
from redis.asyncio import Redis

from .config import SenSettings
from .models import AllowedGroup
from .platform import EventContext

POSITIVE_MEMBERSHIP_VALUE = "active:v3"
ACTIVE_TELEGRAM_STATUSES = {"creator", "administrator", "member"}


class MembershipCache(Protocol):
    """群成员正向缓存协议。"""

    async def get(self, platform: str, group_id: str, user_id: str) -> bool:
        """读取正向缓存。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。

        Returns:
            命中正向缓存返回 `True`。
        """

    async def set(self, platform: str, group_id: str, user_id: str) -> None:
        """写入正向缓存。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。
        """


class RedisMembershipCache:
    """基于 Redis 的群成员正向缓存。"""

    def __init__(self, settings: SenSettings) -> None:
        """初始化 Redis 缓存。

        Args:
            settings: Sen Bot 配置。
        """

        self._settings = settings
        self._ttl_seconds = max(1, settings.membership_cache_ttl_days * 86400)
        self._redis = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )

    async def get(self, platform: str, group_id: str, user_id: str) -> bool:
        """读取正向缓存。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。

        Returns:
            命中正向缓存返回 `True`；Redis 异常返回 `False`。
        """

        try:
            cached = await self._redis.get(self._key(platform, group_id, user_id))
            return cached == POSITIVE_MEMBERSHIP_VALUE
        except Exception as exc:
            logger.warning(f"读取 Redis 群成员缓存失败: {exc}")
            return False

    async def set(self, platform: str, group_id: str, user_id: str) -> None:
        """写入正向缓存。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。
        """

        try:
            await self._redis.set(
                self._key(platform, group_id, user_id),
                POSITIVE_MEMBERSHIP_VALUE,
                ex=self._ttl_seconds,
            )
        except Exception as exc:
            logger.warning(f"写入 Redis 群成员缓存失败: {exc}")

    def _key(self, platform: str, group_id: str, user_id: str) -> str:
        """生成 Redis key。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。

        Returns:
            Redis key 字符串。
        """

        return f"{self._settings.membership_cache_key_prefix}:{platform}:{group_id}:{user_id}"


def create_membership_cache(settings: SenSettings) -> MembershipCache | None:
    """按配置创建群成员缓存。

    Args:
        settings: Sen Bot 配置。

    Returns:
        启用缓存时返回 Redis 缓存对象，否则返回 `None`。
    """

    if not settings.membership_cache_enabled:
        return None
    return RedisMembershipCache(settings)


def is_active_telegram_member(member: Any) -> bool:
    """判断 Telegram getChatMember 原始结果是否表示仍在群内。

    Args:
        member: Telegram ChatMember 数据（dict 或 Pydantic model）。

    Returns:
        仍在群内返回 `True`。
    """

    if hasattr(member, "model_dump"):
        member = member.model_dump()
    elif hasattr(member, "dict"):
        member = member.dict()
    if not isinstance(member, dict):
        return False
    status = member.get("status")
    if not isinstance(status, str):
        return False
    if status in ACTIVE_TELEGRAM_STATUSES:
        return True
    return status == "restricted" and member.get("is_member") is True


async def check_group_membership(
    bot: Bot,
    event_context: EventContext,
    allowed_groups: list[AllowedGroup],
    cache: MembershipCache | None,
    settings: SenSettings,
) -> bool:
    """校验用户是否在任意允许群中。

    Args:
        bot: 当前平台 Bot 对象。
        event_context: 当前命令的平台上下文。
        allowed_groups: 允许群配置。
        cache: 群成员正向缓存。
        settings: Sen Bot 配置。

    Returns:
        至少在一个允许群中返回 `True`。
    """

    for group in allowed_groups:
        if cache and await cache.get(event_context.raw_platform, group.id, event_context.user_id):
            logger.info(
                f"群成员缓存命中，跳过 Bot API platform={event_context.raw_platform} "
                f"group_id={group.id} user_id={event_context.user_id}"
            )
            return True
        logger.info(
            f"群成员缓存未命中或未启用 platform={event_context.raw_platform} "
            f"group_id={group.id} user_id={event_context.user_id}"
        )
        if not await is_group_member(bot, event_context, group.id, settings):
            continue
        if cache:
            await cache.set(event_context.raw_platform, group.id, event_context.user_id)
        return True
    return False


async def is_group_member(
    bot: Bot,
    event_context: EventContext,
    group_id: str,
    settings: SenSettings,
) -> bool:
    """通过平台 Bot API 查询群成员状态。

    Args:
        bot: 当前平台 Bot 对象。
        event_context: 当前命令的平台上下文。
        group_id: 群 ID。
        settings: Sen Bot 配置。

    Returns:
        用户仍在群内返回 `True`。
    """

    try:
        if event_context.raw_platform == "telegram":
            member = await retry_call_api(
                bot,
                "get_chat_member",
                settings,
                chat_id=group_id,
                user_id=int(event_context.user_id),
            )
            member = _unwrap_telegram_member(member)
            active = is_active_telegram_member(member)
            status = member.get("status") if isinstance(member, dict) else (
                member.model_dump().get("status") if hasattr(member, "model_dump") else None
            )
            logger.info(
                f"Telegram 群成员返回 group_id={group_id} user_id={event_context.user_id} "
                f"status={status} active={active}"
            )
            return active

        if event_context.raw_platform == "onebot":
            await retry_call_api(
                bot,
                "get_group_member_info",
                settings,
                group_id=_parse_numeric_id(group_id),
                user_id=_parse_numeric_id(event_context.user_id),
                no_cache=True,
            )
            return True

        await retry_call_api(
            bot,
            "get_guild_member",
            settings,
            guild_id=group_id,
            user_id=event_context.user_id,
        )
        return True
    except Exception as exc:
        logger.warning(
            f"群成员校验请求失败 platform={event_context.raw_platform} "
            f"group_id={group_id} user_id={event_context.user_id} error={exc}"
        )
        return False


async def retry_call_api(bot: Bot, api: str, settings: SenSettings, **params: Any) -> Any:
    """带重试调用平台 Bot API。

    Args:
        bot: 当前平台 Bot 对象。
        api: 平台 API 名称。
        settings: Sen Bot 配置。
        **params: API 参数。

    Returns:
        平台 API 返回值。
    """

    retry_times = settings.platform_api_retry_times
    interval = settings.platform_api_retry_interval_seconds
    for attempt in range(retry_times + 1):
        try:
            return await bot.call_api(api, **params)
        except Exception:
            if attempt >= retry_times:
                raise
            await asyncio.sleep(interval)
    raise RuntimeError("unreachable retry state")


def _unwrap_telegram_member(payload: Any) -> Any:
    """兼容 Telegram API 包装响应（Pydantic model 或 dict）。

    Args:
        payload: NoneBot Telegram adapter 返回值。

    Returns:
        ChatMember 原始 dict 结构。
    """

    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    elif hasattr(payload, "dict"):
        payload = payload.dict()
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def _parse_numeric_id(value: str) -> int | str:
    """尽量把平台 ID 转为整数。

    Args:
        value: 平台 ID 字符串。

    Returns:
        可解析为整数时返回 `int`，否则返回原字符串。
    """

    try:
        return int(value)
    except ValueError:
        return value
