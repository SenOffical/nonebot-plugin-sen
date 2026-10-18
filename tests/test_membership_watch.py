"""群成员变动事件处理测试。"""

from __future__ import annotations

from typing import Any

import pytest

from sen_bot.config import SenSettings
from sen_bot.membership_watch import (
    build_membership_event_url,
    build_membership_payload,
    post_membership_event,
)

ALLOWED = {"-1003701273193"}


def _payload(**overrides: Any) -> dict[str, object] | None:
    """用默认参数构建载荷，便于逐项覆盖。

    Args:
        **overrides: 覆盖 `build_membership_payload` 的关键字参数。

    Returns:
        载荷字典或 `None`。
    """

    values: dict[str, Any] = {
        "group_id": "-1003701273193",
        "user_id": "123456789",
        "status": "left",
        "occurred_at": 1791973599,
        "triggered_by": "123456789",
        "allowed_group_ids": ALLOWED,
    }
    values.update(overrides)
    return build_membership_payload(**values)


def test_left_member_produces_payload() -> None:
    """主动退群应生成上报载荷。"""

    payload = _payload()

    assert payload == {
        "platform": "telegram",
        "group_id": "-1003701273193",
        "user_id": "123456789",
        "status": "left",
        "occurred_at": 1791973599,
        "triggered_by": "123456789",
    }


def test_kicked_member_produces_payload() -> None:
    """被移出群应生成载荷，且状态保留 kicked 以便后端区分处置。"""

    payload = _payload(status="kicked", triggered_by="999")

    assert payload is not None
    assert payload["status"] == "kicked"
    assert payload["triggered_by"] == "999"


@pytest.mark.parametrize("status", ["member", "administrator", "creator", "restricted"])
def test_non_inactive_status_produces_no_payload(status: str) -> None:
    """非「离开群组」的状态不上报，避免入群、提权等事件误触发。"""

    assert _payload(status=status) is None


def test_event_from_other_group_is_ignored() -> None:
    """不在允许群列表中的群，其事件必须忽略。"""

    assert _payload(group_id="-1009999999999") is None


def test_empty_allowed_groups_ignores_everything() -> None:
    """未配置允许群时不应上报任何事件。"""

    assert _payload(allowed_group_ids=set()) is None


def test_event_url_derived_from_api_base_url() -> None:
    """上报地址由后端 Bot API 基址推导，并去掉尾部斜杠。"""

    settings = SenSettings()
    settings.api_base_url = "http://backend/api/v1/bot/"

    assert (
        build_membership_event_url(settings)
        == "http://backend/api/v1/bot/membership-events"
    )


async def test_post_membership_event_uses_bot_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开启上报后复用 X-Bot-Secret 与 SEN_API_BASE_URL，不需额外配置。"""

    captured: dict[str, Any] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(
            self, url: str, *, json: object, headers: dict[str, str]
        ) -> _Response:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Response()

    monkeypatch.setattr("sen_bot.membership_watch.httpx.AsyncClient", _Client)

    settings = SenSettings()
    settings.api_base_url = "http://backend/api/v1/bot"
    settings.bot_secret = "sk-bot"
    await post_membership_event({"user_id": "1"}, settings)

    assert captured["url"] == "http://backend/api/v1/bot/membership-events"
    assert captured["json"] == {"user_id": "1"}
    assert captured["headers"] == {"X-Bot-Secret": "sk-bot"}
