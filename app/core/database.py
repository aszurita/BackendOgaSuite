import logging
import pymysql
import pymysql.cursors
from collections import deque
from contextlib import contextmanager
from threading import Semaphore, Lock
from typing import Generator

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: "ConnectionPool | None" = None


class ConnectionPool:
    """Pool de conexiones PyMySQL thread-safe para MySQL."""

    def __init__(self, pool_size: int = 10, timeout: int = 30):
        self._pool_size = pool_size
        self._timeout = timeout
        self._semaphore = Semaphore(pool_size)
        self._pool: deque = deque()
        self._lock = Lock()

        for _ in range(pool_size // 2):
            try:
                self._pool.append(self._create_connection())
            except Exception as e:
                logger.warning("No se pudo pre-calentar conexion: %s", e)

    def _create_connection(self) -> pymysql.connections.Connection:
        conn = pymysql.connect(
            host=settings.SQL_HOST,
            port=settings.SQL_PORT,
            user=settings.SQL_USER,
            password=settings.SQL_PASSWORD,
            database=settings.SQL_DATABASE,
            charset=settings.SQL_CHARSET,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=self._timeout,
            autocommit=False,
        )
        return conn

    def _is_alive(self, conn: pymysql.connections.Connection) -> bool:
        try:
            conn.ping(reconnect=True)
            return True
        except Exception:
            return False

    @contextmanager
    def acquire(self) -> Generator[pymysql.connections.Connection, None, None]:
        acquired = self._semaphore.acquire(timeout=self._timeout)
        if not acquired:
            raise TimeoutError("No se obtuvo conexion del pool en el tiempo limite")
        try:
            with self._lock:
                conn = self._pool.popleft() if self._pool else None

            if conn is None or not self._is_alive(conn):
                conn = self._create_connection()

            try:
                yield conn
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    conn = self._create_connection()
                raise
            finally:
                with self._lock:
                    self._pool.append(conn)
        finally:
            self._semaphore.release()

    def close_all(self):
        with self._lock:
            while self._pool:
                try:
                    self._pool.popleft().close()
                except Exception:
                    pass


def init_pool() -> None:
    global _pool
    _pool = ConnectionPool(
        pool_size=settings.SQL_POOL_SIZE,
        timeout=settings.SQL_POOL_TIMEOUT,
    )
    logger.info(
        "Pool MySQL inicializado — host=%s:%d db=%s (size=%d)",
        settings.SQL_HOST, settings.SQL_PORT, settings.SQL_DATABASE, settings.SQL_POOL_SIZE,
    )


def close_pool() -> None:
    global _pool
    if _pool:
        _pool.close_all()
        _pool = None
        logger.info("Pool MySQL cerrado")


def get_db() -> Generator[pymysql.connections.Connection, None, None]:
    """FastAPI dependency: entrega conexion del pool con commit/rollback automatico."""
    if _pool is None:
        raise RuntimeError("Pool de BD no inicializado. Llamar a init_pool() primero.")
    with _pool.acquire() as conn:
        yield conn


def check_db_health() -> bool:
    """Verifica que la BD MySQL responde."""
    try:
        if _pool is None:
            return False
        with _pool.acquire() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:
        return False
