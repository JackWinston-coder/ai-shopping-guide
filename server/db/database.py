from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from server.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL,
    avatar TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '新对话',
    state TEXT NOT NULL DEFAULT 'idle',
    summary_text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    products_json TEXT,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    title TEXT NOT NULL,
    sku_label TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    image_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    order_no TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    items_json TEXT NOT NULL,
    total_price REAL NOT NULL,
    address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
"""


_db_connection: aiosqlite.Connection | None = None


def _database_path() -> Path:
    raw = settings.database_url.removeprefix("sqlite+aiosqlite:///")
    return Path(raw)


async def init_db() -> None:
    global _db_connection
    db_path = _database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _db_connection = await aiosqlite.connect(db_path)
    _db_connection.row_factory = aiosqlite.Row
    await _db_connection.execute("PRAGMA journal_mode=WAL")
    await _db_connection.execute("PRAGMA busy_timeout=5000")
    await _db_connection.executescript(SCHEMA_SQL)
    await _db_connection.commit()


async def close_db() -> None:
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        _db_connection = None


async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    if _db_connection is None:
        await init_db()
    yield _db_connection
