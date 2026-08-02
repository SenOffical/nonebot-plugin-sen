"""NoneBot2 应用入口。"""

from __future__ import annotations

import nonebot


def main() -> None:
    """初始化 NoneBot2 驱动并加载 Sen 插件。"""

    nonebot.init()

    driver = nonebot.get_driver()

    from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
    from nonebot.adapters.telegram import Adapter as TelegramAdapter

    driver.register_adapter(OneBotV11Adapter)
    driver.register_adapter(TelegramAdapter)

    nonebot.load_plugin("sen_bot")

    nonebot.run()


if __name__ == "__main__":
    main()

