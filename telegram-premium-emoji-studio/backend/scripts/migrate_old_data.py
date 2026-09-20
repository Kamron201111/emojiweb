"""CLI: migrate the original bot's JSON data into the new database.

Usage:
    python -m scripts.migrate_old_data /path/to/old/bot/dir

Idempotent — safe to run multiple times. Never modifies the source files.
"""
from __future__ import annotations

import asyncio
import sys

from app.core.database import SessionLocal, init_db
from app.services.migration_service import migrate


async def _run(src_dir: str) -> None:
    await init_db()
    async with SessionLocal() as session:
        report = await migrate(session, src_dir)
    print("Migration complete:")
    for k, v in report.items():
        print(f"  {k}: {v}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Foydalanish: python -m scripts.migrate_old_data <eski_bot_papkasi>")
        raise SystemExit(1)
    asyncio.run(_run(sys.argv[1]))


if __name__ == "__main__":
    main()
