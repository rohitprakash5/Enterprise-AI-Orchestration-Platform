"""
Database Connector Stubs
========================
Stub connectors for all supported databases.
Each raises NotImplementedError with installation instructions.
Register the fully-implemented connector here when ready.
"""

from __future__ import annotations

from typing import Any

from eio.connectors.databases.base import DatabaseConnector, QueryResult, SchemaInfo


def _not_implemented(connector: str, package: str, env_var: str) -> None:
    raise NotImplementedError(
        f"{connector} connector is not yet implemented.\n"
        f"  1. Install the driver: pip install {package}\n"
        f"  2. Set {env_var} in your .env file\n"
        f"  3. Implement the connector in eio/connectors/databases/{connector.lower()}_connector.py\n"
        f"     by subclassing DatabaseConnector and decorating with @ConnectorRegistry.register('{connector.lower()}')"
    )


class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL connector stub. Implement using psycopg2 or asyncpg."""
    def connect(self) -> None: _not_implemented("PostgreSQL", "psycopg2-binary", "EIO_POSTGRES_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("PostgreSQL", "psycopg2-binary", "EIO_POSTGRES_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("PostgreSQL", "psycopg2-binary", "EIO_POSTGRES_URL")  # type: ignore
    def close(self) -> None: _not_implemented("PostgreSQL", "psycopg2-binary", "EIO_POSTGRES_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("PostgreSQL", "psycopg2-binary", "EIO_POSTGRES_URL")  # type: ignore


class SQLServerConnector(DatabaseConnector):
    """SQL Server connector stub. Implement using pyodbc."""
    def connect(self) -> None: _not_implemented("SQLServer", "pyodbc", "EIO_SQLSERVER_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("SQLServer", "pyodbc", "EIO_SQLSERVER_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("SQLServer", "pyodbc", "EIO_SQLSERVER_URL")  # type: ignore
    def close(self) -> None: _not_implemented("SQLServer", "pyodbc", "EIO_SQLSERVER_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("SQLServer", "pyodbc", "EIO_SQLSERVER_URL")  # type: ignore


class SnowflakeConnector(DatabaseConnector):
    """Snowflake connector stub. Implement using snowflake-sqlalchemy."""
    def connect(self) -> None: _not_implemented("Snowflake", "snowflake-sqlalchemy", "EIO_SNOWFLAKE_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("Snowflake", "snowflake-sqlalchemy", "EIO_SNOWFLAKE_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("Snowflake", "snowflake-sqlalchemy", "EIO_SNOWFLAKE_URL")  # type: ignore
    def close(self) -> None: _not_implemented("Snowflake", "snowflake-sqlalchemy", "EIO_SNOWFLAKE_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("Snowflake", "snowflake-sqlalchemy", "EIO_SNOWFLAKE_URL")  # type: ignore


class OracleConnector(DatabaseConnector):
    """Oracle connector stub. Implement using cx_Oracle."""
    def connect(self) -> None: _not_implemented("Oracle", "cx_Oracle", "EIO_ORACLE_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("Oracle", "cx_Oracle", "EIO_ORACLE_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("Oracle", "cx_Oracle", "EIO_ORACLE_URL")  # type: ignore
    def close(self) -> None: _not_implemented("Oracle", "cx_Oracle", "EIO_ORACLE_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("Oracle", "cx_Oracle", "EIO_ORACLE_URL")  # type: ignore


class MySQLConnector(DatabaseConnector):
    """MySQL connector stub. Implement using PyMySQL."""
    def connect(self) -> None: _not_implemented("MySQL", "PyMySQL", "EIO_MYSQL_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("MySQL", "PyMySQL", "EIO_MYSQL_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("MySQL", "PyMySQL", "EIO_MYSQL_URL")  # type: ignore
    def close(self) -> None: _not_implemented("MySQL", "PyMySQL", "EIO_MYSQL_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("MySQL", "PyMySQL", "EIO_MYSQL_URL")  # type: ignore


class DuckDBConnector(DatabaseConnector):
    """DuckDB connector stub. Implement using duckdb-engine."""
    def connect(self) -> None: _not_implemented("DuckDB", "duckdb-engine", "EIO_DUCKDB_PATH")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("DuckDB", "duckdb-engine", "EIO_DUCKDB_PATH")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("DuckDB", "duckdb-engine", "EIO_DUCKDB_PATH")  # type: ignore
    def close(self) -> None: _not_implemented("DuckDB", "duckdb-engine", "EIO_DUCKDB_PATH")
    def health_check(self) -> dict[str, Any]: _not_implemented("DuckDB", "duckdb-engine", "EIO_DUCKDB_PATH")  # type: ignore


class DatabricksConnector(DatabaseConnector):
    """Databricks SQL connector stub. Implement using databricks-sql-connector."""
    def connect(self) -> None: _not_implemented("Databricks", "databricks-sql-connector", "EIO_DATABRICKS_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("Databricks", "databricks-sql-connector", "EIO_DATABRICKS_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("Databricks", "databricks-sql-connector", "EIO_DATABRICKS_URL")  # type: ignore
    def close(self) -> None: _not_implemented("Databricks", "databricks-sql-connector", "EIO_DATABRICKS_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("Databricks", "databricks-sql-connector", "EIO_DATABRICKS_URL")  # type: ignore


class DB2Connector(DatabaseConnector):
    """IBM DB2 connector stub. Implement using ibm-db-sa."""
    def connect(self) -> None: _not_implemented("DB2", "ibm-db-sa", "EIO_DB2_URL")
    def execute_query(self, sql: str, params: Any = None) -> QueryResult: _not_implemented("DB2", "ibm-db-sa", "EIO_DB2_URL")  # type: ignore
    def get_schema(self) -> SchemaInfo: _not_implemented("DB2", "ibm-db-sa", "EIO_DB2_URL")  # type: ignore
    def close(self) -> None: _not_implemented("DB2", "ibm-db-sa", "EIO_DB2_URL")
    def health_check(self) -> dict[str, Any]: _not_implemented("DB2", "ibm-db-sa", "EIO_DB2_URL")  # type: ignore
