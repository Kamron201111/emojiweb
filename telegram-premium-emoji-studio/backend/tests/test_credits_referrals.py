"""Credit transaction safety + referral anti-abuse tests."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_consume_credit_decrements_and_blocks_at_zero(session, user):
    from app.services import credit_service

    await credit_service.grant_credit(session, user.id, 1, reason="test")
    assert await credit_service.get_balance(session, user.id) == 1

    ok = await credit_service.consume_credit(session, user.id)
    assert ok is True
    assert await credit_service.get_balance(session, user.id) == 0

    # No credits left -> refuse.
    ok2 = await credit_service.consume_credit(session, user.id)
    assert ok2 is False
    assert await credit_service.get_balance(session, user.id) == 0


async def test_credit_ledger_records_transactions(session, user):
    from app.services import credit_service

    await credit_service.grant_credit(session, user.id, 2, reason="admin_grant")
    await credit_service.consume_credit(session, user.id)
    txns = await credit_service.list_transactions(session, user.id)
    assert len(txns) == 2
    assert txns[0].amount == -1  # most recent first
    assert txns[0].balance_after == 1


async def test_referral_self_referral_rejected(session, user):
    from app.services import referral_service

    ok = await referral_service.record_referral(session, user.id, user.id)
    assert ok is False


async def test_referral_duplicate_ignored(session):
    from app.models import User
    from app.services import referral_service

    referred = User(id=2002, language="uz")
    session.add(referred)
    await session.flush()

    assert await referral_service.record_referral(session, 2002, 3003) is True
    # Second referrer for same user is ignored.
    assert await referral_service.record_referral(session, 2002, 4004) is False


async def test_referral_reward_granted_once(session):
    from app.models import User
    from app.services import credit_service, referral_service

    referrer = User(id=5005, language="uz", credits=0)
    referred = User(id=6006, language="uz")
    session.add_all([referrer, referred])
    await session.flush()

    await referral_service.record_referral(session, 6006, 5005)

    first = await referral_service.reward_if_pending(session, 6006)
    assert first == 5005
    assert await credit_service.get_balance(session, 5005) == 1

    # Idempotent — second call grants nothing.
    second = await referral_service.reward_if_pending(session, 6006)
    assert second is None
    assert await credit_service.get_balance(session, 5005) == 1
