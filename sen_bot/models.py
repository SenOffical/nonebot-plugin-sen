"""Sen Bot 共享数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """支持 snake_case 与 camelCase 双向解析的数据模型。"""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="ignore")


class AllowedGroup(CamelModel):
    """允许使用命令的群配置。"""

    id: str = Field(description="群 ID。")
    desc: str | None = Field(default=None, description="运维备注。")


class ApiResponse[T](CamelModel):
    """后端统一响应格式。"""

    code: int = Field(description="业务状态码。")
    msg: str = Field(description="业务提示。")
    data: T | None = Field(default=None, description="响应数据。")


class RegisterDetail(CamelModel):
    """注册接口返回数据。"""

    user_id: int = Field(description="用户 ID。")
    secret: str = Field(description="注册密钥。")


class AccountDetail(CamelModel):
    """外部账户信息。"""

    id: int | None = Field(default=None, description="账户记录 ID。")
    user_id: int | None = Field(default=None, description="所属用户 ID。")
    provider: str = Field(description="账户类型。")
    external_uid: str = Field(description="外部账户 UID。")
    status: int = Field(description="账户状态。")


class PlatformBindingDetail(CamelModel):
    """平台绑定信息。"""

    id: int | None = Field(default=None, description="绑定记录 ID。")
    platform: str = Field(description="平台标识。")
    platform_user_id: str = Field(description="平台用户 ID。")
    display_name: str | None = Field(default=None, description="展示名。")
    extra: dict[str, object] | None = Field(default=None, description="平台元数据。")


class UserInfoDetail(CamelModel):
    """当前用户完整信息。"""

    id: int = Field(description="用户 ID。")
    secret: str = Field(description="注册密钥。")
    status: int = Field(description="用户状态。")
    ban_reason: str | None = Field(default=None, description="封禁原因。")
    accounts: list[AccountDetail] = Field(default_factory=list, description="外部账户列表。")
    platform_bindings: list[PlatformBindingDetail] = Field(
        default_factory=list,
        description="平台绑定列表。",
    )
