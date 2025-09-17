"""
Plugin management system for the Aviation Workflow System.

Provides dynamic loading and unloading of modules based on configuration.
Each module must follow the standard ModuleInterface to be pluggable.
"""

import importlib
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Type
from fastapi import APIRouter, FastAPI
from sqlmodel import SQLModel
from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModuleConfig:
    """Configuration for a pluggable module."""
    
    name: str
    enabled: bool = True
    routes_path: Optional[str] = None
    models_path: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set default paths based on module name if not provided."""
        if self.routes_path is None:
            self.routes_path = f"modules.{self.name}.routes"
        if self.models_path is None:
            self.models_path = f"modules.{self.name}.models"


class ModuleInterface:
    """
    Standard interface that all modules must implement.
    
    Defines the contract for pluggable modules including required
    attributes and optional lifecycle methods.
    """
    
    # Required attributes
    name: str = "unknown_module"
    version: str = "1.0.0"
    description: str = "Module description"
    
    # Optional components
    router: Optional[APIRouter] = None
    models: Optional[List[Type[SQLModel]]] = None
    dependencies: Optional[List[str]] = None
    
    def on_load(self) -> None:
        """Called when module is loaded."""
        pass
    
    def on_unload(self) -> None:
        """Called when module is unloaded."""
        pass
    
    def validate_config(self, config: dict) -> bool:
        """
        Validate module configuration.
        
        Args:
            config: Module configuration dictionary
            
        Returns:
            True if configuration is valid, False otherwise
        """
        return True


class PluginManager:
    """
    Dynamically loads/unloads modules based on configuration.
    
    Manages the lifecycle of pluggable modules, handles dependencies,
    and provides integration with FastAPI routing and SQLModel migrations.
    """
    
    def __init__(self):
        """Initialize the plugin manager."""
        self._loaded_modules: Dict[str, ModuleInterface] = {}
        self._module_configs: Dict[str, ModuleConfig] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
    
    def load_module(self, module_name: str) -> Optional[ModuleInterface]:
        """
        Dynamically import and register a module.
        
        Args:
            module_name: Name of the module to load (e.g., 'departments')
            
        Returns:
            Loaded module interface or None if loading failed
        """
        if module_name in self._loaded_modules:
            logger.warning(f"Module {module_name} is already loaded")
            return self._loaded_modules[module_name]
        
        try:
            # Create module configuration
            config = ModuleConfig(name=module_name)
            self._module_configs[module_name] = config
            
            # Import the module's __init__.py
            module_path = f"modules.{module_name}"
            module = importlib.import_module(module_path)
            
            # Look for ModuleInterface implementation
            module_interface = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, ModuleInterface) and 
                    attr is not ModuleInterface):
                    module_interface = attr()
                    break
            
            # Fallback: create interface from module attributes
            if module_interface is None:
                module_interface = ModuleInterface()
                module_interface.name = module_name
                
                # Try to get router
                if hasattr(module, 'router'):
                    module_interface.router = getattr(module, 'router')
                
                # Try to get models
                if hasattr(module, 'models'):
                    module_interface.models = getattr(module, 'models')
                elif hasattr(module, '__models__'):
                    module_interface.models = getattr(module, '__models__')
            
            # Validate configuration
            if not module_interface.validate_config({}):
                logger.error(f"Module {module_name} failed configuration validation")
                return None
            
            # Check dependencies
            if module_interface.dependencies:
                missing_deps = self._check_dependencies(module_interface.dependencies)
                if missing_deps:
                    logger.error(f"Module {module_name} missing dependencies: {missing_deps}")
                    return None
            
            # Store in dependency graph
            self._dependency_graph[module_name] = module_interface.dependencies or []
            
            # Load the module
            self._loaded_modules[module_name] = module_interface
            
            # Call lifecycle method
            try:
                module_interface.on_load()
            except Exception as e:
                logger.error(f"Error calling on_load for module {module_name}: {e}")
                # Continue loading despite lifecycle error
            
            logger.info(f"Successfully loaded module: {module_name}")
            return module_interface
            
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading module {module_name}: {e}")
            return None
    
    def unload_module(self, module_name: str) -> bool:
        """
        Unload a module and clean up resources.
        
        Args:
            module_name: Name of the module to unload
            
        Returns:
            True if successfully unloaded, False otherwise
        """
        if module_name not in self._loaded_modules:
            logger.warning(f"Module {module_name} is not loaded")
            return False
        
        try:
            module_interface = self._loaded_modules[module_name]
            
            # Call lifecycle method
            try:
                module_interface.on_unload()
            except Exception as e:
                logger.error(f"Error calling on_unload for module {module_name}: {e}")
            
            # Remove from tracking
            del self._loaded_modules[module_name]
            if module_name in self._module_configs:
                del self._module_configs[module_name]
            if module_name in self._dependency_graph:
                del self._dependency_graph[module_name]
            
            logger.info(f"Successfully unloaded module: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading module {module_name}: {e}")
            return False
    
    def register_routes(self, app: FastAPI) -> None:
        """
        Register all enabled module routes with FastAPI.
        
        Args:
            app: FastAPI application instance
        """
        for module_name, module_interface in self._loaded_modules.items():
            if module_interface.router:
                try:
                    # Routers already define their own prefixes (e.g., 
                    # "/api/departments"). Avoid duplicating the API prefix.
                    app.include_router(module_interface.router)
                    logger.info(f"Registered routes for module: {module_name}")
                except Exception as e:
                    logger.error(f"Error registering routes for module {module_name}: {e}")
    
    def get_models(self) -> List[Type[SQLModel]]:
        """
        Collect all SQLModel models from loaded modules for migration.
        
        Returns:
            List of SQLModel classes from all loaded modules
        """
        all_models = []
        
        for module_name, module_interface in self._loaded_modules.items():
            if module_interface.models:
                try:
                    all_models.extend(module_interface.models)
                    logger.debug(f"Collected {len(module_interface.models)} models from {module_name}")
                except Exception as e:
                    logger.error(f"Error collecting models from module {module_name}: {e}")
        
        return all_models
    
    def load_enabled_modules(self) -> None:
        """Load all modules specified in settings.enabled_modules."""
        for module_name in settings.enabled_modules_list:
            if module_name.strip():
                self.load_module(module_name.strip())
    
    def get_loaded_modules(self) -> Dict[str, ModuleInterface]:
        """Get dictionary of all loaded modules."""
        return self._loaded_modules.copy()
    
    def is_module_loaded(self, module_name: str) -> bool:
        """Check if a module is currently loaded."""
        return module_name in self._loaded_modules
    
    def get_module_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all loaded modules.
        
        Returns:
            Dictionary containing status info for each loaded module
        """
        status = {}
        for module_name, module_interface in self._loaded_modules.items():
            status[module_name] = {
                "name": module_interface.name,
                "version": module_interface.version,
                "description": module_interface.description,
                "has_router": module_interface.router is not None,
                "model_count": len(module_interface.models) if module_interface.models else 0,
                "dependencies": module_interface.dependencies or []
            }
        return status
    
    def _check_dependencies(self, dependencies: List[str]) -> List[str]:
        """
        Check if all dependencies are loaded.
        
        Args:
            dependencies: List of required module names
            
        Returns:
            List of missing dependencies
        """
        missing = []
        for dep in dependencies:
            if not self.is_module_loaded(dep):
                missing.append(dep)
        return missing
    
    def reload_module(self, module_name: str) -> bool:
        """
        Reload a module (unload then load).
        
        Args:
            module_name: Name of the module to reload
            
        Returns:
            True if successfully reloaded, False otherwise
        """
        if self.is_module_loaded(module_name):
            if not self.unload_module(module_name):
                return False
        
        return self.load_module(module_name) is not None


# Global plugin manager instance
plugin_manager = PluginManager()
