"""平台上下文提取测试。"""

from __future__ import annotations

from sen_bot.platform import extract_event_context

from .conftest import FakeEvent


def test_提取OneBot私聊上下文() -> None:
    """验证 OneBot 私聊事件能映射为 qq 平台。"""

    event = FakeEvent(
        {
            "message_type": "private",
            "user_id": 10001,
            "sender": {"nickname": "测试用户", "card": "群名片"},
        },
        module="nonebot.adapters.onebot.v11.event",
    )
    context = extract_event_context(event)
    assert context is not None
    assert context.platform == "qq"
    assert context.user_id == "10001"
    assert context.display_name == "群名片"
    assert context.extra == {"nickname": "测试用户", "card": "群名片"}


def test_提取Telegram私聊上下文() -> None:
    """验证 Telegram 私聊事件能映射为 tg 平台。"""

    event = FakeEvent(
        {
            "message": {
                "chat": {"type": "private"},
                "from": {
                    "id": 123456789,
                    "username": "tester",
                    "first_name": "Test",
                    "language_code": "zh-hans",
                },
            }
        },
        module="nonebot.adapters.telegram.event",
    )
    context = extract_event_context(event)
    assert context is not None
    assert context.platform == "tg"
    assert context.user_id == "123456789"
    assert context.display_name == "@tester"
    assert context.extra == {"first_name": "Test", "language_code": "zh-hans"}


def test_群聊事件返回None() -> None:
    """验证群聊命令会被静默忽略。"""

    event = FakeEvent(
        {"message_type": "group", "user_id": 10001},
        module="nonebot.adapters.onebot.v11.event",
    )
    assert extract_event_context(event) is None

