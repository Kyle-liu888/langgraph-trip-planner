"""Run migrations with the DSN from backend/.env; never print credentials."""
import asyncio
import sys

from alembic import context

from app.config import get_settings
from app.database import Base, create_database


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    url = get_settings().secret_value("database_url")
    if not url:
        raise RuntimeError("请先在 backend/.env 配置 DATABASE_URL")
    engine, _ = create_database(url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(run())
