"""Data interfaces for MindFlow backend.

Provides interfaces for data operations, database access,
and analytics tools.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

from pydantic import BaseModel


class DatabaseInterface(ABC):
    """Interface for database operations."""
    
    @abstractmethod
    async def connect(self, connection_string: str) -> bool:
        """Connect to database.
        
        Args:
            connection_string: Database connection string
            
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute database query.
        
        Args:
            query: SQL query
            parameters: Query parameters
            
        Returns:
            Query results
        """
        pass
    
    @abstractmethod
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table information.
        
        Args:
            table_name: Table name
            
        Returns:
            Table information
        """
        pass
    
    @abstractmethod
    async def list_tables(self) -> List[str]:
        """List all tables.
        
        Returns:
            List of table names
        """
        pass


class CSVInterface(ABC):
    """Interface for CSV file operations."""
    
    @abstractmethod
    async def read_csv(
        self,
        file_path: str,
        delimiter: str = ",",
        has_header: bool = True,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Read CSV file.
        
        Args:
            file_path: Path to CSV file
            delimiter: Field delimiter
            has_header: File has header row
            encoding: File encoding
            
        Returns:
            CSV data and metadata
        """
        pass
    
    @abstractmethod
    async def write_csv(
        self,
        data: List[Dict[str, Any]],
        file_path: str,
        delimiter: str = ",",
        include_header: bool = True,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Write data to CSV file.
        
        Args:
            data: Data to write
            file_path: Output file path
            delimiter: Field delimiter
            include_header: Include header row
            encoding: File encoding
            
        Returns:
            Write operation result
        """
        pass
    
    @abstractmethod
    async def analyze_csv(
        self,
        file_path: str,
        sample_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Analyze CSV file structure and content.
        
        Args:
            file_path: Path to CSV file
            sample_size: Number of rows to sample
            
        Returns:
            Analysis results
        """
        pass


class JSONInterface(ABC):
    """Interface for JSON file operations."""
    
    @abstractmethod
    async def read_json(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read JSON file.
        
        Args:
            file_path: Path to JSON file
            encoding: File encoding
            
        Returns:
            JSON data
        """
        pass
    
    @abstractmethod
    async def write_json(
        self,
        data: Dict[str, Any],
        file_path: str,
        indent: Optional[int] = 2,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Write data to JSON file.
        
        Args:
            data: Data to write
            file_path: Output file path
            indent: JSON indentation
            encoding: File encoding
            
        Returns:
            Write operation result
        """
        pass
    
    @abstractmethod
    async def validate_json(
        self,
        data: Union[str, Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate JSON data.
        
        Args:
            data: JSON data or file path
            schema: JSON schema for validation
            
        Returns:
            Validation results
        """
        pass


class AnalyticsInterface(ABC):
    """Interface for data analytics operations."""
    
    @abstractmethod
    async def calculate_statistics(
        self,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calculate descriptive statistics.
        
        Args:
            data: Data to analyze
            columns: Columns to analyze
            
        Returns:
            Statistics results
        """
        pass
    
    @abstractmethod
    async def create_visualization(
        self,
        data: List[Dict[str, Any]],
        chart_type: str,
        x_column: str,
        y_column: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create data visualization.
        
        Args:
            data: Data to visualize
            chart_type: Type of chart
            x_column: X-axis column
            y_column: Y-axis column
            options: Visualization options
            
        Returns:
            Visualization data
        """
        pass
    
    @abstractmethod
    async def detect_anomalies(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        method: str = "statistical"
    ) -> Dict[str, Any]:
        """Detect anomalies in data.
        
        Args:
            data: Data to analyze
            columns: Columns to check
            method: Detection method
            
        Returns:
            Anomaly detection results
        """
        pass


# Schema classes for data interfaces
class DatabaseConfig(BaseModel):
    """Database configuration schema."""
    
    connection_string: str
    database_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database_name: Optional[str] = None


class QueryResult(BaseModel):
    """Database query result schema."""
    
    success: bool
    rows_affected: int
    data: List[Dict[str, Any]]
    columns: List[str]
    execution_time_ms: int
    error: Optional[str] = None


class CSVInfo(BaseModel):
    """CSV file information schema."""
    
    file_path: str
    delimiter: str
    has_header: bool
    encoding: str
    row_count: int
    column_count: int
    columns: List[str]
    data_types: Dict[str, str]
    sample_data: List[Dict[str, Any]]


class JSONInfo(BaseModel):
    """JSON file information schema."""
    
    file_path: str
    encoding: str
    size_bytes: int
    structure_type: str  # object, array, etc.
    keys: List[str]
    depth: int
    is_valid: bool


class StatisticsResult(BaseModel):
    """Statistics result schema."""
    
    column: str
    data_type: str
    count: int
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[Union[int, float, str]] = None
    max_value: Optional[Union[int, float, str]] = None
    null_count: int
    unique_values: int


class VisualizationConfig(BaseModel):
    """Visualization configuration schema."""
    
    chart_type: str
    title: Optional[str] = None
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    width: int = 800
    height: int = 600
    color_scheme: str = "default"
    show_legend: bool = True
    interactive: bool = False


# Abstract base classes for implementation
class BaseDatabase(DatabaseInterface):
    """Base implementation of DatabaseInterface."""
    
    def __init__(self):
        self._connection = None
        self._connection_string = None
        self._is_connected = False
    
    async def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected
    
    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._close_connection()
            self._connection = None
            self._is_connected = False
    
    async def _close_connection(self) -> None:
        """Close the actual connection (implementation-specific)."""
        pass


class BaseCSV(CSVInterface):
    """Base implementation of CSVInterface."""
    
    def __init__(self):
        self._encoding_cache = {}
        self._delimiter_cache = {}
    
    async def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding."""
        # Implementation would use chardet or similar
        return "utf-8"
    
    async def _detect_delimiter(self, file_path: str) -> str:
        """Detect CSV delimiter."""
        # Implementation would analyze the file
        return ","


class BaseJSON(JSONInterface):
    """Base implementation of JSONInterface."""
    
    def __init__(self):
        self._schema_cache = {}
    
    async def _infer_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Infer JSON schema from data."""
        # Implementation would analyze the data structure
        return {}


class BaseAnalytics(AnalyticsInterface):
    """Base implementation of AnalyticsInterface."""
    
    def __init__(self):
        self._method_cache = {}
    
    async def _validate_data(
        self,
        data: List[Dict[str, Any]],
        columns: List[str]
    ) -> bool:
        """Validate data for analysis."""
        # Implementation would check data integrity
        return True
    
    async def _preprocess_data(
        self,
        data: List[Dict[str, Any]],
        columns: List[str]
    ) -> List[Dict[str, Any]]:
        """Preprocess data for analysis."""
        # Implementation would clean and prepare data
        return data
