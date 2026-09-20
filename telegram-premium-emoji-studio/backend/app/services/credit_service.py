"""Credit ledger — transactional grant/consume so double-clicks can't
duplicate or double-spend credits.

Consumption uses ``SELECT ... FOR UPDATE`` (row lock) where the backend
supports it (PostgreSQL). On SQLite the surrounding transaction + the balance
check still prevents negative balances; combined with per-order idempotency
keys this makes double-spend safe in practice.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreditTransaction, User


async def get_balance(session: AsyncSession, user_id: int) -> int:
    user = await session.get(User, user_id)
    return int(user.credits) if user else 0


async def _lock_user(session: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    # with_for_update is a no-op on SQLite but real on PostgreSQL.
    try:
        stmt = stmt.with_for_update()
    except Exception:  # pragma: no cover
        pass
    return (await session.execute(stmt)).scalar_one_or_none()


async def grant_credit(
    session: AsyncSession, user_id: int, amount: int = 1, reason: str = "admin_grant",
    order_id: Optional[int] = None,
) -> int:
    user = await _lock_user(session, user_id)
    if user is None:
        return 0
    user.credits = int(user.credits) + amount
    session.add(
        CreditTransaction(
            user_id=user_id, amount=amount, reason=reason,
            order_id=order_id, balance_after=user.credits,
        )
    )
    await session.flush()
    return user.credits


async def consume_credit(
    session: AsyncSession, user_id: int, reason: str = "order_use",
    order_id: Optional[int] = None,
) -> bool:
    """Atomically consume one credit. Returns False if none available."""
    user = await _lock_user(session, user_id)
    if user is None or int(user.credits) <= 0:
        return False
    user.credits = int(user.credits) - 1
    session.add(
        CreditTransaction(
            user_id=user_id, amount=-1, reason=reason,
            order_id=order_id, balance_after=user.credits,
        )
    )
    await session.flush()
    return True


async def list_transactions(session: AsyncSession, user_id: int, limit: int = 20):
    stmt = (
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.id.desc())
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()
