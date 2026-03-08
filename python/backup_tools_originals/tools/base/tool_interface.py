"""
Abstract base interface 
for all MindFlow tools. DEPRECATED: This module has been moved to mindflow_backend.interfaces.tools.base This file is maintained 
for backward compatibility during migration. Use: 
from mindflow_backend.interfaces.tools 
import ToolInterface, AsyncToolInterface, StatefulToolInterface, ToolSchema, ToolPermission 
"""
 
# Forward compatibility aliases - 
import 
from new location 
from mindflow_backend.interfaces.tools.base 
import ( ToolInterface, AsyncToolInterface, StatefulToolInterface, ToolSchema, ToolPermission, ) 
# Maintain backward compatibility __all__ = [ "ToolInterface", "AsyncToolInterface", "StatefulToolInterface", "ToolSchema", "ToolPermission", ]