"""NoneBot 事件到 Sen 平台上下文的转换。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nonebot.adapters import Event

PLATFORM_MAP: dict[str, str] = {
    "telegram": "tg",
    "onebot": "qq",
    "onebot_v11": "qq",
    "qq": "qq",
    "discord": "discord",
    "kook": "kook",
}


@dataclass(frozen=True)
class EventContext:
    """Sen 命令所需的平台上下文。"""

    platform: str
    raw_platform: str
    user_id: str
    display_name: str | None
    extra: dict[str, object] | None


def extract_event_context(event: Event) -> EventContext | None:
    """从 NoneBot 事件中提取私聊用户上下文。

    Args:
        event: NoneBot 适配器事件。

    Returns:
        私聊事件返回上下文；群聊或缺少用户 ID 时返回 `None`。
    """

    raw = dump_event(event)
    raw_platform = detect_raw_platform(event, raw)
    if not is_private_event(raw_platform, raw):
        return None
    user_id = extract_user_id(event, raw)
    if not user_id:
        return None
    platform = PLATFORM_MAP.get(raw_platform, raw_platform)
    return EventContext(
        platform=platform,
        raw_platform=raw_platform,
        user_id=user_id,
        display_name=display_name(raw_platform, raw),
        extra=extract_extra(raw_platform, raw),
    )


def dump_event(event: Event) -> dict[str, Any]:
    """将 NoneBot 事件转换为普通字典。

    Args:
        event: NoneBot 适配器事件。

    Returns:
        事件字典；无法转换时返回空字典。
    """

    if hasattr(event, "model_dump"):
        dumped = event.model_dump(by_alias=True)
    elif hasattr(event, "dict"):
        dumped = event.dict()
    else:
        dumped = {}
    return dumped if isinstance(dumped, dict) else {}


def detect_raw_platform(event: Event, raw: dict[str, Any]) -> str:
    """识别事件来源平台。

    Args:
        event: NoneBot 适配器事件。
        raw: 事件字典。

    Returns:
        归一化前的平台标识。
    """

    module = event.__class__.__module__.lower()
    if "telegram" in module or "telegram" in raw:
        return "telegram"
    if "onebot" in module or "message_type" in raw:
        return "onebot"
    return raw.get("platform", "unknown") if isinstance(raw.get("platform"), str) else "unknown"


def is_private_event(raw_platform: str, raw: dict[str, Any]) -> bool:
    """判断事件是否为私聊。

    Args:
        raw_platform: 归一化前的平台标识。
        raw: 事件字典。

    Returns:
        私聊返回 `True`。
    """

    if raw_platform == "onebot":
        return raw.get("message_type") == "private"
    if raw_platform == "telegram":
        chat = _telegram_chat(raw)
        return chat.get("type") == "private"
    return raw.get("is_private") is True


def extract_user_id(event: Event, raw: dict[str, Any]) -> str | None:
    """提取平台用户 ID。

    Args:
        event: NoneBot 适配器事件。
        raw: 事件字典。

    Returns:
        用户 ID 字符串；无法提取时返回 `None`。
    """

    try:
        user_id = event.get_user_id()
        if user_id:
            return user_id
    except Exception:
        pass
    direct = raw.get("user_id")
    if direct is not None:
        return str(direct)
    tg_from = _telegram_from(raw)
    tg_id = tg_from.get("id")
    return str(tg_id) if tg_id is not None else None


def display_name(raw_platform: str, raw: dict[str, Any]) -> str | None:
    """提取用户展示名。

    Args:
        raw_platform: 归一化前的平台标识。
        raw: 事件字典。

    Returns:
        用户展示名；无可用字段时返回 `None`。
    """

    if raw_platform == "telegram":
        tg_from = _telegram_from(raw)
        username = tg_from.get("username")
        if isinstance(username, str) and username:
            return f"@{username}"
        names = [tg_from.get("first_name"), tg_from.get("last_name")]
        full_name = " ".join(str(name) for name in names if name)
        return full_name or None

    sender = raw.get("sender")
    if isinstance(sender, dict):
        for key in ("card", "nickname", "user_name"):
            value = sender.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def extract_extra(raw_platform: str, raw: dict[str, Any]) -> dict[str, object] | None:
    """提取平台特有元数据。

    Args:
        raw_platform: 归一化前的平台标识。
        raw: 事件字典。

    Returns:
        可发送给后端的元数据；无字段时返回 `None`。
    """

    if raw_platform == "telegram":
        tg_from = _telegram_from(raw)
        extra = {
            key: tg_from[key]
            for key in ("first_name", "last_name", "language_code")
            if tg_from.get(key)
        }
        return extra or None

    sender = raw.get("sender")
    if isinstance(sender, dict):
        extra = {
            key: sender[key]
            for key in ("nickname", "card", "sex", "age", "area", "level", "role", "title")
            if sender.get(key) is not None
        }
        return extra or None
    return None


def _telegram_from(raw: dict[str, Any]) -> dict[str, Any]:
    """提取 Telegram from 对象。

    Args:
        raw: 事件字典。

    Returns:
        Telegram from 字典。
    """

    message = raw.get("message")
    if isinstance(message, dict) and isinstance(message.get("from"), dict):
        return message["from"]
    callback_query = raw.get("callback_query")
    if isinstance(callback_query, dict) and isinstance(callback_query.get("from"), dict):
        return callback_query["from"]
    if isinstance(raw.get("from"), dict):
        return raw["from"]
    return {}


def _telegram_chat(raw: dict[str, Any]) -> dict[str, Any]:
    """提取 Telegram chat 对象。

    Args:
        raw: 事件字典。

    Returns:
        Telegram chat 字典。
    """

    message = raw.get("message")
    if isinstance(message, dict) and isinstance(message.get("chat"), dict):
        return message["chat"]
    chat = raw.get("chat")
    return chat if isinstance(chat, dict) else {}

