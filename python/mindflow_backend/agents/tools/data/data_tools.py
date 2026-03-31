"""Data tools for MindFlow agents.

Provides database operations, CSV/JSON processing,
and data analysis capabilities.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

try:
    import sqlalchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    sqlalchemy = None
    create_engine = None
    text = None
    sessionmaker = None

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.data_schemas import CSV_PROCESSOR_SCHEMA, DATABASE_SCHEMA

_logger = get_logger(__name__)


class DatabaseTool(AsyncToolInterface):
    """Database operations tool with multi-database support."""
    
    def __init__(self, backend: Any | None = None):
        """Initialize the database tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "database_manager"
        self.description = "Database operations and query management"
        self._connections = {}
        self._engines = {}
        
        self._schema = DATABASE_SCHEMA
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute database operation.
        
        Args:
            action: Action to perform
            database_type: Database type
            connection_string: Connection string
            query: SQL query
            table_name: Table name
            
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"]
            database_type = kwargs.get("database_type", "sqlite")
            connection_string = kwargs.get("connection_string")
            query = kwargs.get("query")
            table_name = kwargs.get("table_name")
            
            if action == "connect":
                if not connection_string:
                    return self._format_result(
                        success=False,
                        error="Connection string required for connect action"
                    )
                return await self._connect_database(database_type, connection_string)
            elif action == "query":
                if not connection_string or not query:
                    return self._format_result(
                        success=False,
                        error="Connection string and query required for query action"
                    )
                return await self._execute_query(database_type, connection_string, query)
            elif action == "list_tables":
                if not connection_string:
                    return self._format_result(
                        success=False,
                        error="Connection string required for list_tables action"
                    )
                return await self._list_tables(database_type, connection_string)
            elif action == "schema":
                if not connection_string or not table_name:
                    return self._format_result(
                        success=False,
                        error="Connection string and table name required for schema action"
                    )
                return await self._get_table_schema(database_type, connection_string, table_name)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Database operation failed: {str(e)}"
            )
    
    async def _connect_database(self, database_type: str, connection_string: str) -> dict[str, Any]:
        """Connect to database."""
        try:
            # For SQLite, create connection
            if database_type == "sqlite":
                if not connection_string.startswith("sqlite:///"):
                    connection_string = f"sqlite:///{connection_string}"
                
                conn = sqlite3.connect(connection_string.replace("sqlite:///", ""))
                self._connections[connection_string] = conn
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "connect",
                        "database_type": database_type,
                        "connection_string": connection_string,
                        "status": "connected"
                    }
                )
            else:
                return self._format_result(
                    success=False,
                    error=f"Database type {database_type} not yet supported"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to connect: {str(e)}"
            )
    
    async def _execute_query(self, database_type: str, connection_string: str, query: str) -> dict[str, Any]:
        """Execute SQL query."""
        try:
            if database_type == "sqlite":
                if connection_string not in self._connections:
                    await self._connect_database(database_type, connection_string)
                
                conn = self._connections[connection_string]
                cursor = conn.cursor()
                
                cursor.execute(query)
                
                if query.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    results = []
                    for row in rows:
                        result = dict(zip(columns, row))
                        results.append(result)
                    
                    return self._format_result(
                        success=True,
                        result={
                            "action": "query",
                            "query": query,
                            "results": results,
                            "row_count": len(results)
                        }
                    )
                else:
                    conn.commit()
                    return self._format_result(
                        success=True,
                        result={
                            "action": "query",
                            "query": query,
                            "rows_affected": cursor.rowcount
                        }
                    )
            else:
                return self._format_result(
                    success=False,
                    error=f"Database type {database_type} not yet supported"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Query execution failed: {str(e)}"
            )
    
    async def _list_tables(self, database_type: str, connection_string: str) -> dict[str, Any]:
        """List database tables."""
        try:
            if database_type == "sqlite":
                if connection_string not in self._connections:
                    await self._connect_database(database_type, connection_string)
                
                conn = self._connections[connection_string]
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "list_tables",
                        "tables": tables,
                        "count": len(tables)
                    }
                )
            else:
                return self._format_result(
                    success=False,
                    error=f"Database type {database_type} not yet supported"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to list tables: {str(e)}"
            )
    
    async def _get_table_schema(self, database_type: str, connection_string: str, table_name: str) -> dict[str, Any]:
        """Get table schema."""
        try:
            if database_type == "sqlite":
                if connection_string not in self._connections:
                    await self._connect_database(database_type, connection_string)
                
                conn = self._connections[connection_string]
                cursor = conn.cursor()
                
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                schema = []
                for col in columns:
                    schema.append({
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "primary_key": bool(col[5])
                    })
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "schema",
                        "table_name": table_name,
                        "schema": schema
                    }
                )
            else:
                return self._format_result(
                    success=False,
                    error=f"Database type {database_type} not yet supported"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to get schema: {str(e)}"
            )
    
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()


class CSVProcessorTool(AsyncToolInterface):
    """CSV processing and analysis tool."""
    
    def __init__(self, backend: Any | None = None):
        """Initialize the CSV processor tool.
        
        Args:
            backend: Optional backend for compatibility
        """
        super().__init__()
        self.backend = backend
        self.name = "csv_processor"
        self.description = "CSV file processing and analysis"
        
        self._schema = CSV_PROCESSOR_SCHEMA
    
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute CSV operation.
        
        Args:
            action: Action to perform
            file_path: CSV file path
            data: Data to write
            delimiter: CSV delimiter
            encoding: File encoding
            headers: Whether CSV has headers
            
        Returns:
            Dictionary with operation result
        """
        try:
            action = kwargs["action"]
            file_path = kwargs.get("file_path")
            data = kwargs.get("data", [])
            delimiter = kwargs.get("delimiter", ",")
            encoding = kwargs.get("encoding", "utf-8")
            headers = kwargs.get("headers", True)
            
            if action == "read":
                if not file_path:
                    return self._format_result(
                        success=False,
                        error="File path required for read action"
                    )
                return await self._read_csv(file_path, delimiter, encoding, headers)
            elif action == "write":
                if not file_path or not data:
                    return self._format_result(
                        success=False,
                        error="File path and data required for write action"
                    )
                return await self._write_csv(file_path, data, delimiter, encoding, headers)
            elif action == "info":
                if not file_path:
                    return self._format_result(
                        success=False,
                        error="File path required for info action"
                    )
                return await self._get_csv_info(file_path, delimiter, encoding)
            elif action == "analyze":
                if not file_path:
                    return self._format_result(
                        success=False,
                        error="File path required for analyze action"
                    )
                return await self._analyze_csv(file_path, delimiter, encoding, headers)
            else:
                return self._format_result(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"CSV operation failed: {str(e)}"
            )
    
    async def _read_csv(self, file_path: str, delimiter: str, encoding: str, headers: bool) -> dict[str, Any]:
        """Read CSV file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return self._format_result(
                    success=False,
                    error=f"File not found: {file_path}"
                )
            
            if PANDAS_AVAILABLE:
                df = pd.read_csv(path, delimiter=delimiter, encoding=encoding, header=0 if headers else None)
                
                # Convert to list of dictionaries
                if headers:
                    data = df.to_dict('records')
                else:
                    data = df.values.tolist()
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "read",
                        "file_path": str(path.absolute()),
                        "data": data,
                        "rows": len(df),
                        "columns": list(df.columns) if headers else None
                    }
                )
            else:
                # Fallback to csv module
                with open(path, encoding=encoding, newline='') as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    
                    if headers:
                        headers_row = next(reader)
                        data = []
                        for row in reader:
                            row_dict = dict(zip(headers_row, row))
                            data.append(row_dict)
                    else:
                        data = list(reader)
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "read",
                        "file_path": str(path.absolute()),
                        "data": data,
                        "rows": len(data),
                        "columns": headers_row if headers else None
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to read CSV: {str(e)}"
            )
    
    async def _write_csv(self, file_path: str, data: list[dict], delimiter: str, encoding: str, headers: bool) -> dict[str, Any]:
        """Write CSV file."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if not data:
                return self._format_result(
                    success=False,
                    error="No data provided for writing"
                )
            
            if PANDAS_AVAILABLE:
                df = pd.DataFrame(data)
                df.to_csv(path, sep=delimiter, encoding=encoding, index=False, header=headers)
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "write",
                        "file_path": str(path.absolute()),
                        "rows": len(df),
                        "columns": list(df.columns)
                    }
                )
            else:
                # Fallback to csv module
                with open(path, 'w', encoding=encoding, newline='') as f:
                    writer = csv.writer(f, delimiter=delimiter)
                    
                    if headers and data:
                        writer.writerow(data[0].keys())
                    
                    for row in data:
                        if isinstance(row, dict):
                            writer.writerow(row.values())
                        else:
                            writer.writerow(row)
                
                return self._format_result(
                    success=True,
                    result={
                        "action": "write",
                        "file_path": str(path.absolute()),
                        "rows": len(data),
                        "columns": list(data[0].keys()) if data and isinstance(data[0], dict) else None
                    }
                )
                
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to write CSV: {str(e)}"
            )
    
    async def _get_csv_info(self, file_path: str, delimiter: str, encoding: str) -> dict[str, Any]:
        """Get CSV file information."""
        try:
            path = Path(file_path)
            if not path.exists():
                return self._format_result(
                    success=False,
                    error=f"File not found: {file_path}"
                )
            
            stat = path.stat()
            
            # Quick row count
            with open(path, encoding=encoding) as f:
                line_count = sum(1 for _ in f)
            
            # Get column count from first line
            with open(path, encoding=encoding) as f:
                first_line = f.readline().strip()
                column_count = len(first_line.split(delimiter))
            
            return self._format_result(
                success=True,
                result={
                    "action": "info",
                    "file_path": str(path.absolute()),
                    "size_bytes": stat.st_size,
                    "lines": line_count,
                    "columns": column_count,
                    "delimiter": delimiter,
                    "encoding": encoding,
                    "modified_at": stat.st_mtime
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to get CSV info: {str(e)}"
            )
    
    async def _analyze_csv(self, file_path: str, delimiter: str, encoding: str, headers: bool) -> dict[str, Any]:
        """Analyze CSV file."""
        try:
            # Get basic info first
            info_result = await self._get_csv_info(file_path, delimiter, encoding)
            if not info_result["success"]:
                return info_result
            
            info = info_result["result"]
            
            analysis = {
                "file_info": info,
                "data_types": {},
                "null_counts": {},
                "unique_counts": {}
            }
            
            if PANDAS_AVAILABLE and info["lines"] > 1:
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, nrows=1000)  # Sample for analysis
                
                # Data types
                for col in df.columns:
                    analysis["data_types"][col] = str(df[col].dtype)
                    analysis["null_counts"][col] = df[col].isnull().sum()
                    analysis["unique_counts"][col] = df[col].nunique()
            
            return self._format_result(
                success=True,
                result={
                    "action": "analyze",
                    "analysis": analysis
                }
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                error=f"Failed to analyze CSV: {str(e)}"
            )
    
    def get_schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return self._schema.dict()
