"""
Database Connector Abstraction Layer
=====================================
All database drivers must implement the DatabaseConnector ABC.
Switching databases requires only an env-var change (EIO_ACTIVE_DB).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Structured result returned by all database connectors."""

    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    sql: str = ""
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_markdown_table(self) -> str:
        """Render the result as a markdown table for LLM context."""
        if not self.columns or not self.rows:
            return "_No results_"
        header = "| " + " | ".join(self.columns) + " |"
        separator = "| " + " | ".join(["---"] * len(self.columns)) + " |"
        rows = [
            "| " + " | ".join(str(row.get(col, "")) for col in self.columns) + " |"
            for row in self.rows[:50]  # cap table size for LLM context
        ]
        return "\n".join([header, separator] + rows)


class SchemaInfo(BaseModel):
    """Structured schema metadata returned by get_schema()."""

    tables: dict[str, list[dict[str, str]]] = Field(
        default_factory=dict,
        description="table_name -> list of {column, type, nullable, primary_key}",
    )
    connector_type: str = ""
    database_name: str = ""
    sample_values: dict[str, str] = Field(
        default_factory=dict,
        description="table_name -> compact sample row string; helps LLM know what data exists",
    )

    def to_context_string(self) -> str:
        """Render schema as a compact string for LLM prompts."""
        lines = [f"Database: {self.database_name} ({self.connector_type})\n"]
        for table, columns in self.tables.items():
            col_defs = ", ".join(
                f"{c['column']} {c['type']}{'(PK)' if c.get('primary_key') == 'True' else ''}"
                for c in columns
            )
            lines.append(f"  TABLE {table}({col_defs})")
        # Include sample values if available (populated by SQLiteConnector.get_schema_with_samples)
        if self.sample_values:
            lines.append("\nSample values (to confirm data availability):")
            for table, samples in self.sample_values.items():
                if samples:
                    lines.append(f"  {table}: {samples}")
        return "\n".join(lines)


class DatabaseConnector(ABC):
    """
    Abstract base class for all EIO database connectors.

    Concrete implementations: SQLiteConnector, PostgreSQLConnector, etc.
    All connectors are registered in ConnectorRegistry and selected via
    the EIO_ACTIVE_DB environment variable.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish the database connection."""

    @abstractmethod
    def execute_query(self, sql: str, params: dict[str, Any] | None = None) -> QueryResult:
        """Execute a SQL query and return structured results."""

    @abstractmethod
    def get_schema(self) -> SchemaInfo:
        """Introspect and return the full database schema."""

    @abstractmethod
    def close(self) -> None:
        """Release the database connection."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return health status: {"status": "ok"|"error", "detail": str}."""

    def __enter__(self) -> "DatabaseConnector":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
