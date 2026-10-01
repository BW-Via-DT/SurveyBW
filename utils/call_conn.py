import os

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv

load_dotenv()  # em local lê o .env; no Render não faz nada


def get_db_connection():
    """Devolve a connection string (DSN/URL) do PostgreSQL.

    Local:   DATABASE_URL no .env (External Database URL do Render, com ?sslmode=require)
    Render:  DATABASE_URL = Internal Database URL
    """
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError("DATABASE_URL não está definida.")
    return url


class Row(tuple):
    """Tuplo que também permite row.NomeColuna (sem distinguir maiúsculas),
    para manter compatibilidade com o código escrito para pyodbc."""

    def __new__(cls, values, names):
        obj = super().__new__(cls, values)
        obj._names = {n.lower(): i for i, n in enumerate(names)}
        return obj

    def __getattr__(self, name):
        try:
            return self[self._names[name.lower()]]
        except KeyError:
            raise AttributeError(name)


class RowCursor(psycopg2.extensions.cursor):
    def _wrap(self, r):
        if r is None:
            return None
        return Row(r, [d[0] for d in self.description])

    def fetchone(self):
        return self._wrap(super().fetchone())

    def fetchall(self):
        return [self._wrap(r) for r in super().fetchall()]

    def fetchmany(self, size=None):
        rows = super().fetchmany(size) if size else super().fetchmany()
        return [self._wrap(r) for r in rows]


def connect():
    return psycopg2.connect(
        get_db_connection(),
        cursor_factory=RowCursor,
        connect_timeout=10,
    )