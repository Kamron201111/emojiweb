"""Pricing, order idempotency, admin authorization tests."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_price_defaults_and_update(session):
    from app.services import pricing_service

    # Missing row seeds a default.
    p = await pricing_service.get_price(session, "logo")
    assert p == 15

    await pricing_service.set_price(session, "logo", 42)
    assert await pricing_service.get_price(session, "logo") == 42

    prices = await pricing_service.all_prices(session)
    assert prices["logo"] == 42
    assert "code" in prices and "pf" in prices


async def test_order_idempotency(session, user):
    from app.services import order_service

    key = "same-key-123"
    o1 = await order_service.create_order(
        session, user, kind="logo", pack_kind="emoji", text="Hi",
        templates="1", outer_hex=None, inner_hex=None, color_hex=None,
        font_key=None, pack_title="", idempotency_key=key,
    )
    o2 = await order_service.create_order(
        session, user, kind="logo", pack_kind="emoji", text="Hi",
        templates="1", outer_hex=None, inner_hex=None, color_hex=None,
        font_key=None, pack_title="", idempotency_key=key,
    )
    assert o1.id == o2.id  # same key -> same order, no duplicate


async def test_order_text_length_limit(session, user):
    from app.services import order_service

    with pytest.raises(order_service.OrderError):
        await order_service.create_order(
            session, user, kind="pf", pack_kind="emoji",
            text="toolongname", templates="1",  # pf max is 5
            outer_hex=None, inner_hex=None, color_hex=None, font_key=None, pack_title="",
        )


async def test_stale_price_blocks_fulfillment(session, user, monkeypatch):
    from app.services import order_service, pricing_service

    await pricing_service.set_price(session, "logo", 20)
    order = await order_service.create_order(
        session, user, kind="logo", pack_kind="emoji", text="Hi",
        templates="1", outer_hex=None, inner_hex=None, color_hex=None,
        font_key=None, pack_title="",
    )
    # Paying the OLD amount (10) when current price*count is 20 must be rejected.
    with pytest.raises(order_service.OrderError):
        await order_service.fulfill_after_payment(session, order, paid_amount=10, bot=None)
    assert order.status == "cancelled"


def test_admin_authorization():
    from app.core.config import Settings

    s = Settings(admin_ids="111,222")
    assert s.is_admin(111) is True
    assert s.is_admin(222) is True
    assert s.is_admin(333) is False
    assert s.admin_id_list == [111, 222]
