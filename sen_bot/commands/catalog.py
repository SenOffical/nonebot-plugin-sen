"""命令目录：所有用户命令的单一数据源。

`/start` 帮助文本（`start.py`）与 Telegram 命令菜单（`bot.py`）均由本模块
生成，避免命令名称、功能说明与使用样例在多处重复维护。

本模块为纯数据，不导入 nonebot、不注册 matcher，可被入口脚本在运行时安全
延迟导入。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    """单个命令的元信息。

    Attributes:
        name: 命令名（不含前导斜杠），如 ``register``。
        args: 帮助文本签名中的参数占位，如 ``<支付宝UID>``；无参数为空串。
        summary: 一句话功能说明，同时用作 Telegram 命令菜单描述。
        example: 使用样例中的参数部分，如 ``sk-xxxx``；无参数为空串。
    """

    name: str
    args: str
    summary: str
    example: str


# /start 与 /help 帮助命令本身，单列以便在 Telegram 菜单中置顶。
HELP_COMMAND = CommandSpec(
    name="start",
    args="",
    summary="显示帮助与可用命令列表",
    example="",
)

# 用户可执行命令，顺序即帮助文本与命令菜单的展示顺序。
COMMAND_CATALOG: tuple[CommandSpec, ...] = (
    CommandSpec("register", "", "注册 Sen 账号并获取访问密钥", ""),
    CommandSpec("info", "", "查询当前账号信息（绑定 UID / 平台关联 / 密钥）", ""),
    CommandSpec("bind", "<支付宝UID>", "将支付宝 UID 绑定到当前账号", "xxxxxxxxxxxxxxxx"),
    CommandSpec("unbind", "<支付宝UID>", "解绑已关联的支付宝 UID", "xxxxxxxxxxxxxxxx"),
    CommandSpec("secret", "", "重新生成访问密钥（旧密钥立即失效）", ""),
    CommandSpec(
        "sync",
        "<密钥>",
        "用密钥同步当前平台账号到已有 Sen 账号",
        "sk-xxxx-xxxx-xxxx-xxxx",
    ),
    CommandSpec(
        "merge",
        "<密钥>",
        "将当前平台账号合并到密钥对应的 Sen 账号",
        "sk-xxxx-xxxx-xxxx-xxxx",
    ),
)
