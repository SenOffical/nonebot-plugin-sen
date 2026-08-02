"""Sen NoneBot2 插件入口。

所有命令的 on_command matcher 均在 `commands/` 子模块中定义，
NoneBot2 加载此插件时会自动导入并注册。
"""

from __future__ import annotations

from nonebot.plugin import PluginMetadata

from .config import SenSettings

__plugin_meta__ = PluginMetadata(
    name="sen",
    description="Sen 用户注册、支付宝 UID 绑定和账号信息查询机器人插件。",
    usage="/register /bind /unbind /secret /info /sync /merge",
    config=SenSettings,
)


from . import commands  # noqa: E402,F401 — 导入命令模块以注册 on_command matcher
