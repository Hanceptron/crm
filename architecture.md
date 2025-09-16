# Aviation Workflow MVP - Modular Architecture Document

## PROJECT CONTEXT FOR LLM AGENT

You are building a modular workflow management system for an aviation company. Work items flow through departments in configurable sequences (e.g., Engineering→QC→Operations). Each department can approve (move forward) or reject (send back) items with comments. The system must handle 500-700 users and be completely modular for easy feature addition/removal.

**Core Philosophy**: Every feature is a plugin. The core system only handles workflow state transitions. Everything else (departments, notifications, reports) is a removable module.

## TECHNOLOGY STACK

```yaml
Core:
  Backend: FastAPI (Python 3.11+)
  Workflow Engine: Burr (state machine library)
  Database: SQLite (MVP) → PostgreSQL (production)
  Testing UI: Streamlit
  
Optional Modules:
  Queue: Redis (for async operations)
  Cache: Redis/In-memory
  File Storage: Local filesystem → S3 (future)
  
Development:
  Package Manager: Poetry
  Testing: pytest
  Code Format: black + ruff
  Type Checking: mypy
```

## PROJECT STRUCTURE

```
aviation-workflow/
├── pyproject.toml                 # Poetry dependencies
├── .env.example                   # Environment variables template
├── .env                          # Local environment (git ignored)
├── README.md                     # User documentation
├── architecture.md               # This file
│
├── core/                         # Core system (minimal, never changes)
│   ├── __init__.py
│   ├── config.py                # System configuration
│   ├── database.py              # Database connection manager
│   ├── models.py                # Core data models (work_items only)
│   ├── workflow_engine.py       # Burr integration
│   └── plugin_manager.py        # Plugin loading system
│
├── api/                          # FastAPI application
│   ├── __init__.py
│   ├── main.py                  # FastAPI app initialization
│   ├── dependencies.py          # Shared dependencies
│   └── middleware.py            # CORS, logging, etc.
│
├── modules/                      # Pluggable modules (add/remove freely)
│   ├── __init__.py
│   │
│   ├── departments/             # Department management module
│   │   ├── __init__.py
│   │   ├── models.py           # Department SQLModel
│   │   ├── routes.py           # /api/departments endpoints
│   │   ├── service.py          # Business logic
│   │   └── schemas.py          # Pydantic schemas
│   │
│   ├── approvals/               # Approval/rejection module
│   │   ├── __init__.py
│   │   ├── models.py           # Approval history model
│   │   ├── routes.py           # /api/approvals endpoints
│   │   ├── service.py          # Approval logic
│   │   ├── validators.py       # Approval rules
│   │   └── schemas.py
│   │
│   ├── comments/                # Comments module
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── routes.py           # /api/comments endpoints
│   │   ├── service.py
│   │   └── schemas.py
│   │
│   ├── templates/               # Workflow templates module
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── routes.py           # /api/templates endpoints
│   │   ├── service.py
│   │   └── schemas.py
│   │
│   └── reports/                 # Reporting module (future)
│       ├── __init__.py
│       ├── routes.py
│       └── service.py
│
├── workflows/                    # Workflow definitions (Burr)
│   ├── __init__.py
│   ├── base_workflow.py        # Abstract base workflow
│   ├── sequential_approval.py   # Main approval workflow
│   └── configs/                # YAML workflow configurations
│       ├── standard.yaml
│       └── custom.yaml
│
├── ui/                          # Streamlit interface
│   ├── __init__.py
│   ├── app.py                  # Main Streamlit app
│   ├── pages/                  # Multi-page app
│   │   ├── 1_📋_Dashboard.py
│   │   ├── 2_➕_Create_Item.py
│   │   ├── 3_✅_Approvals.py
│   │   └── 4_📊_Reports.py
│   └── components/             # Reusable UI components
│       ├── __init__.py
│       ├── workflow_viz.py    # Workflow visualization
│       └── item_card.py       # Work item display
│
├── migrations/                  # Database migrations
│   ├── __init__.py
│   └── versions/
│       └── 001_initial.py
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py            # pytest fixtures
│   ├── test_core/
│   ├── test_modules/
│   └── test_workflows/
│
└── scripts/                     # Utility scripts
    ├── init_db.py              # Database initialization
    ├── seed_data.py            # Sample data generator
    └── run_dev.py              # Development server runner
```

## CORE SYSTEM DESIGN

### 1. Plugin Manager System

```python
# core/plugin_manager.py

class ModuleConfig:
    """Configuration for a pluggable module"""
    name: str
    enabled: bool = True
    routes_path: str = None
    models_path: str = None
    dependencies: List[str] = []

class PluginManager:
    """
    Dynamically loads/unloads modules based on configuration.
    Each module must follow the standard interface.
    """
    
    def load_module(self, module_name: str):
        """Dynamically import and register a module"""
        
    def register_routes(self, app: FastAPI):
        """Register all enabled module routes"""
        
    def get_models(self):
        """Collect all SQLModel models for migration"""
```

### 2. Workflow Engine Integration

```python
# core/workflow_engine.py

from burr.core import State, Action, ApplicationBuilder

class WorkflowEngine:
    """
    Burr-based workflow engine for state management.
    Handles ONLY state transitions, not business logic.
    """
    
    def create_workflow(self, template: str) -> Application:
        """Create workflow from template"""
        
    def execute_transition(self, 
                          workflow_id: str, 
                          action: str, 
                          context: dict) -> State:
        """Execute state transition with validation"""
        
    def get_available_actions(self, workflow_id: str) -> List[str]:
        """Get valid actions for current state"""
```

## DATABASE SCHEMA

### Core Tables (Always Present)

```sql
-- Work Items (Core)
CREATE TABLE work_items (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    title TEXT NOT NULL,
    description TEXT,
    workflow_template TEXT NOT NULL,  -- References workflow config
    current_state TEXT NOT NULL,      -- Burr state
    current_step INTEGER DEFAULT 0,
    workflow_data JSON NOT NULL,      -- Serialized Burr state
    metadata JSON,                    -- Flexible additional data
    status TEXT DEFAULT 'active',     -- active/completed/cancelled
    priority TEXT DEFAULT 'normal',   -- normal/urgent
    created_by TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_work_items_status ON work_items(status);
CREATE INDEX idx_work_items_current_state ON work_items(current_state);
```

### Module Tables (Loaded Dynamically)

```sql
-- Departments Module
CREATE TABLE IF NOT EXISTS departments (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    metadata JSON,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Approvals Module  
CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    work_item_id TEXT NOT NULL REFERENCES work_items(id),
    action TEXT NOT NULL,  -- approved/rejected
    from_state TEXT,
    to_state TEXT,
    from_department_id TEXT REFERENCES departments(id),
    to_department_id TEXT REFERENCES departments(id),
    comment TEXT,
    actor_name TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comments Module
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    work_item_id TEXT NOT NULL REFERENCES work_items(id),
    content TEXT NOT NULL,
    author_name TEXT DEFAULT 'User',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Templates Module
CREATE TABLE IF NOT EXISTS workflow_templates (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    department_sequence JSON NOT NULL,  -- ["dept_id_1", "dept_id_2"]
    approval_rules JSON,                -- Conditional logic
    metadata JSON,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## WORKFLOW CONFIGURATION

### Burr Workflow Definition

```python
# workflows/sequential_approval.py

from burr.core import Action, State, when, default
from typing import Dict, Any

class ApprovalAction(Action):
    """Base action for approval workflows"""
    
    @property
    def reads(self) -> list[str]:
        return ["current_step", "department_sequence", "status"]
    
    @property
    def writes(self) -> list[str]:
        return ["current_step", "status", "history"]

class Approve(ApprovalAction):
    """Move to next department"""
    
    def run(self, state: State, comment: str = None) -> Dict[str, Any]:
        current_step = state["current_step"]
        sequence = state["department_sequence"]
        
        next_step = current_step + 1
        is_complete = next_step >= len(sequence)
        
        return {
            "current_step": next_step if not is_complete else current_step,
            "status": "completed" if is_complete else "active",
            "history": state.get("history", []) + [{
                "action": "approved",
                "from_step": current_step,
                "to_step": next_step,
                "comment": comment,
                "timestamp": datetime.now().isoformat()
            }]
        }

class Reject(ApprovalAction):
    """Send back to previous department"""
    
    def run(self, state: State, target_step: int, comment: str) -> Dict[str, Any]:
        return {
            "current_step": target_step,
            "status": "active",
            "history": state.get("history", []) + [{
                "action": "rejected",
                "from_step": state["current_step"],
                "to_step": target_step,
                "comment": comment,
                "timestamp": datetime.now().isoformat()
            }]
        }

# Workflow Builder
def build_approval_workflow(department_sequence: list) -> Application:
    """Build a Burr application for approval workflow"""
    
    return (
        ApplicationBuilder()
        .with_actions(
            approve=Approve(),
            reject=Reject(),
            cancel=Cancel(),
        )
        .with_transitions(
            ("approve", "approve", when(status="active")),
            ("approve", "complete", when(status="completed")),
            ("reject", "approve", default),
            ("*", "cancel", when(action="cancel")),
        )
        .with_initial_state(
            current_step=0,
            department_sequence=department_sequence,
            status="active",
            history=[]
        )
        .with_tracker(LocalTrackingClient("burr_state.db"))
        .build()
    )
```

### YAML Workflow Configuration

```yaml
# workflows/configs/standard.yaml

name: "Standard Approval Workflow"
description: "Default sequential approval through all departments"

states:
  - name: "draft"
    type: "initial"
  - name: "in_review"
    type: "approval"
  - name: "completed"
    type: "terminal"
  - name: "cancelled"
    type: "terminal"

transitions:
  - from: "draft"
    to: "in_review"
    action: "submit"
  - from: "in_review"
    to: "in_review"
    action: "approve"
    condition: "not_final_approval"
  - from: "in_review"
    to: "completed"
    action: "approve"
    condition: "is_final_approval"
  - from: "in_review"
    to: "in_review"
    action: "reject"

approval_rules:
  min_approvals: 1
  allow_self_approval: false
  escalation_timeout_hours: 48
```

## API ENDPOINTS

### Core Endpoints

```python
# api/main.py

from fastapi import FastAPI
from core.plugin_manager import PluginManager

app = FastAPI(title="Aviation Workflow System")
plugin_manager = PluginManager()

# Core endpoints (always available)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/work-items")
async def list_work_items(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all work items with filtering"""

@app.post("/api/work-items")
async def create_work_item(
    title: str,
    description: str,
    template_id: str,
    department_ids: List[str]
):
    """Create new work item with workflow"""

@app.get("/api/work-items/{item_id}")
async def get_work_item(item_id: str):
    """Get single work item with full state"""

@app.post("/api/work-items/{item_id}/transition")
async def execute_transition(
    item_id: str,
    action: str,  # approve/reject/cancel
    comment: Optional[str] = None,
    target_step: Optional[int] = None
):
    """Execute workflow transition"""

# Module routes loaded dynamically
plugin_manager.register_routes(app)
```

### Module Endpoints (Dynamically Loaded)

```python
# modules/departments/routes.py

from fastapi import APIRouter, Depends
from typing import List

router = APIRouter(prefix="/api/departments", tags=["departments"])

@router.get("/", response_model=List[DepartmentSchema])
async def list_departments():
    """List all departments"""

@router.post("/", response_model=DepartmentSchema)
async def create_department(department: DepartmentCreate):
    """Create new department"""

@router.put("/{dept_id}")
async def update_department(dept_id: str, department: DepartmentUpdate):
    """Update department"""

@router.delete("/{dept_id}")
async def delete_department(dept_id: str):
    """Soft delete department"""
```

## MODULE INTERFACE SPECIFICATION

Every module MUST follow this interface to be pluggable:

```python
# modules/<module_name>/__init__.py

from typing import Optional
from fastapi import APIRouter

class ModuleInterface:
    """Standard interface for all modules"""
    
    # Required attributes
    name: str = "module_name"
    version: str = "1.0.0"
    description: str = "Module description"
    
    # Optional components
    router: Optional[APIRouter] = None
    models: Optional[List[SQLModel]] = None
    dependencies: Optional[List[str]] = None
    
    def on_load(self):
        """Called when module is loaded"""
        pass
    
    def on_unload(self):
        """Called when module is unloaded"""
        pass
    
    def validate_config(self, config: dict) -> bool:
        """Validate module configuration"""
        return True
```

## CONFIGURATION MANAGEMENT

### Environment Variables (.env)

```bash
# Core Configuration
APP_NAME="Aviation Workflow System"
APP_ENV="development"  # development/staging/production
DEBUG=true

# Database
DATABASE_URL="sqlite:///./workflow.db"  # PostgreSQL in production
# DATABASE_URL="postgresql://user:pass@localhost/workflow"

# Redis (Optional)
REDIS_URL="redis://localhost:6379/0"
USE_REDIS=false

# Burr Configuration
BURR_TRACKER_TYPE="local"  # local/api
BURR_STATE_DIR="./burr_state"

# Module Configuration
ENABLED_MODULES="departments,approvals,comments,templates"
MODULE_AUTO_LOAD=true

# API Configuration
API_PREFIX="/api"
API_VERSION="v1"
CORS_ORIGINS="http://localhost:8501"  # Streamlit default

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS="localhost"
```

### Module Configuration (config.yaml)

```yaml
# core/config.yaml

modules:
  departments:
    enabled: true
    auto_create_defaults: true
    default_departments:
      - name: "Engineering"
        code: "ENG"
      - name: "Quality Control"
        code: "QC"
      - name: "Operations"
        code: "OPS"
  
  approvals:
    enabled: true
    require_comment: false
    allow_skip: false
    
  comments:
    enabled: true
    max_length: 5000
    allow_edit: false
    
  templates:
    enabled: true
    allow_custom: true
    
  reports:
    enabled: false  # Future module
```

## STREAMLIT UI STRUCTURE

### Main App (ui/app.py)

```python
import streamlit as st
import requests
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Aviation Workflow System",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if "selected_item" not in st.session_state:
    st.session_state.selected_item = None

# API base URL
API_URL = "http://localhost:8000/api"

# Sidebar navigation
with st.sidebar:
    st.title("✈️ Aviation Workflow")
    
    # Module status
    st.subheader("Active Modules")
    modules = requests.get(f"{API_URL}/modules/status").json()
    for module in modules:
        st.success(f"✅ {module['name']}")
    
    # Quick stats
    st.subheader("System Stats")
    stats = requests.get(f"{API_URL}/stats").json()
    st.metric("Active Items", stats["active_items"])
    st.metric("Pending Approvals", stats["pending_approvals"])

# Main content area
st.title("Workflow Dashboard")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📋 Active Items", "✅ My Approvals", "📊 Analytics"])

with tab1:
    # Work items list
    items = requests.get(f"{API_URL}/work-items").json()
    for item in items:
        with st.expander(f"{item['title']} - {item['status']}"):
            st.write(item['description'])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("View Details", key=f"view_{item['id']}"):
                    st.session_state.selected_item = item['id']
            with col2:
                if st.button("Take Action", key=f"action_{item['id']}"):
                    # Open action modal
                    pass
```

## DEVELOPMENT WORKFLOW

### Initial Setup Commands

```bash
# 1. Create project
poetry new aviation-workflow
cd aviation-workflow

# 2. Add dependencies
poetry add fastapi uvicorn sqlmodel burr streamlit
poetry add redis python-dotenv pyyaml
poetry add --dev pytest black ruff mypy

# 3. Initialize database
python scripts/init_db.py

# 4. Seed sample data
python scripts/seed_data.py

# 5. Run development servers
python scripts/run_dev.py  # Starts both FastAPI and Streamlit
```

### Adding a New Module

```bash
# 1. Create module structure
mkdir -p modules/new_feature
touch modules/new_feature/{__init__.py,models.py,routes.py,service.py,schemas.py}

# 2. Implement ModuleInterface in __init__.py

# 3. Add to ENABLED_MODULES in .env

# 4. Restart server - module auto-loads
```

### Testing Strategy

```python
# tests/test_modules/test_approvals.py

import pytest
from fastapi.testclient import TestClient

def test_approval_workflow():
    """Test complete approval cycle"""
    # 1. Create work item
    # 2. Approve through departments
    # 3. Verify state transitions
    # 4. Test rejection flow
```

## DEPLOYMENT INSTRUCTIONS

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY . .

# Run both services
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 & streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0"]
```

### Production Considerations

1. **Database**: Migrate to PostgreSQL
2. **Cache**: Enable Redis for session management
3. **Queue**: Use Redis/RabbitMQ for async tasks
4. **Storage**: Move to S3 for file attachments
5. **Monitoring**: Add Prometheus metrics endpoint
6. **Logging**: Structured logging with correlation IDs

## LLM IMPLEMENTATION INSTRUCTIONS

### For Claude Code Agent

When implementing this architecture:

1. **Start with Core**: Build `core/` directory first - this never changes
2. **Add Base Workflow**: Implement `workflows/sequential_approval.py`
3. **Create API Shell**: Set up FastAPI with plugin manager
4. **Add Modules Incrementally**: Start with departments, then approvals
5. **Test Each Module**: Ensure module can be enabled/disabled
6. **Add Streamlit Last**: UI is optional for backend testing

### Code Generation Priorities

1. **Models First**: Define SQLModel classes
2. **Services Second**: Business logic in service layer
3. **Routes Third**: Thin controller layer
4. **UI Last**: Streamlit for visualization

### Testing Checkpoints

After each module:

- [ ] Module loads successfully
- [ ] Routes are accessible
- [ ] Database tables created
- [ ] Can be disabled without breaking system
- [ ] State transitions work correctly

## SUCCESS METRICS

The implementation is successful when:

1. ✅ Can create work item with 3+ departments
2. ✅ Can approve and see state change
3. ✅ Can reject to any previous step
4. ✅ Can add/remove modules without breaking
5. ✅ Burr tracks all state transitions
6. ✅ Streamlit shows workflow visualization
7. ✅ System runs on 8GB RAM
8. ✅ Any module can be deleted and system still works

## COMMON PITFALLS TO AVOID

1. **Don't hardcode department IDs** - Use configuration
2. **Don't mix business logic with workflow** - Burr handles state only
3. **Don't create module dependencies** - Each module is independent
4. **Don't skip the plugin interface** - All modules must implement it
5. **Don't use global state** - Use dependency injection

## FUTURE EXPANSION PATHS

After MVP success, these modules can be added:

- **notifications/**: Email/Slack notifications
- **files/**: File attachment handling
- **analytics/**: Performance metrics
- **auth/**: User authentication
- **permissions/**: Role-based access
- **audit/**: Compliance logging
- **integrations/**: External system connectors

Each module follows the same pattern and can be developed independently.