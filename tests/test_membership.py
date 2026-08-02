"""群成员校验测试。"""

from __future__ import annotations

from sen_bot.membership import check_group_membership, is_active_telegram_member
from sen_bot.models import AllowedGroup
from sen_bot.platform import EventContext

from .conftest import FakeBot, FakeCache, make_settings


def test_Telegram_left和kicked不通过() -> None:
    """验证 Telegram left/kicked 状态不算群成员。"""

    assert is_active_telegram_member({"status": "left"}) is False
    assert is_active_telegram_member({"status": "kicked"}) is False


def test_Telegram_restricted只在is_member为true时通过() -> None:
    """验证 Telegram restricted 状态的 is_member 规则。"""

    assert is_active_telegram_member({"status": "restricted", "is_member": False}) is False
    assert is_active_telegram_member({"status": "restricted", "is_member": True}) is True


async def test_缓存命中跳过BotAPI() -> None:
    """验证正向缓存命中时不调用平台 API。"""

    bot = FakeBot({"get_chat_member": {"status": "member"}})
    cache = FakeCache(hit=True)
    result = await check_group_membership(
        bot,  # type: ignore[arg-type]
        EventContext("tg", "telegram", "123456789", None, None),
        [AllowedGroup(id="-1001", desc="主群")],
        cache,
        make_settings(),
    )
    assert result is True
    assert bot.calls == []
    assert cache.get_calls == [("telegram", "-1001", "123456789")]


async def test_缓存未命中且成员存在时写入缓存() -> None:
    """验证 Bot API 通过后写入正向缓存。"""

    bot = FakeBot({"get_chat_member": {"status": "member"}})
    cache = FakeCache(hit=False)
    result = await check_group_membership(
        bot,  # type: ignore[arg-type]
        EventContext("tg", "telegram", "123456789", None, None),
        [AllowedGroup(id="-1001")],
        cache,
        make_settings(),
    )
    assert result is True
    assert bot.calls == [("get_chat_member", {"chat_id": "-1001", "user_id": 123456789})]
    assert cache.set_calls == [("telegram", "-1001", "123456789")]


async def test_成员不存在不写缓存() -> None:
    """验证 Bot API 拒绝时不写入缓存。"""

    bot = FakeBot({"get_chat_member": {"status": "left"}})
    cache = FakeCache(hit=False)
    result = await check_group_membership(
        bot,  # type: ignore[arg-type]
        EventContext("tg", "telegram", "123456789", None, None),
        [AllowedGroup(id="-1001")],
        cache,
        make_settings(),
    )
    assert result is False
    assert cache.set_calls == []



def test_Pydantic模型ChatMember也能识别() -> None:
    """验证 Pydantic model 格式的 ChatMember 同样能辨认状态。"""

    from pydantic import BaseModel

    class FakeChatMemberModel(BaseModel):
        status: str
        is_member: bool = False

    # 直接 Pydantic model
    assert is_active_telegram_member(FakeChatMemberModel(status="creator")) is True
    assert is_active_telegram_member(FakeChatMemberModel(status="member")) is True
    assert is_active_telegram_member(FakeChatMemberModel(status="left")) is False
    # restricted + is_member
    assert is_active_telegram_member(
        FakeChatMemberModel(status="restricted", is_member=True)
    ) is True
    assert is_active_telegram_member(
        FakeChatMemberModel(status="restricted", is_member=False)
    ) is False

