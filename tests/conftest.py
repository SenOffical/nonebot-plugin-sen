"""NoneBot2 迁移测试辅助对象。"""

from __future__ import annotations

from typing import Any

import nonebot

nonebot.init()

from sen_bot.backend import BackendApiClient  # noqa: E402
from sen_bot.commands.shared import CommandContext  # noqa: E402
from sen_bot.config import SenSettings  # noqa: E402
from sen_bot.platform import EventContext  # noqa: E402


class FakeBot:
    """模拟 NoneBot Bot。"""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        """初始化模拟 Bot。

        Args:
            responses: 按 API 名称配置的返回值或异常。
        """

        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_api(self, api: str, **params: Any) -> Any:
        """记录并模拟平台 API 调用。

        Args:
            api: API 名称。
            **params: API 参数。

        Returns:
            配置的模拟返回值。
        """

        self.calls.append((api, params))
        response = self.responses.get(api)
        if isinstance(response, Exception):
            raise response
        return response


class FakeEvent:
    """模拟 NoneBot 事件。"""

    def __init__(
        self,
        payload: dict[str, Any],
        user_id: str | None = None,
        module: str = "tests.onebot",
    ) -> None:
        """初始化模拟事件。

        Args:
            payload: `model_dump()` 返回的事件 payload。
            user_id: `get_user_id()` 返回值。
            module: 用于平台识别的类模块名。
        """

        self._payload = payload
        self._user_id = user_id
        self.__class__.__module__ = module

    def model_dump(self, by_alias: bool = True) -> dict[str, Any]:
        """返回事件 payload。

        Args:
            by_alias: 保留 NoneBot 兼容签名。

        Returns:
            事件 payload。
        """

        return self._payload

    def get_user_id(self) -> str:
        """返回用户 ID。

        Returns:
            用户 ID。
        """

        if self._user_id is None:
            raise ValueError("missing user id")
        return self._user_id


class FakeApi(BackendApiClient):
    """模拟后端 API 客户端。"""

    def __init__(self, response: Any) -> None:
        """初始化模拟 API 客户端。

        Args:
            response: `post()` 返回值。
        """

        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def post(self, path: str, **kwargs: Any) -> Any:
        """记录并返回模拟响应。

        Args:
            path: API 路径。
            **kwargs: API 参数。

        Returns:
            预设响应。
        """

        self.calls.append({"path": path, **kwargs})
        return self.response


class FakeCache:
    """模拟群成员缓存。"""

    def __init__(self, hit: bool = False) -> None:
        """初始化模拟缓存。

        Args:
            hit: 读取缓存时是否命中。
        """

        self.hit = hit
        self.get_calls: list[tuple[str, str, str]] = []
        self.set_calls: list[tuple[str, str, str]] = []

    async def get(self, platform: str, group_id: str, user_id: str) -> bool:
        """读取模拟缓存。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。

        Returns:
            预设命中结果。
        """

        self.get_calls.append((platform, group_id, user_id))
        return self.hit

    async def set(self, platform: str, group_id: str, user_id: str) -> None:
        """写入模拟缓存。

        Args:
            platform: 平台标识。
            group_id: 群 ID。
            user_id: 用户 ID。
        """

        self.set_calls.append((platform, group_id, user_id))


def make_settings(**overrides: Any) -> SenSettings:
    """创建测试配置。

    Args:
        **overrides: 覆盖配置字段。

    Returns:
        Sen Bot 配置。
    """

    values = {
        "SEN_API_BASE_URL": "http://test/api/v1/koishi",
        "KOISHI_SECRET": "sk-test",
        "SEN_ALLOWED_GROUPS": "[]",
        **overrides,
    }
    return SenSettings(**values)


def make_context(api_response: Any, **settings_overrides: Any) -> CommandContext:
    """创建命令上下文。

    Args:
        api_response: 模拟 API 返回。
        **settings_overrides: 覆盖配置字段。

    Returns:
        命令处理上下文。
    """

    return CommandContext(
        bot=FakeBot(),
        event_context=EventContext(
            platform="tg",
            raw_platform="telegram",
            user_id="123456789",
            display_name="@testuser",
            extra={"first_name": "Test", "last_name": "User", "language_code": "zh-hans"},
        ),
        settings=make_settings(**settings_overrides),
        api=FakeApi(api_response),
        membership_cache=None,
    )
