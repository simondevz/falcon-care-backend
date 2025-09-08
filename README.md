# FalconCare Backend - AI-Native RCM API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009639.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-FF6B6B.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **High-performance AI-powered backend for FalconCare's Revenue Cycle Management platform**

The FalconCare backend is a modern FastAPI application that orchestrates complex AI workflows using LangGraph, designed specifically for healthcare providers in the GCC region. It provides intelligent automation for patient data processing, medical coding, claims management, and denial handling.

## 🌟 Key Features

### 🤖 AI-Powered Workflows

- **LangGraph Integration**: Complex multi-agent AI workflows
- **OpenAI GPT-4**: Advanced natural language processing
- **Specialized Agents**: Data structuring, coding, eligibility, claims, and denial management
- **Confidence Scoring**: ML-based decision confidence assessment

### 🏥 Healthcare-Specific Features

- **Medical Coding**: Automated ICD-10 and CPT code suggestions
- **Eligibility Verification**: Real-time insurance eligibility checks
- **Claims Processing**: Intelligent claim preparation and optimization
- **Denial Management**: Automated denial analysis and appeal generation

### 🌍 GCC Regional Support

- **Multi-Payer Integration**: DAMAN, ADNIC, THIQA, BUPA support
- **Regional Compliance**: Built for GCC healthcare regulations
- **Multi-Language Processing**: Arabic and English clinical notes
- **Cultural Adaptation**: Designed for regional medical practices

### 🔧 Enterprise-Ready

- **High Performance**: Async FastAPI with optimized database queries
- **Scalable Architecture**: Microservices-ready design
- **Comprehensive API**: RESTful endpoints with OpenAPI documentation
- **Security First**: JWT authentication, role-based access, audit logging

## 🛠️ Technology Stack

### Core Framework

- **FastAPI 0.104.1** - Modern, fast web framework for building APIs
- **Python 3.11+** - Latest Python with performance improvements
- **Uvicorn** - Lightning-fast ASGI server

### AI & ML

- **LangGraph** - Advanced AI workflow orchestration
- **OpenAI Python SDK** - GPT-4 integration for NLP tasks
- **LangChain** - LLM application framework
- **Pydantic** - Data validation and settings management

### Database & ORM

- **PostgreSQL 15** - Robust relational database
- **SQLAlchemy 2.0** - Modern Python SQL toolkit and ORM
- **Alembic** - Database migrations
- **asyncpg** - Fast async PostgreSQL driver

### Authentication & Security

- **python-jose** - JWT token handling
- **passlib** - Password hashing with bcrypt
- **python-multipart** - File upload support

### Background Tasks & Caching

- **Redis** - Caching and session management
- **Celery** - Distributed task queue (planned)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)
- OpenAI API key

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/falconcare-backend.git
   cd falconcare-backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:

   ```bash
   # Database Configuration
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/falconcare

   # JWT Authentication
   JWT_SECRET=your-secret-key-change-in-production

   # OpenAI API
   OPENAI_API_KEY=your-openai-api-key

   # Environment
   ENVIRONMENT=development

   # Redis (optional)
   REDIS_URL=redis://localhost:6379/0

   # CORS Origins
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

5. **Set up database**

   ```bash
   # Create PostgreSQL database
   createdb falconcare

   # Run migrations
   alembic upgrade head
   ```

6. **Start the server**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the API**
   - **API**: http://localhost:8000
   - **Documentation**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc

## 📁 Project Structure

```
falconcare-backend/
├── agents/                        # LangGraph AI agents
│   ├── __init__.py
│   ├── rcm_agent.py              # Main RCM workflow orchestrator
│   ├── utils/                    # Agent utilities
│   │   ├── prompts.py           # AI agent prompts
│   │   ├── parsers.py           # Response parsers
│   │   └── validators.py        # Data validators
│   └── tools/                    # Specialized agent tools
│       ├── __init__.py
│       ├── patient_tools.py     # Patient data operations
│       ├── coding_tools.py      # Medical coding operations
│       ├── eligibility_tools.py # Insurance eligibility
│       ├── claims_tools.py      # Claims processing
│       └── denial_tools.py      # Denial management
├── controllers/                   # Business logic controllers
│   ├── __init__.py
│   ├── auth_controller.py       # Authentication endpoints
│   ├── patient_controller.py    # Patient management
│   ├── encounter_controller.py  # Medical encounters
│   ├── claims_controller.py     # Claims processing
│   └── rcm_chat_controller.py   # AI chat interface
├── models/                       # Database models
│   ├── __init__.py
│   ├── patient.py              # Patient data model
│   ├── encounter.py            # Medical encounter model
│   ├── claim.py                # Claims data model
│   ├── denial.py               # Denial data model
│   └── user.py                 # User authentication model
├── schemas/                      # Pydantic schemas
│   ├── __init__.py
│   ├── patient.py              # Patient API schemas
│   ├── encounter.py            # Encounter API schemas
│   ├── claim.py                # Claims API schemas
│   ├── auth.py                 # Authentication schemas
│   └── ai.py                   # AI response schemas
├── services/                     # Business services
│   ├── __init__.py
│   ├── patient_service.py      # Patient business logic
│   ├── encounter_service.py    # Encounter processing
│   ├── claims_service.py       # Claims management
│   ├── ai_service.py           # AI orchestration
│   └── payer_service.py        # Payer integrations
├── utils/                        # Utility functions
│   ├── __init__.py
│   ├── auth.py                 # Authentication utilities
│   ├── database.py             # Database utilities
│   ├── exceptions.py           # Custom exceptions
│   ├── logging.py              # Logging configuration
│   └── validators.py           # Data validation
├── database/                     # Database configuration
│   ├── __init__.py
│   ├── connection.py           # Database connection
│   └── migrations/             # Alembic migrations
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_agents.py          # AI agent tests
│   ├── test_controllers.py     # Controller tests
│   ├── test_services.py        # Service tests
│   └── fixtures/               # Test fixtures
├── alembic/                      # Database migrations
│   ├── versions/               # Migration files
│   ├── env.py                  # Migration environment
│   └── script.py.mako          # Migration template
├── .env.example                  # Environment variables template
├── alembic.ini                   # Alembic configuration
├── main.py                       # FastAPI application entry point
├── requirements.txt              # Python dependencies
└── Dockerfile                    # Docker configuration
```

## 🤖 AI Workflow Architecture

### LangGraph Agents

The backend uses LangGraph to orchestrate complex AI workflows:

#### 1. RCM Agent (`agents/rcm_agent.py`)

Main orchestrator that coordinates all RCM workflows:

```python
class RCMAgentExecutor:
    def __init__(self):
        self.graph = self._build_workflow_graph()

    def execute_step(self, state: RCMState, user_input: str):
        # Orchestrate AI workflow based on current state
        return self.graph.invoke(state)
```

#### 2. Specialized Tools (`agents/tools/`)

- **Patient Tools**: Data extraction and validation
- **Coding Tools**: ICD-10/CPT code suggestions
- **Eligibility Tools**: Insurance verification
- **Claims Tools**: Claim preparation and optimization
- **Denial Tools**: Denial analysis and appeal generation

### Workflow Examples

#### Encounter Processing Workflow

```
Unstructured Input → Parse & Clean → Extract Patient Info →
Validate & Standardize → Suggest Medical Codes →
Confidence Check → Auto-Approve/Human Review → Store
```

#### Claims Processing Workflow

```
Encounter Data → Eligibility Check → Code Validation →
Payer Rules → Claims Optimization → Submission Ready →
Submit to Payer → Track Status
```

## 📚 API Documentation

### Authentication Endpoints

```
POST   /auth/login        # User login
POST   /auth/refresh      # Refresh JWT token
POST   /auth/logout       # User logout
GET    /auth/me          # Get current user info
```

### Patient Management

```
POST   /patients         # Create patient record
GET    /patients/{id}    # Get patient details
PUT    /patients/{id}    # Update patient
DELETE /patients/{id}    # Delete patient
GET    /patients         # List patients (paginated)
```

### Encounter Processing

```
POST   /encounters                  # Create new encounter
GET    /encounters/{id}            # Get encounter details
PUT    /encounters/{id}            # Update encounter
POST   /encounters/{id}/process    # Trigger AI processing
GET    /encounters                 # List encounters
```

### Claims Management

```
POST   /claims                 # Create claim from encounter
GET    /claims/{id}           # Get claim details
PUT    /claims/{id}           # Update claim
POST   /claims/{id}/submit    # Submit claim to payer
GET    /claims                # List claims with filters
```

### AI Services

```
POST   /ai/chat                  # Chat with RCM agent
POST   /ai/structure-data        # Structure unstructured text
POST   /ai/suggest-codes         # Suggest ICD/CPT codes
POST   /ai/verify-eligibility    # Check insurance eligibility
POST   /ai/process-denial        # Analyze and process denials
```

### Health & Monitoring

```
GET    /health              # Health check
GET    /metrics             # Application metrics
```

## 🔧 Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/falconcare

# JWT Authentication
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# OpenAI API Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000

# Environment Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Payer Configuration (Mock for MVP)
MOCK_PAYER_ENABLED=true
PAYER_API_TIMEOUT=30

# Application Settings
MAX_UPLOAD_SIZE=10485760  # 10MB
PAGINATION_DEFAULT_SIZE=10
PAGINATION_MAX_SIZE=100
```

### Database Configuration

```python
# database/connection.py
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=True if os.getenv("ENVIRONMENT") == "development" else False,
    pool_size=10,
    max_overflow=20,
)
```

## 🔒 Security Features

### Authentication & Authorization

- **JWT Tokens**: Secure token-based authentication
- **Role-Based Access Control**: Granular permission system
- **Password Hashing**: bcrypt for secure password storage
- **Token Refresh**: Automatic token renewal

### Data Protection

- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **Input Validation**: Pydantic schema validation
- **Rate Limiting**: API endpoint protection
- **Audit Logging**: Comprehensive action tracking

### Healthcare Compliance

- **Data Encryption**: At-rest and in-transit encryption
- **Access Controls**: Role-based data access
- **Audit Trails**: Immutable logs for all actions
- **Privacy Controls**: Patient data protection

## 📊 Database Schema

### Core Entities

```sql
-- Patients table
patients (
    patient_id UUID PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(10),
    phone VARCHAR(20),
    email VARCHAR(255),
    insurance_provider VARCHAR(100),
    insurance_number VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Encounters table
encounters (
    encounter_id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(patient_id),
    encounter_date DATE,
    chief_complaint TEXT,
    clinical_notes TEXT,
    structured_data JSONB,
    ai_confidence_score DECIMAL(3,2),
    status VARCHAR(50),
    created_at TIMESTAMP
);

-- Claims table
claims (
    claim_id UUID PRIMARY KEY,
    encounter_id UUID REFERENCES encounters(encounter_id),
    claim_number VARCHAR(100),
    total_amount DECIMAL(10,2),
    status VARCHAR(50),
    submission_date DATE,
    payer_name VARCHAR(100),
    created_at TIMESTAMP
);
```
