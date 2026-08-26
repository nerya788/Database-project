"""Database Connection Manager: a small pooled psycopg2 wrapper.

Every service in the app goes through `Database.cursor()` (or
`Database.cursor_with_notices()`) instead of opening a raw connection - the
pool, commit/rollback, and connection hand-back are all centralized here.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extensions import connection as PGConnection, cursor as PGCursor

from app.config import DB_CONFIG


class DatabaseError(Exception):
    """Raised when the pool itself cannot be created/reached."""


class Database:
    _pool: "pg_pool.SimpleConnectionPool | None" = None

    @classmethod
    def _ensure_pool(cls) -> "pg_pool.SimpleConnectionPool":
        if cls._pool is None:
            try:
                cls._pool = pg_pool.SimpleConnectionPool(1, 5, dsn=DB_CONFIG.dsn)
            except psycopg2.OperationalError as exc:
                raise DatabaseError(f"Could not connect to the database: {exc}") from exc
        return cls._pool

    @classmethod
    def test_connection(cls) -> tuple[bool, str]:
        """Used by the dashboard's connection-status indicator."""
        try:
            with cls.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
            return True, version
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not logged
            return False, str(exc)

    @classmethod
    @contextmanager
    def cursor(cls) -> Iterator[PGCursor]:
        """Borrow a pooled connection, yield a cursor, commit/rollback, return it."""
        pool = cls._ensure_pool()
        conn: PGConnection = pool.getconn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            pool.putconn(conn)

    @classmethod
    @contextmanager
    def cursor_with_notices(cls) -> Iterator[tuple[PGCursor, list]]:
        """Like `cursor()`, but also exposes the connection's live NOTICE log.

        Used by the Stage D routines screen so RAISE NOTICE / RAISE WARNING
        messages from functions, procedures and triggers can be shown to the
        user as real-time feedback.
        """
        pool = cls._ensure_pool()
        conn: PGConnection = pool.getconn()
        conn.notices.clear()
        cur = conn.cursor()
        try:
            yield cur, conn.notices
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            pool.putconn(conn)

    @classmethod
    def close_all(cls) -> None:
        if cls._pool is not None:
            cls._pool.closeall()
            cls._pool = None
