"""
Database Connectors Package
============================
Auto-registers all connectors into the ConnectorRegistry on import.
"""

from eio.connectors.databases.registry import ConnectorRegistry
from eio.connectors.databases.sqlite_connector import SQLiteConnector

# Register active connector
ConnectorRegistry.register("sqlite")(SQLiteConnector)

# Register stubs (raise NotImplementedError when instantiated)
from eio.connectors.databases.stubs import (  # noqa: E402
    DB2Connector,
    DatabricksConnector,
    DuckDBConnector,
    MySQLConnector,
    OracleConnector,
    PostgreSQLConnector,
    SQLServerConnector,
    SnowflakeConnector,
)

ConnectorRegistry.register("postgresql")(PostgreSQLConnector)
ConnectorRegistry.register("sqlserver")(SQLServerConnector)
ConnectorRegistry.register("snowflake")(SnowflakeConnector)
ConnectorRegistry.register("oracle")(OracleConnector)
ConnectorRegistry.register("mysql")(MySQLConnector)
ConnectorRegistry.register("duckdb")(DuckDBConnector)
ConnectorRegistry.register("databricks")(DatabricksConnector)
ConnectorRegistry.register("db2")(DB2Connector)

__all__ = ["ConnectorRegistry", "SQLiteConnector"]
