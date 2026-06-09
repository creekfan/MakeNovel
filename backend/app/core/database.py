import os
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, inspect

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def _backup_db():
    """Copy current DB to data/backups/ with timestamp. Keep last 10 backups."""
    db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    if not db_path.exists():
        return

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"makenovel_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    # Rotate: keep last 10
    backups = sorted(backup_dir.glob("makenovel_*.db"))
    for old in backups[:-10]:
        old.unlink()


def _sync_migrate(conn):
    """Auto-add missing columns to existing tables so schema changes don't crash."""
    inspector = inspect(conn)

    for table_name in Base.metadata.tables:
        if not inspector.has_table(table_name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        for col in Base.metadata.tables[table_name].columns:
            if col.name not in existing and not col.primary_key and col.server_default is None:
                col_type = str(col.type).upper()
                if col.foreign_keys:
                    fk = list(col.foreign_keys)[0]
                    fk_clause = f" REFERENCES {fk.column.table.name}({fk.column.name})"
                else:
                    fk_clause = ""

                if col.default is not None:
                    default_val = col.default.arg if hasattr(col.default, "arg") else repr(col.default)
                    if callable(default_val) or not isinstance(default_val, (str, int, float, bool)):
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{fk_clause}"
                    else:
                        if isinstance(default_val, str):
                            default_val = f"'{default_val}'"
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{fk_clause} DEFAULT {default_val}"
                else:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{fk_clause}"
                conn.execute(text(sql))


async def init_db():
    _backup_db()
    async with engine.begin() as conn:
        await conn.run_sync(_sync_migrate)
        await conn.run_sync(Base.metadata.create_all)
