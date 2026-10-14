"""Telegram 命令菜单配置测试。"""

from __future__ import annotations

import re

from bot import build_telegram_command_menu
from sen_bot.commands.catalog import COMMAND_CATALOG, HELP_COMMAND
from sen_bot.commands.start import HELP_TEXT

# Telegram BotCommand.command 约束：1-32 字符，仅小写字母、数字、下划线。
_COMMAND_PATTERN = re.compile(r"^[a-z0-9_]{1,32}$")


def test_command_menu_names_are_valid_telegram_commands() -> None:
    """命令名必须符合 Telegram BotCommand 约束（不含前导斜杠）。"""

    for name, _ in build_telegram_command_menu():
        assert _COMMAND_PATTERN.match(name), f"非法命令名: {name}"


def test_command_menu_descriptions_within_limit() -> None:
    """命令描述必须为 1-256 字符的纯文本。"""

    for name, desc in build_telegram_command_menu():
        assert 1 <= len(desc) <= 256, f"{name} 描述长度非法: {len(desc)}"


def test_command_menu_names_unique() -> None:
    """命令名不得重复。"""

    names = [name for name, _ in build_telegram_command_menu()]
    assert len(names) == len(set(names)), "命令菜单存在重复命令名"


def test_command_menu_covers_catalog() -> None:
    """命令菜单必须覆盖帮助命令与命令目录中的全部命令，且帮助命令置顶。"""

    menu = build_telegram_command_menu()
    assert menu[0] == (HELP_COMMAND.name, HELP_COMMAND.summary)
    assert {name for name, _ in menu} == {spec.name for spec in (HELP_COMMAND, *COMMAND_CATALOG)}


def test_menu_descriptions_match_catalog_summaries() -> None:
    """菜单描述必须与命令目录的功能说明单一数据源一致。"""

    menu = dict(build_telegram_command_menu())
    for spec in COMMAND_CATALOG:
        assert menu[spec.name] == spec.summary


def test_help_text_renders_every_catalog_command() -> None:
    """帮助文本必须渲染命令目录中的每一条命令签名。"""

    for spec in COMMAND_CATALOG:
        assert f"/{spec.name}" in HELP_TEXT, f"帮助文本缺少命令: {spec.name}"
