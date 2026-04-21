# Correções para os validators Pydantic V2

# Database validator
@field_validator("database", mode="before", check_fields=False)
def assemble_database_config(cls, v: DatabaseConfig | dict | None, info: pydantic.ValidationInfo) -> DatabaseConfig:
    """Assemble database configuration from environment variables."""
    if isinstance(v, DatabaseConfig):
        return v
        
    # Extract database URL from main settings for backward compatibility
    database_url = info.data.get("default", {}).get("database_url")
    if database_url:
        if v is None:
            v = {}
        v["url"] = database_url
        
    return DatabaseConfig(**(v or {}))

# Cache validator  
@field_validator("cache", mode="before", check_fields=False)
def assemble_cache_config(cls, v: CacheConfig | dict | None, info: pydantic.ValidationInfo) -> CacheConfig:
    """Assemble cache configuration from environment variables."""
    if isinstance(v, CacheConfig):
        return v
        
    # Extract Redis configuration from main settings for backward compatibility
    redis_url = info.data.get("default", {}).get("redis_url")
    if redis_url:
        if v is None:
            v = {}
        v["redis_url"] = redis_url
        
    return CacheConfig(**(v or {}))

# Monitoring validator
@field_validator("monitoring", mode="before", check_fields=False)
def assemble_monitoring_config(cls, v: MonitoringConfig | dict | None, info: pydantic.ValidationInfo) -> MonitoringConfig:
    """Assemble monitoring configuration from environment variables."""
    if isinstance(v, MonitoringConfig):
        return v
        
    # Extract monitoring configuration from main settings for backward compatibility
    monitoring_config = info.data.get("default", {}).get("monitoring", {})
    if monitoring_config:
        if v is None:
            v = {}
        v.update(monitoring_config)
        
    return MonitoringConfig(**(v or {}))
