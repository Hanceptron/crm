# Aviation Workflow System

A modular workflow management system designed for aviation companies to handle work items flowing through departments with configurable approval sequences. Built with FastAPI, SQLModel, Burr workflow engine, and Streamlit UI.

## 🚀 Features

- **Modular Architecture**: Every feature is a plugin that can be enabled/disabled
- **Department-Based Workflows**: Configurable approval sequences across departments
- **Template System**: Reusable workflow templates for common processes
- **Real-time Dashboard**: Streamlit-based UI with live updates
- **State Management**: Burr-powered workflow engine for robust state transitions
- **Aviation-Specific**: Tailored for aviation maintenance, safety, and operations workflows

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Architecture Overview](#architecture-overview)
- [Module Development](#module-development)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Contributing](#contributing)

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- SQLite (development) or PostgreSQL (production)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd aviation-workflow

# Using Poetry (recommended)
poetry install
poetry shell

# Or using pip
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional for development)
nano .env
```

### 3. Initialize Database

```bash
# Create database tables
python scripts/init_db.py

# Seed with sample data
python scripts/seed_data.py
```

### 4. Start Development Servers

```bash
# Start both FastAPI and Streamlit
python scripts/run_dev.py
```

### 5. Access the Application

- **Streamlit Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 🛠️ Installation

### Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd aviation-workflow
   ```

2. **Install Dependencies**
   ```bash
   # Using Poetry (recommended)
   poetry install
   poetry shell
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   ```bash
   cp .env.example .env
   ```
   
   Key environment variables:
   ```bash
   # Database
   DATABASE_URL="sqlite:///./workflow.db"
   
   # Modules
   ENABLED_MODULES="departments,templates,comments,approvals"
   
   # API
   API_PREFIX="/api"
   CORS_ORIGINS="http://localhost:8501"
   ```

4. **Database Setup**
   ```bash
   # Initialize database
   python scripts/init_db.py
   
   # Add sample data
   python scripts/seed_data.py
   ```

### Production Setup

1. **Database Configuration**
   ```bash
   DATABASE_URL="postgresql://user:password@localhost:5432/aviation_workflow"
   ```

2. **Environment Variables**
   ```bash
   APP_ENV="production"
   DEBUG=false
   ```

3. **Run with Production Server**
   ```bash
   # API Server
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   
   # Streamlit Dashboard
   streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
   ```

## 🏗️ Architecture Overview

### Core Philosophy

> **Every feature is a plugin.** The core system only handles workflow state transitions. Everything else (departments, notifications, reports) is a removable module.

### System Components

```
aviation-workflow/
├── core/                    # Core system (minimal, never changes)
│   ├── config.py           # Configuration management
│   ├── database.py         # Database connection
│   ├── models.py           # Core WorkItem model only
│   ├── workflow_engine.py  # Burr integration
│   └── plugin_manager.py   # Module loading system
│
├── api/                     # FastAPI application
│   ├── main.py             # App initialization
│   ├── dependencies.py     # Dependency injection
│   └── middleware.py       # CORS, logging, etc.
│
├── modules/                 # Pluggable modules
│   ├── departments/        # Department management
│   ├── templates/          # Workflow templates
│   ├── comments/           # Comments and notes
│   ├── approvals/          # Approval workflows
│   └── reports/            # Analytics (future)
│
├── workflows/              # Burr workflow definitions
│   ├── base_workflow.py    # Abstract base
│   ├── sequential_approval.py
│   └── configs/           # YAML configurations
│
├── ui/                     # Streamlit interface
│   ├── app.py             # Main application
│   ├── pages/             # Multi-page interface
│   └── components/        # Reusable UI components
│
└── scripts/               # Utility scripts
    ├── init_db.py         # Database initialization
    ├── seed_data.py       # Sample data creation
    └── run_dev.py         # Development server
```

### Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: SQLModel (SQLite/PostgreSQL)
- **Workflow Engine**: Burr (state machine)
- **Frontend**: Streamlit
- **Package Management**: Poetry
- **Testing**: pytest
- **Code Quality**: black, ruff, mypy

### Data Flow

1. **Work Item Creation**: Items created via UI or API
2. **Template Selection**: Choose predefined workflow or custom sequence
3. **Department Flow**: Items move through departments based on configuration
4. **Approval Process**: Each department can approve, reject, or request information
5. **State Management**: Burr tracks workflow state and transitions
6. **Completion**: Items reach final approved/rejected/completed state

## 🔧 Module Development

### Module Interface

All modules must implement the `ModuleInterface`:

```python
from core.plugin_manager import ModuleInterface

class MyModule(ModuleInterface):
    name: str = "my_module"
    version: str = "1.0.0"
    description: str = "Module description"
    
    # Optional components
    router: Optional[APIRouter] = None
    models: Optional[List[SQLModel]] = None
    dependencies: Optional[List[str]] = None
    
    def on_load(self) -> bool:
        """Called when module is loaded"""
        return True
    
    def on_unload(self) -> bool:
        """Called when module is unloaded"""
        return True
    
    def validate_config(self, config: Dict) -> bool:
        """Validate module configuration"""
        return True
```

### Creating a New Module

1. **Create Module Directory**
   ```bash
   mkdir modules/my_module
   touch modules/my_module/__init__.py
   ```

2. **Implement Required Files**
   ```
   modules/my_module/
   ├── __init__.py          # Module interface
   ├── models.py            # SQLModel definitions
   ├── routes.py            # FastAPI routes
   ├── service.py           # Business logic
   └── schemas.py           # Pydantic schemas
   ```

3. **Module Interface (`__init__.py`)**
   ```python
   from .models import MyModel
   from .routes import router
   from core.plugin_manager import ModuleInterface
   
   class MyModuleInterface(ModuleInterface):
       name = "my_module"
       version = "1.0.0"
       description = "My custom module"
       router = router
       models = [MyModel]
   
   module_interface = MyModuleInterface()
   ```

4. **Enable Module**
   ```bash
   # Add to .env
   ENABLED_MODULES="departments,templates,my_module"
   ```

### Module Best Practices

- **Independence**: Modules should not depend on each other
- **Configuration**: Use `config.yaml` for module settings
- **Database**: Define models with proper relationships
- **API**: Follow RESTful conventions
- **Testing**: Include comprehensive tests
- **Documentation**: Document all endpoints and models

## 📚 API Documentation

### Core Endpoints

- `GET /health` - System health check
- `GET /api/work-items` - List work items
- `POST /api/work-items` - Create work item
- `GET /api/work-items/{id}` - Get work item details
- `PUT /api/work-items/{id}` - Update work item

### Module Endpoints

Each enabled module provides its own endpoints:

- **Departments**: `/api/departments/*`
- **Templates**: `/api/templates/*`
- **Comments**: `/api/comments/*`
- **Approvals**: `/api/approvals/*`

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication

Currently using mock authentication for development. In production:

```python
# Enable in config.yaml
features:
  enable_auth: true

# Or environment variable
ENABLE_AUTH=true
```

## 🚢 Deployment

### Docker Deployment

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Deployment

1. **Production Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup**
   ```bash
   # PostgreSQL recommended for production
   DATABASE_URL="postgresql://user:pass@localhost/aviation_workflow"
   python scripts/init_db.py
   ```

3. **Start Services**
   ```bash
   # API Server
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
   
   # Dashboard
   streamlit run ui/app.py --server.port 8501
   ```

4. **Reverse Proxy (Nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location /api/ {
           proxy_pass http://localhost:8000/api/;
       }
       
       location / {
           proxy_pass http://localhost:8501/;
       }
   }
   ```

### Environment Configuration

**Development**:
```bash
APP_ENV=development
DEBUG=true
DATABASE_URL=sqlite:///./workflow.db
```

**Production**:
```bash
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@host/db
```

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_modules/test_departments.py

# With coverage
pytest --cov=core --cov=modules
```

### Test Categories

- **Unit Tests**: Individual functions and classes
- **Integration Tests**: Module interactions
- **API Tests**: Endpoint testing
- **Workflow Tests**: State machine validation

### Writing Tests

```python
# tests/test_modules/test_my_module.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_my_module_endpoint():
    response = client.get("/api/my-module/")
    assert response.status_code == 200
```

## 🔧 Development Workflow

### Daily Development

1. **Start Development Environment**
   ```bash
   python scripts/run_dev.py
   ```

2. **Code Changes**
   - Edit modules in `modules/`
   - Update UI in `ui/`
   - Modify workflows in `workflows/`

3. **Test Changes**
   ```bash
   pytest tests/
   ```

4. **Code Quality**
   ```bash
   black .
   ruff check .
   mypy .
   ```

### Adding New Features

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Implement as Module**
   - Follow module interface
   - Add tests
   - Update documentation

3. **Integration**
   - Update `config.yaml`
   - Add to enabled modules
   - Test full workflow

### Database Changes

1. **Model Updates**
   ```python
   # Update models in modules/*/models.py
   ```

2. **Migrate Database**
   ```bash
   python scripts/init_db.py --force
   ```

3. **Re-seed Data**
   ```bash
   python scripts/seed_data.py
   ```

## 📊 Monitoring

### Health Checks

- **API Health**: `GET /health`
- **Database**: Connection status
- **Modules**: Load status
- **Workflow Engine**: State consistency

### Logging

```python
# Configured in config.yaml
logging:
  level: "INFO"
  handlers:
    - type: "console"
    - type: "file"
      filename: "logs/aviation_workflow.log"
```

### Metrics (Future)

- Work item processing times
- Department bottlenecks
- Approval rates
- System performance

## 🤝 Contributing

### Getting Started

1. **Fork Repository**
2. **Create Feature Branch**
3. **Follow Development Workflow**
4. **Submit Pull Request**

### Code Standards

- **Python**: Follow PEP 8
- **Documentation**: Docstrings for all functions
- **Testing**: Minimum 80% coverage
- **Type Hints**: Use throughout

### Module Contributions

New modules are welcome! Follow the module development guide and ensure:

- Complete module interface implementation
- Comprehensive tests
- Documentation
- Configuration options

## 📝 License

[Add your license here]

## 🆘 Support

### Troubleshooting

**Database Issues**:
```bash
# Reset database
rm workflow.db
python scripts/init_db.py
python scripts/seed_data.py
```

**Module Loading Issues**:
```bash
# Check enabled modules
python -c "from core.config import settings; print(settings.enabled_modules)"
```

**Port Conflicts**:
```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9
lsof -ti:8501 | xargs kill -9
```

### Getting Help

- **Documentation**: Check this README and inline docs
- **API Docs**: http://localhost:8000/docs
- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub discussions for questions

## 🎯 Roadmap

### Current (MVP)
- ✅ Core workflow engine
- ✅ Department management
- ✅ Template system
- ✅ Basic UI
- ✅ Comment system

### Near Term
- 🔄 User authentication
- 🔄 File attachments
- 🔄 Email notifications
- 🔄 Advanced reporting

### Future
- 📋 Mobile app
- 📋 External integrations
- 📋 Advanced analytics
- 📋 Multi-tenant support

---

**Built with ❤️ for the aviation industry**