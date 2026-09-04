"""Sen NoneBot2 配置模型。"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import AllowedGroup


class SenSettings(BaseSettings):
    """Sen Bot 运行配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str = Field(
        default="http://localhost:8010/api/v1/bot",
        validation_alias=AliasChoices("SEN_API_BASE_URL"),
        description="后端 Bot API 地址。",
    )
    bot_secret: str = Field(
        default="",
        validation_alias=AliasChoices("SEN_BOT_SECRET", "KOISHI_SECRET"),
        description="后端 X-Bot-Secret 鉴权密钥。",
    )
    allowed_groups_json: str = Field(
        default="[]",
        validation_alias=AliasChoices("SEN_ALLOWED_GROUPS"),
        description="允许使用私聊命令的群配置 JSON 数组。",
    )
    membership_cache_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("SEN_MEMBERSHIP_CACHE_ENABLED"),
        description="是否启用 Redis 群成员正向缓存。",
    )
    redis_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("SEN_REDIS_HOST"),
        description="Redis 主机。",
    )
    redis_port: int = Field(
        default=6379,
        validation_alias=AliasChoices("SEN_REDIS_PORT"),
        description="Redis 端口。",
    )
    redis_password: str = Field(
        default="",
        validation_alias=AliasChoices("SEN_REDIS_PASSWORD"),
        description="Redis 密码。",
    )
    redis_db: int = Field(
        default=0,
        validation_alias=AliasChoices("SEN_REDIS_DB"),
        description="Redis DB 编号。",
    )
    membership_cache_ttl_days: int = Field(
        default=7,
        validation_alias=AliasChoices("SEN_MEMBERSHIP_CACHE_TTL_DAYS"),
        ge=1,
        description="正向群成员缓存 TTL，单位为天。",
    )
    membership_cache_key_prefix: str = Field(
        default="sen:membership",
        validation_alias=AliasChoices("SEN_MEMBERSHIP_CACHE_KEY_PREFIX"),
        description="Redis 群成员缓存 key 前缀。",
    )
    backend_timeout_seconds: float = Field(
        default=10.0,
        validation_alias=AliasChoices("SEN_BACKEND_TIMEOUT_SECONDS"),
        gt=0,
        description="后端 HTTP 请求超时时间。",
    )
    platform_api_retry_times: int = Field(
        default=2,
        validation_alias=AliasChoices("SEN_PLATFORM_API_RETRY_TIMES"),
        ge=0,
        description="平台 Bot API 临时失败后的重试次数。",
    )
    platform_api_retry_interval_seconds: float = Field(
        default=1.0,
        validation_alias=AliasChoices("SEN_PLATFORM_API_RETRY_INTERVAL_SECONDS"),
        ge=0,
        description="平台 Bot API 重试间隔秒数。",
    )

    @property
    def allowed_groups(self) -> list[AllowedGroup]:
        """解析允许群配置。

        Returns:
            去重并过滤空 ID 后的群配置列表。
        """

        return normalize_allowed_groups(parse_allowed_groups(self.allowed_groups_json))


def parse_allowed_groups(raw: str) -> list[AllowedGroup]:
    """从 JSON 字符串解析允许群配置。

    Args:
        raw: `SEN_ALLOWED_GROUPS` 环境变量原始字符串。

    Returns:
        解析后的允许群配置列表；非法 JSON 返回空列表。
    """

    try:
        payload = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    groups: list[AllowedGroup] = []
    for item in payload:
        group = _parse_allowed_group_item(item)
        if group is not None:
            groups.append(group)
    return groups


def _parse_allowed_group_item(item: Any) -> AllowedGroup | None:
    """解析单个群配置项。

    Args:
        item: JSON 数组中的单个元素。

    Returns:
        合法群配置；非法项返回 `None`。
    """

    if isinstance(item, str):
        return AllowedGroup(id=item)
    if isinstance(item, dict):
        group_id = item.get("id")
        if isinstance(group_id, str):
            desc = item.get("desc")
            return AllowedGroup(id=group_id, desc=desc if isinstance(desc, str) else None)
    return None


def normalize_allowed_groups(groups: list[AllowedGroup]) -> list[AllowedGroup]:
    """过滤空 ID 并按 ID 去重。

    Args:
        groups: 待归一化的群配置列表。

    Returns:
        后出现的同 ID 配置覆盖前配置后的列表。
    """

    normalized: dict[str, AllowedGroup] = {}
    for group in groups:
        if group.id:
            normalized[group.id] = AllowedGroup(id=group.id, desc=group.desc or None)
    return list(normalized.values())


@lru_cache(maxsize=1)
def get_sen_settings() -> SenSettings:
    """读取并缓存 Sen Bot 配置。

    Returns:
        当前进程的 Sen Bot 配置对象。
    """

    return SenSettings()

