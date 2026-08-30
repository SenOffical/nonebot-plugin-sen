"""NoneBot2 应用入口。"""

from __future__ import annotations

import asyncio

import nonebot

# Telegram API 调用硬超时（秒）。getUpdates 长轮询参数为 30 秒，
# 预留 3 倍余量以覆盖代理转发的额外延迟，避免误伤正常请求。
TELEGRAM_API_HARD_TIMEOUT = 90.0


def patch_telegram_api_timeout() -> None:
    """为 Telegram 适配器所有 API 调用强制附加硬超时。

    背景：适配器构造 HTTP 请求时不设置 timeout，经 HTTP 代理的长轮询
    连接可能被代理或 NAT 静默丢弃且不产生任何异常，导致 ``poll()``
    协程永久挂起（表现为机器人"假死"，但进程与端口仍然存活）。

    实现方式：包装 :meth:`TelegramAdapter._call_api`，使用
    :func:`asyncio.wait_for` 限时。超时后内部请求被取消，
    :class:`TimeoutError` 会被轮询循环的 ``except Exception`` 捕获，
    记录日志、休眠 5 秒后自动重试，从而实现自愈。

    必须在 ``register_adapter`` 之前调用，确保所有 Bot 实例都走补丁路径。
    """

    from nonebot.adapters.telegram import Adapter as TelegramAdapter

    original_call_api = TelegramAdapter._call_api

    async def call_api_with_timeout(
        self: TelegramAdapter,
        bot: object,
        api: str,
        **data: object,
    ) -> object:
        """带硬超时的 API 调用包装。

        :param self: Telegram 适配器实例。
        :param bot: 发起调用的 Bot 实例。
        :param api: Telegram Bot API 方法名，如 ``getUpdates``。
        :param data: API 参数。
        :returns: 原 ``_call_api`` 的返回值。
        :raises TimeoutError: 调用超过 :data:`TELEGRAM_API_HARD_TIMEOUT` 时抛出。
        """

        return await asyncio.wait_for(
            original_call_api(self, bot, api, **data),
            timeout=TELEGRAM_API_HARD_TIMEOUT,
        )

    TelegramAdapter._call_api = call_api_with_timeout  # type: ignore[method-assign]


def main() -> None:
    """初始化 NoneBot2 驱动并加载 Sen 插件。"""

    nonebot.init()

    driver = nonebot.get_driver()

    from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
    from nonebot.adapters.telegram import Adapter as TelegramAdapter

    patch_telegram_api_timeout()

    driver.register_adapter(OneBotV11Adapter)
    driver.register_adapter(TelegramAdapter)

    nonebot.load_plugin("sen_bot")

    nonebot.run()


if __name__ == "__main__":
    main()
