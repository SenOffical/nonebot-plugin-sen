"""命令业务逻辑测试。"""

from __future__ import annotations

from sen_bot.commands.bind import handle_bind
from sen_bot.commands.info import handle_info
from sen_bot.commands.merge import handle_merge
from sen_bot.commands.register import handle_register
from sen_bot.commands.secret import handle_secret
from sen_bot.commands.shared import check_authorized
from sen_bot.commands.sync import handle_sync
from sen_bot.commands.unbind import handle_unbind
from sen_bot.models import ApiResponse, RegisterDetail, UserInfoDetail

from .conftest import FakeApi, FakeBot, make_context, make_settings


async def test_注册成功返回密钥并携带extra() -> None:
    """验证注册成功回复和 API payload。"""

    ctx = make_context(
        ApiResponse[RegisterDetail](
            code=200,
            msg="请求成功",
            data=RegisterDetail(user_id=1, secret="sk-aaaa"),
        )
    )
    result = await handle_register(ctx)
    assert result is not None
    assert "sk-aaaa" in result
    api = ctx.api
    assert isinstance(api, FakeApi)
    assert api.calls[0]["path"] == "/register"
    assert api.calls[0]["data"]["extra"] == {
        "first_name": "Test",
        "last_name": "User",
        "language_code": "zh-hans",
    }


async def test_绑定成功返回纯文本() -> None:
    """验证绑定成功使用稳定纯文本回复。"""

    ctx = make_context(ApiResponse(code=200, msg="请求成功", data={"id": 1}))
    result = await handle_bind(ctx, "1234567890123456")
    assert result == "✅ UID 1234567890123456 绑定成功。"


async def test_解绑参数错误() -> None:
    """验证解绑 UID 参数校验。"""

    ctx = make_context(ApiResponse(code=200, msg="请求成功", data={"id": 1}))
    assert await handle_unbind(ctx, "bad") == "⚠️ 用法：/unbind xxxxxxxxxxxxxxxx"


async def test_密钥更新成功返回新密钥() -> None:
    """验证 secret 更新成功回复。"""

    ctx = make_context(
        ApiResponse[RegisterDetail](
            code=200,
            msg="请求成功",
            data=RegisterDetail(user_id=1, secret="sk-new"),
        )
    )
    result = await handle_secret(ctx)
    assert result is not None
    assert "sk-new" in result


async def test_信息展示完整账号信息() -> None:
    """验证 info 展示 secret、支付宝 UID 和平台绑定。"""

    ctx = make_context(
        ApiResponse[UserInfoDetail](
            code=200,
            msg="请求成功",
            data=UserInfoDetail.model_validate({
                "id": 1,
                "secret": "sk-info",
                "status": 0,
                "accounts": [
                    {"provider": "alipay", "externalUid": "1234567890123456", "status": 0}
                ],
                "platformBindings": [
                    {"platform": "tg", "platformUserId": "123456789", "displayName": "@test"}
                ],
            }),
        )
    )
    result = await handle_info(ctx)
    assert result is not None
    assert "用户 ID: 1" in result
    assert "sk-info" in result
    assert "1234567890123456" in result
    assert "tg: 123456789" in result


async def test_同步密钥格式错误() -> None:
    """验证 sync secret 格式校验。"""

    ctx = make_context(ApiResponse(code=200, msg="请求成功", data={"id": 1}))
    assert await handle_sync(ctx, "bad") == "⚠️ 用法：/sync sk-xxxx-xxxx-xxxx-xxxx"


async def test_合并目标密钥无效返回映射提示() -> None:
    """验证 merge 错误码映射。"""

    ctx = make_context(ApiResponse(code=40104, msg="无效", data=None))
    result = await handle_merge(ctx, "sk-aaaa-bbbb")
    assert result == "无效密钥，请检查后重试。"


async def test_守卫拒绝时返回错误提示且不调用后端() -> None:
    """验证允许群守卫拒绝时直接返回错误提示，不会调用后端 API。"""

    ctx = make_context(
        ApiResponse(code=200, msg="请求成功", data={"id": 1}),
        SEN_ALLOWED_GROUPS='[{"id":"-1001","desc":"主群"}]',
    )
    ctx.bot = FakeBot({"get_chat_member": {"status": "left"}})  # type: ignore[assignment]
    ctx.settings = make_settings(SEN_ALLOWED_GROUPS='[{"id":"-1001","desc":"主群"}]')
    result = await check_authorized(ctx)
    assert result is not None
    assert "你不在允许的群组中" in result
    api = ctx.api
    assert isinstance(api, FakeApi)
    assert api.calls == []

