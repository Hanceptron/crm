"""
Configuration management for the Aviation Workflow System.

Loads environment variables and provides centralized configuration access
using Pydantic BaseSettings for type validation and documentation.
"""

import os
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for automatic type validation and conversion.
    All settings have sensible defaults for development.
    """
    
    # Core Configuration
    app_name: str = Field(
        default="Aviation Workflow System",
        env="APP_NAME",
        description="Application name"
    )
    app_env: str = Field(
        default="development",
        env="APP_ENV", 
        description="Environment: development/staging/production"
    )
    debug: bool = Field(
        default=True,
        env="DEBUG",
        description="Enable debug mode"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./workflow.db",
        env="DATABASE_URL",
        description="Database connection URL"
    )
    
    # Redis Configuration (Optional)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL"
    )
    use_redis: bool = Field(
        default=False,
        env="USE_REDIS",
        description="Enable Redis for caching and queues"
    )
    
    # Burr Workflow Engine Configuration
    burr_tracker_type: str = Field(
        default="local",
        env="BURR_TRACKER_TYPE",
        description="Burr state tracker type: local/api"
    )
    burr_state_dir: str = Field(
        default="./burr_state",
        env="BURR_STATE_DIR",
        description="Directory for Burr state persistence"
    )
    
    # Module Configuration
    enabled_modules: str = Field(
        default="departments,approvals,comments,templates",
        env="ENABLED_MODULES",
        description="Comma-separated list of enabled modules"
    )
    module_auto_load: bool = Field(
        default=True,
        env="MODULE_AUTO_LOAD",
        description="Automatically load enabled modules on startup"
    )
    
    # API Configuration
    api_prefix: str = Field(
        default="/api",
        env="API_PREFIX",
        description="API route prefix"
    )
    api_version: str = Field(
        default="v1",
        env="API_VERSION",
        description="API version"
    )
    cors_origins: str = Field(
        default="http://localhost:8501",
        env="CORS_ORIGINS",
        description="CORS allowed origins (comma-separated)"
    )
    
    # Streamlit Configuration
    streamlit_server_port: int = Field(
        default=8501,
        env="STREAMLIT_SERVER_PORT",
        description="Streamlit server port"
    )
    streamlit_server_address: str = Field(
        default="localhost",
        env="STREAMLIT_SERVER_ADDRESS",
        description="Streamlit server bind address"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def enabled_modules_list(self) -> List[str]:
        """Get enabled modules as a list."""
        return [module.strip() for module in self.enabled_modules.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() == "production"
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")
    
    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.database_url.startswith("postgresql")


# Global settings instance
settings = Settings()