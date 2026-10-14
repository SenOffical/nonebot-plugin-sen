"""NoneBot2 应用入口。"""

from __future__ import annotations

import asyncio

import nonebot
from nonebot import logger
from nonebot.drivers import Driver

# Telegram API 调用硬超时（秒）。getUpdates 长轮询参数为 30 秒，
# 预留 3 倍余量以覆盖代理转发的额外延迟，避免误伤正常请求。
TELEGRAM_API_HARD_TIMEOUT = 90.0


def build_telegram_command_menu() -> list[tuple[str, str]]:
    """构建 Telegram 命令菜单条目。

    命令数据来自插件的命令目录单一数据源（`sen_bot.commands.catalog`），
    与 `/start` 帮助文本共享，帮助命令置顶。command 不含前导斜杠，
    仅允许小写字母、数字与下划线（1-32 字符）；description 为纯文本（1-256 字符）。

    采用延迟导入：`sen_bot` 包导入会触发命令 matcher 注册，必须在
    ``nonebot.init()`` 之后执行；本函数仅在 Bot 连接钩子（运行时）中调用。

    :returns: ``(命令名, 描述)`` 列表。
    """

    from sen_bot.commands.catalog import COMMAND_CATALOG, HELP_COMMAND

    return [(spec.name, spec.summary) for spec in (HELP_COMMAND, *COMMAND_CATALOG)]


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
    from nonebot.adapters.telegram import Bot as TelegramBot

    original_call_api = TelegramAdapter._call_api

    async def call_api_with_timeout(
        self: TelegramAdapter,
        bot: TelegramBot,
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


def setup_telegram_command_menu(driver: Driver) -> None:
    """注册 bot 连接钩子，为 Telegram Bot 自动配置命令菜单。

    在 Bot 连接成功后调用 Telegram ``setMyCommands`` 写入命令菜单，
    使用户可通过客户端菜单按钮查看并触发可用命令。仅对 Telegram
    适配器生效，OneBot 等其他适配器的 Bot 会被跳过。

    :param driver: NoneBot2 驱动实例，用于注册 ``on_bot_connect`` 钩子。
    """

    from nonebot.adapters import Bot
    from nonebot.adapters.telegram import Bot as TelegramBot
    from nonebot.adapters.telegram.model import BotCommand

    @driver.on_bot_connect
    async def _apply_command_menu(bot: Bot) -> None:
        """为已连接的 Telegram Bot 写入命令菜单。

        :param bot: 当前连接成功的 Bot 实例。
        """

        if not isinstance(bot, TelegramBot):
            return
        commands = [
            BotCommand(command=name, description=desc)
            for name, desc in build_telegram_command_menu()
        ]
        try:
            await bot.set_my_commands(commands)
        except Exception as exc:
            # 菜单配置失败不应中断启动或轮询，仅记录告警。
            logger.warning(f"配置 Telegram Bot {bot.self_id} 命令菜单失败: {exc}")
            return
        logger.info(
            f"已为 Telegram Bot {bot.self_id} 配置命令菜单（{len(commands)} 项）"
        )


def main() -> None:
    """初始化 NoneBot2 驱动并加载 Sen 插件。"""

    nonebot.init()

    driver = nonebot.get_driver()

    from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
    from nonebot.adapters.telegram import Adapter as TelegramAdapter

    patch_telegram_api_timeout()
    setup_telegram_command_menu(driver)

    driver.register_adapter(OneBotV11Adapter)
    driver.register_adapter(TelegramAdapter)

    nonebot.load_plugin("sen_bot")

    nonebot.run()


if __name__ == "__main__":
    main()
