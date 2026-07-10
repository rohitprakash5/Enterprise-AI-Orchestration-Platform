"""
SQLite Database Connector
=========================
Concrete implementation of DatabaseConnector for SQLite.
Used as the demo connector in the EIO MVP.

Connection string is controlled by EIO_SQLITE_PATH environment variable.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import sqlparse
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from eio.connectors.databases.base import DatabaseConnector, QueryResult, SchemaInfo


class SQLiteConnector(DatabaseConnector):
    """
    SQLite connector using SQLAlchemy Core.
    The same SQLAlchemy pattern is reused in all other SQL connectors —
    only the connection URL changes.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = str(Path(db_path).resolve())
        self._engine: Engine | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
        )

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def _ensure_connected(self) -> Engine:
        if self._engine is None:
            self.connect()
        return self._engine  # type: ignore[return-value]

    # ── query ──────────────────────────────────────────────────────────────

    def execute_query(self, sql: str, params: dict[str, Any] | None = None) -> QueryResult:
        engine = self._ensure_connected()
        start = time.perf_counter()
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                elapsed_ms = (time.perf_counter() - start) * 1000
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=round(elapsed_ms, 2),
                    sql=sql,
                )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return QueryResult(
                sql=sql,
                error=str(exc),
                execution_time_ms=round(elapsed_ms, 2),
            )

    # ── schema ─────────────────────────────────────────────────────────────

    def get_schema(self) -> SchemaInfo:
        engine = self._ensure_connected()
        inspector = inspect(engine)
        tables: dict[str, list[dict[str, str]]] = {}
        pk_map: dict[str, set[str]] = {}

        for table_name in inspector.get_table_names():
            pk_cols = {c for c in inspector.get_pk_constraint(table_name).get("constrained_columns", [])}
            pk_map[table_name] = pk_cols
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append(
                    {
                        "column": col["name"],
                        "type": str(col["type"]),
                        "nullable": str(col.get("nullable", True)),
                        "primary_key": str(col["name"] in pk_cols),
                    }
                )
            tables[table_name] = columns

        # Collect compact sample values for each table so LLM knows what data exists
        sample_values: dict[str, str] = {}
        with engine.connect() as conn:
            for table_name in tables:
                try:
                    row = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1")).fetchone()  # noqa: S608
                    if row:
                        sample_values[table_name] = str(dict(row._mapping))
                except Exception:
                    pass
                # Also get distinct years/quarters for time-series tables
                try:
                    years = conn.execute(
                        text(f"SELECT DISTINCT year FROM {table_name} ORDER BY year")  # noqa: S608
                    ).fetchall()
                    if years:
                        yr_list = [str(r[0]) for r in years]
                        sample_values[table_name] = (
                            sample_values.get(table_name, "") +
                            f" | years available: {', '.join(yr_list)}"
                        )
                except Exception:
                    pass

        db_path = Path(self._db_path)
        return SchemaInfo(
            tables=tables,
            connector_type="sqlite",
            database_name=db_path.stem,
            sample_values=sample_values,
        )

    # ── health ─────────────────────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        try:
            result = self.execute_query("SELECT 1 AS ping")
            if result.success:
                return {"status": "ok", "connector": "sqlite", "path": self._db_path}
            return {"status": "error", "connector": "sqlite", "detail": result.error}
        except Exception as exc:
            return {"status": "error", "connector": "sqlite", "detail": str(exc)}
