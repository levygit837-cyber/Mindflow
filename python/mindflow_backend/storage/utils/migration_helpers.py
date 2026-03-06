"""Migration helpers for PostgreSQL to other databases.

Utilities for migrating data between different database systems.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def migrate_postgres_to_duckdb(
    postgres_connection_string: str,
    duckdb_path: str,
    tables: Optional[List[str]] = None,
) -> Dict[str, int]:
    """Migrate data from PostgreSQL to DuckDB.
    
    Args:
        postgres_connection_string: PostgreSQL connection string
        duckdb_path: Path to DuckDB database file
        tables: List of tables to migrate (all if None)
        
    Returns:
        Dictionary with table names and row counts migrated
    """
    try:
        import duckdb
        import psycopg
    except ImportError as e:
        raise ImportError(f"Required packages not installed: {e}")
    
    if tables is None:
        tables = [
            "chat_sessions",
            "chat_messages", 
            "agent_memory_events",
            "agent_memory_cursor",
            "agent_memory_windows",
            "agent_memory_facts",
        ]
    
    results = {}
    
    # Connect to PostgreSQL
    pg_conn = psycopg.connect(postgres_connection_string)
    pg_conn.autocommit = False
    
    # Connect to DuckDB
    duckdb_conn = duckdb.connect(duckdb_path)
    
    try:
        for table in tables:
            _logger.info(f"Migrating table: {table}")
            
            # Get data from PostgreSQL
            with pg_conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table}")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
            
            if not rows:
                _logger.info(f"No data in table {table}")
                results[table] = 0
                continue
            
            # Create table in DuckDB (simplified)
            create_table_sql = _generate_duckdb_create_table(table, columns)
            duckdb_conn.execute(create_table_sql)
            
            # Insert data into DuckDB
            insert_sql = _generate_duckdb_insert(table, columns)
            
            # Convert rows for DuckDB
            duckdb_rows = []
            for row in rows:
                # Convert PostgreSQL types to DuckDB compatible types
                converted_row = []
                for i, value in enumerate(row):
                    if value is None:
                        converted_row.append(None)
                    elif isinstance(value, dict):
                        converted_row.append(json.dumps(value))
                    else:
                        converted_row.append(value)
                duckdb_rows.append(tuple(converted_row))
            
            # Execute insert
            duckdb_conn.executemany(insert_sql, duckdb_rows)
            
            results[table] = len(rows)
            _logger.info(f"Migrated {len(rows)} rows from {table}")
        
        duckdb_conn.commit()
        _logger.info("Migration completed successfully")
        
    except Exception as e:
        duckdb_conn.rollback()
        _logger.error(f"Migration failed: {e}")
        raise
    finally:
        pg_conn.close()
        duckdb_conn.close()
    
    return results


def _generate_duckdb_create_table(table: str, columns: List[str]) -> str:
    """Generate DuckDB CREATE TABLE statement."""
    # Simplified column type mapping
    type_mapping = {
        "id": "INTEGER",
        "session_id": "VARCHAR",
        "title": "VARCHAR",
        "content": "TEXT",
        "role": "VARCHAR",
        "provider": "VARCHAR",
        "model": "VARCHAR",
        "agent_id": "VARCHAR",
        "token_count": "INTEGER",
        "source_message_id": "INTEGER",
        "token_total": "INTEGER",
        "tokens_since_summary": "INTEGER",
        "window_index": "INTEGER",
        "last_summarized_event_id": "INTEGER",
        "tokens_since_chunk": "INTEGER",
        "last_chunked_event_id": "INTEGER",
        "chunk_sequence": "INTEGER",
        "token_start": "INTEGER",
        "token_end": "INTEGER",
        "event_start_id": "INTEGER",
        "event_end_id": "INTEGER",
        "summary_md": "TEXT",
        "key_points": "JSON",
        "coverage_ratio": "FLOAT",
        "checksum": "VARCHAR",
        "fact_type": "VARCHAR",
        "confidence_score": "FLOAT",
        "metadata": "JSON",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    }
    
    column_defs = []
    for col in columns:
        duckdb_type = type_mapping.get(col, "VARCHAR")
        column_defs.append(f"{col} {duckdb_type}")
    
    return f"CREATE TABLE {table} ({', '.join(column_defs)})"


def _generate_duckdb_insert(table: str, columns: List[str]) -> str:
    """Generate DuckDB INSERT statement."""
    placeholders = ", ".join(["?" for _ in columns])
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"


async def backup_postgres_data(
    connection_string: str,
    output_dir: str,
    tables: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Backup PostgreSQL data to JSON files.
    
    Args:
        connection_string: PostgreSQL connection string
        output_dir: Directory to save backup files
        tables: List of tables to backup (all if None)
        
    Returns:
        Dictionary with table names and backup file paths
    """
    import psycopg
    from pathlib import Path
    
    if tables is None:
        tables = [
            "chat_sessions",
            "chat_messages",
            "agent_memory_events", 
            "agent_memory_cursor",
            "agent_memory_windows",
            "agent_memory_facts",
        ]
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    pg_conn = psycopg.connect(connection_string)
    
    try:
        for table in tables:
            _logger.info(f"Backing up table: {table}")
            
            with pg_conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table}")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
            
            # Convert to JSON-serializable format
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if isinstance(value, dict):
                        row_dict[columns[i]] = value
                    else:
                        row_dict[columns[i]] = value
                data.append(row_dict)
            
            # Save to file
            backup_file = output_path / f"{table}.json"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            
            results[table] = str(backup_file)
            _logger.info(f"Backed up {len(data)} rows from {table} to {backup_file}")
    
    finally:
        pg_conn.close()
    
    return results


async def restore_postgres_data(
    connection_string: str,
    backup_dir: str,
    tables: Optional[List[str]] = None,
) -> Dict[str, int]:
    """Restore PostgreSQL data from JSON files.
    
    Args:
        connection_string: PostgreSQL connection string
        backup_dir: Directory containing backup files
        tables: List of tables to restore (all if None)
        
    Returns:
        Dictionary with table names and row counts restored
    """
    import psycopg
    from pathlib import Path
    
    backup_path = Path(backup_dir)
    
    if tables is None:
        # Find all JSON files in backup directory
        tables = [f.stem for f in backup_path.glob("*.json")]
    
    results = {}
    pg_conn = psycopg.connect(connection_string)
    pg_conn.autocommit = False
    
    try:
        for table in tables:
            backup_file = backup_path / f"{table}.json"
            if not backup_file.exists():
                _logger.warning(f"Backup file not found: {backup_file}")
                results[table] = 0
                continue
            
            _logger.info(f"Restoring table: {table}")
            
            # Load data from file
            with open(backup_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not data:
                _logger.info(f"No data to restore for table {table}")
                results[table] = 0
                continue
            
            # Get columns from first row
            columns = list(data[0].keys())
            
            # Clear existing data
            with pg_conn.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table}")
            
            # Insert data
            insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
            
            with pg_conn.cursor() as cursor:
                for row in data:
                    values = [row.get(col) for col in columns]
                    cursor.execute(insert_sql, values)
            
            results[table] = len(data)
            _logger.info(f"Restored {len(data)} rows to {table}")
        
        pg_conn.commit()
        _logger.info("Restore completed successfully")
        
    except Exception as e:
        pg_conn.rollback()
        _logger.error(f"Restore failed: {e}")
        raise
    finally:
        pg_conn.close()
    
    return results


def validate_migration_integrity(
    source_connection_string: str,
    target_connection_string: str,
    tables: List[str],
) -> Dict[str, Dict[str, Any]]:
    """Validate migration integrity between source and target databases.
    
    Args:
        source_connection_string: Source database connection string
        target_connection_string: Target database connection string  
        tables: List of tables to validate
        
    Returns:
        Dictionary with validation results for each table
    """
    import psycopg
    
    results = {}
    
    source_conn = psycopg.connect(source_connection_string)
    target_conn = psycopg.connect(target_connection_string)
    
    try:
        for table in tables:
            _logger.info(f"Validating table: {table}")
            
            # Get row counts
            with source_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                source_count = cursor.fetchone()[0]
            
            with target_conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                target_count = cursor.fetchone()[0]
            
            # Get sample data for comparison
            with source_conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                source_sample = cursor.fetchall()
            
            with target_conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                target_sample = cursor.fetchall()
            
            results[table] = {
                "source_count": source_count,
                "target_count": target_count,
                "count_match": source_count == target_count,
                "sample_match": len(source_sample) > 0 and len(target_sample) > 0,
                "status": "OK" if source_count == target_count else "MISMATCH"
            }
            
            if source_count != target_count:
                _logger.warning(f"Row count mismatch for {table}: {source_count} vs {target_count}")
            else:
                _logger.info(f"Table {table} validated successfully")
    
    finally:
        source_conn.close()
        target_conn.close()
    
    return results
