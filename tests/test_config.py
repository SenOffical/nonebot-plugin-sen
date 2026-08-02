"""配置解析测试。"""

from __future__ import annotations

from sen_bot.config import normalize_allowed_groups, parse_allowed_groups
from sen_bot.models import AllowedGroup


def test_解析允许群JSON数组() -> None:
    """验证允许群 JSON 数组可解析为模型。"""

    groups = parse_allowed_groups('[{"id":"-1001","desc":"主群"}]')
    assert groups == [AllowedGroup(id="-1001", desc="主群")]


def test_过滤空ID并按后者覆盖() -> None:
    """验证允许群归一化规则。"""

    groups = normalize_allowed_groups(
        [
            AllowedGroup(id="", desc="空"),
            AllowedGroup(id="-1001", desc="旧"),
            AllowedGroup(id="-1001", desc="新"),
        ]
    )
    assert groups == [AllowedGroup(id="-1001", desc="新")]


def test_非法允许群JSON返回空列表() -> None:
    """验证非法允许群配置不会炸进程。"""

    assert parse_allowed_groups("{bad") == []

