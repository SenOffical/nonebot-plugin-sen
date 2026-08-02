"""Sen 后端 API 客户端。"""

from __future__ import annotations

from typing import Any, TypeVar

import httpx
from nonebot import logger
from pydantic import TypeAdapter

from .config import SenSettings
from .models import ApiResponse

T = TypeVar("T")


ERROR_MSG: dict[int, str] = {
    -1: "后端服务暂不可用，请稍后重试。",
    40104: "无效密钥，请检查后重试。",
    40402: "该 UID 未绑定。",
    40403: "你尚未注册，请先使用 /register 注册。",
    40901: "你已经注册过了，请勿重复注册。",
    40902: "该 UID 已被其他用户绑定。",
    40903: "已达到绑定数量上限。",
    40904: "该平台已绑定到其他用户，请使用 /merge 合并。",
}


def err_msg(code: int, fallback: str) -> str:
    """将后端错误码转换为用户可见提示。

    Args:
        code: 后端业务错误码。
        fallback: 未知错误码时使用的兜底提示。

    Returns:
        用户可见中文错误提示。
    """

    return ERROR_MSG.get(code, f"操作失败（错误码 {code}），请稍后重试。")


def redact_for_log(value: Any) -> Any:
    """递归脱敏日志 payload。

    Args:
        value: 准备写入日志的任意数据。

    Returns:
        已将 secret、password、token 字段替换为 `<redacted>` 的副本。
    """

    if isinstance(value, list):
        return [redact_for_log(item) for item in value]
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for key, item in value.items():
        lower_key = key.lower()
        if "secret" in lower_key or "password" in lower_key or "token" in lower_key:
            result[key] = "<redacted>"
        else:
            result[key] = redact_for_log(item)
    return result


class BackendApiClient:
    """封装 Sen 后端 Koishi 兼容 API。"""

    def __init__(
        self,
        settings: SenSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """初始化后端 API 客户端。

        Args:
            settings: Sen Bot 配置。
            transport: 测试时可注入的 httpx transport。
        """

        self._settings = settings
        self._transport = transport

    async def post(
        self,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data_type: type[T] | None = None,
    ) -> ApiResponse[T]:
        """向后端发送 POST 请求。

        Args:
            path: API 路径，以 `/` 开头。
            data: JSON 请求体。
            params: URL query 参数。
            data_type: 响应 `data` 的 Pydantic 模型类型。

        Returns:
            解析后的统一响应；网络失败时返回 `code=-1`。
        """

        url = f"{self._settings.api_base_url.rstrip('/')}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-Koishi-Secret": self._settings.bot_secret,
        }
        logger.info(f"[->] POST {path} body={redact_for_log(data or {})}")
        try:
            async with httpx.AsyncClient(  # noqa: F823
                timeout=self._settings.backend_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(url, headers=headers, json=data, params=params)
                response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.error(f"API POST {path} 失败: {exc}")
            if isinstance(exc, httpx.HTTPStatusError):
                resp_body = exc.response.text[:200] if exc.response.text else ""
                logger.warning(f"后端 HTTP 错误响应: {resp_body}")
            return ApiResponse[T](code=-1, msg="后端服务暂不可用，请稍后重试", data=None)

        api_response = _parse_api_response(payload, data_type)
        response_data = api_response.data
        log_data = response_data.model_dump() if hasattr(
            response_data, "model_dump"
        ) else response_data
        logger.info(
            f"[<-] {path} code={api_response.code} "
            f"msg={api_response.msg} data={redact_for_log(log_data)}"
        )
        return api_response


def _parse_api_response[T](payload: Any, data_type: type[T] | None) -> ApiResponse[T]:
    """解析后端统一响应。

    Args:
        payload: `response.json()` 的原始结果。
        data_type: 响应 `data` 的 Pydantic 模型类型。

    Returns:
        解析后的统一响应。
    """

    if data_type is None:
        return ApiResponse[Any].model_validate(payload)
    adapter = TypeAdapter(ApiResponse[data_type])  # type: ignore[valid-type]
    return adapter.validate_python(payload)
