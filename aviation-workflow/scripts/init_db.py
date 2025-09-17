#!/usr/bin/env python3
"""
Database initialization script for the Aviation Workflow System.

Creates all tables based on enabled modules and handles both SQLite and PostgreSQL.
Checks for existing tables before creating to avoid conflicts.
"""

import sys
import os
import logging
from typing import List
from sqlmodel import SQLModel, create_engine, text
from sqlalchemy import inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import DatabaseManager
from core.plugin_manager import PluginManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_database_info():
    """Get database connection information."""
    db_url = settings.database_url
    
    if db_url.startswith("sqlite"):
        db_type = "SQLite"
        db_file = db_url.replace("sqlite:///", "")
        db_info = f"SQLite database: {db_file}"
    elif db_url.startswith("postgresql"):
        db_type = "PostgreSQL"
        # Parse PostgreSQL URL for display (hide password)
        parts = db_url.replace("postgresql://", "").split("@")
        if len(parts) == 2:
            host_info = parts[1]
            db_info = f"PostgreSQL database: {host_info}"
        else:
            db_info = "PostgreSQL database"
    else:
        db_type = "Unknown"
        db_info = f"Database: {db_url}"
    
    return db_type, db_info


def check_database_connection():
    """Test database connection."""
    try:
        engine = create_engine(settings.database_url)
        
        # Test connection
        with engine.connect() as conn:
            # Use appropriate test query based on database type
            if settings.database_url.startswith("sqlite"):
                result = conn.execute(text("SELECT 1"))
            else:
                result = conn.execute(text("SELECT version()"))
            
            result.fetchone()
            logger.info("✅ Database connection successful")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_existing_tables():
    """Get list of existing tables in the database."""
    try:
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return tables
    except Exception as e:
        logger.error(f"Error getting existing tables: {e}")
        return []


def import_core_models():
    """Import core models to register them with SQLModel."""
    try:
        from core.models import WorkItem
        logger.info("📦 Core models imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to import core models: {e}")
        return False


def load_enabled_modules() -> List[str]:
    """Load enabled modules and import their models."""
    try:
        plugin_manager = PluginManager()
        
        # Get enabled modules from configuration
        enabled_modules = settings.enabled_modules.split(",")
        enabled_modules = [m.strip() for m in enabled_modules if m.strip()]
        
        logger.info(f"📋 Enabled modules: {', '.join(enabled_modules)}")
        
        loaded_modules = []
        
        for module_name in enabled_modules:
            try:
                logger.info(f"🔄 Loading module: {module_name}")
                module_interface = plugin_manager.load_module(module_name)
                
                if module_interface:
                    # Import module models to register them with SQLModel
                    if hasattr(module_interface, 'models') and module_interface.models:
                        for model_class in module_interface.models:
                            logger.info(f"📦 Registered model: {model_class.__name__}")
                    
                    loaded_modules.append(module_name)
                    logger.info(f"✅ Successfully loaded module: {module_name}")
                else:
                    logger.warning(f"⚠️  Module {module_name} returned None")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load module {module_name}: {e}")
                continue
        
        logger.info(f"✅ Loaded {len(loaded_modules)} modules: {', '.join(loaded_modules)}")
        return loaded_modules
        
    except Exception as e:
        logger.error(f"❌ Error loading modules: {e}")
        return []


def create_database_tables(force: bool = False):
    """Create database tables for all registered models."""
    try:
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # Get existing tables
        existing_tables = get_existing_tables()
        
        if existing_tables and not force:
            logger.info(f"📋 Found {len(existing_tables)} existing tables: {', '.join(existing_tables)}")
            
            # Check if we should skip creation
            response = input("\n❓ Tables already exist. Continue with table creation? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                logger.info("⏭️  Skipping table creation")
                return True
        
        logger.info("🏗️  Creating database tables...")
        
        # Create all tables
        SQLModel.metadata.create_all(engine)
        
        # Get updated table list
        new_tables = get_existing_tables()
        logger.info(f"✅ Database tables created successfully!")
        logger.info(f"📊 Total tables: {len(new_tables)}")
        
        # List all tables
        if new_tables:
            logger.info("📋 Database tables:")
            for i, table in enumerate(sorted(new_tables), 1):
                logger.info(f"   {i:2d}. {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False


def verify_table_creation():
    """Verify that tables were created successfully."""
    try:
        tables = get_existing_tables()
        
        # Check for core tables
        expected_core_tables = ['work_items']
        
        missing_core = []
        for table in expected_core_tables:
            if table not in tables:
                missing_core.append(table)
        
        if missing_core:
            logger.warning(f"⚠️  Missing core tables: {', '.join(missing_core)}")
            return False
        
        logger.info("✅ Core tables verified successfully")
        
        # Check for module tables
        module_tables = [t for t in tables if t not in expected_core_tables]
        if module_tables:
            logger.info(f"📦 Module tables found: {', '.join(sorted(module_tables))}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Table verification failed: {e}")
        return False


def show_database_info():
    """Display database information and statistics."""
    try:
        db_type, db_info = get_database_info()
        tables = get_existing_tables()
        
        print("\n" + "=" * 60)
        print("📊 DATABASE INFORMATION")
        print("=" * 60)
        print(f"Database Type: {db_type}")
        print(f"Connection: {db_info}")
        print(f"Total Tables: {len(tables)}")
        
        if tables:
            print("\nTables:")
            for i, table in enumerate(sorted(tables), 1):
                print(f"  {i:2d}. {table}")
        
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Error showing database info: {e}")


def main():
    """Main database initialization function."""
    print("🚀 Aviation Workflow System - Database Initialization")
    print("=" * 60)
    
    # Check database connection
    logger.info("🔌 Testing database connection...")
    if not check_database_connection():
        logger.error("❌ Cannot connect to database. Check your configuration.")
        return 1
    
    # Show database info
    db_type, db_info = get_database_info()
    logger.info(f"🗄️  {db_info}")
    
    # Import core models
    logger.info("📦 Importing core models...")
    if not import_core_models():
        logger.error("❌ Failed to import core models")
        return 1
    
    # Load enabled modules
    logger.info("🔌 Loading enabled modules...")
    loaded_modules = load_enabled_modules()
    
    if not loaded_modules:
        logger.warning("⚠️  No modules loaded. Only core tables will be created.")
    
    # Create database tables
    force_create = "--force" in sys.argv
    if not create_database_tables(force=force_create):
        logger.error("❌ Failed to create database tables")
        return 1
    
    # Verify table creation
    logger.info("🔍 Verifying table creation...")
    if not verify_table_creation():
        logger.warning("⚠️  Table verification failed")
        return 1
    
    # Show final database information
    show_database_info()
    
    logger.info("🎉 Database initialization completed successfully!")
    
    print("\n" + "💡 NEXT STEPS:")
    print("  1. Run 'python scripts/seed_data.py' to add sample data")
    print("  2. Run 'python scripts/run_dev.py' to start the development server")
    print("  3. Visit the API docs at http://localhost:8000/docs")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Database initialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
