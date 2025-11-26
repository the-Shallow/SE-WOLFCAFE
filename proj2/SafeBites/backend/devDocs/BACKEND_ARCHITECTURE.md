# SafeBites Backend Architecture

## Overview

SafeBites is an AI-powered food allergy detection and recommendation system that helps users find safe menu items based on their allergen preferences. The backend uses conversational AI to understand natural language queries and provide personalized, allergen-safe dish recommendations.

**Tech Stack**: FastAPI + MongoDB + LangGraph + FAISS + OpenAI

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Environment configuration & logging
│   ├── db.py                      # MongoDB connection
│   ├── create_indexes.py          # Database index creation
│   ├── generate_seed.py           # Seed data generator
│   │
│   ├── models/                    # Pydantic data schemas
│   │   ├── user_model.py          # User schemas (Create, Update, Out)
│   │   ├── restaurant_model.py    # Restaurant & filter models
│   │   ├── dish_model.py          # Dish schemas with allergen info
│   │   ├── intent_model.py        # Intent extraction results
│   │   ├── session_model.py       # Chat session models
│   │   └── exception_model.py     # Custom exceptions
│   │
│   ├── routers/                   # API endpoint definitions
│   │   ├── user_router.py         # /users - Auth & profile management
│   │   ├── restaurant_router.py   # /restaurants - CRUD & chat search
│   │   └── dish_router.py         # /dishes - CRUD & filtering
│   │
│   ├── services/                  # Business logic layer
│   │   ├── user_service.py        # User CRUD & authentication
│   │   ├── restaurant_service.py  # Restaurant CRUD & CSV processing
│   │   ├── dish_service.py        # Dish CRUD & safety evaluation
│   │   ├── intent_service.py      # LLM-based intent classification
│   │   ├── state_service.py       # Chat session management
│   │   ├── faiss_service.py       # Vector embeddings & search
│   │   ├── retrieval_service.py   # Menu item retrieval
│   │   ├── dish_info_service.py   # Detailed dish information
│   │   ├── context_resolver.py    # Conversation context resolution
│   │   ├── response_synthesizer_tool.py  # Response formatting
│   │   └── orchestrator_service.py       # LangChain agent setup
│   │
│   ├── flow/                      # LangGraph conversation pipeline
│   │   ├── graph.py               # Multi-stage processing workflow
│   │   ├── state.py               # ChatState Pydantic model
│   │   └── state_store.py         # State persistence
│   │
│   ├── utils/                     # Utilities
│   │   ├── faiss_index.py         # FAISS index management
│   │   └── llm_tracker.py         # LLM usage tracking
│   │
│   └── tests/                     # Test suite
│       ├── unit/                  # Unit tests
│       ├── integration/           # Integration tests
│       └── conftest.py            # Pytest fixtures
│
├── seed_data/                     # Sample restaurant & dish data
├── requirements.txt               # Python dependencies
└── .env                          # Environment variables
```

---

## API Endpoints

### User Management (`/users`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/users/signup` | Register new user | No |
| POST | `/users/login` | Authenticate user | No |
| GET | `/users/me` | Get current user profile | Yes |
| PUT | `/users/me` | Update profile | Yes |
| DELETE | `/users/me` | Delete account | Yes |
| GET | `/users/{id_or_username}` | Get user by ID/username | No |

### Restaurant Management (`/restaurants`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/restaurants/` | Create restaurant + CSV upload | No |
| GET | `/restaurants/` | List all restaurants | No |
| GET | `/restaurants/{id}` | Get specific restaurant | No |
| PATCH | `/restaurants/{id}` | Update restaurant | No |
| DELETE | `/restaurants/{id}` | Delete restaurant | No |
| POST | `/restaurants/search` | **Conversational search** | Yes |
| GET | `/restaurants/history/{user_id}/{restaurant_id}` | Get chat history | Yes |

### Dish Management (`/dishes`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/dishes/{restaurant_id}` | Create dish | No |
| GET | `/dishes/` | List dishes (with filters) | No |
| GET | `/dishes/filter` | Filter by allergens | Yes |
| GET | `/dishes/{dish_id}` | Get dish details | No |
| PUT | `/dishes/{dish_id}` | Update dish | No |
| DELETE | `/dishes/{dish_id}` | Delete dish | No |

---

## Core Features

### 1. Authentication & User Management

**File**: `services/user_service.py`

- JWT-based authentication
- Bcrypt password hashing
- User allergen preferences stored in profile
- Token-based session management

**User Schema**:
```python
{
  "name": "John Doe",
  "username": "johndoe",
  "password": "hashed_password",
  "allergen_preferences": ["peanuts", "shellfish"]
}
```

---

### 2. Allergen Detection & Safety Scoring

**File**: `services/restaurant_service.py` (CSV processing)

When restaurants upload menus via CSV, each dish is enriched using LLM (GPT-4):

**AllergenInfo Schema**:
```python
{
  "allergen": "peanuts",
  "confidence": 0.95,
  "reasoning": "Contains peanut butter in sauce"
}
```

Dishes are marked as `safe_for_user: true/false` based on user allergen preferences.

---

### 3. Semantic Search with FAISS

**File**: `services/faiss_service.py`

- Uses OpenAI `text-embedding-3-large` (1536-dimensional vectors)
- Builds searchable index from all dishes
- Combines semantic similarity with metadata filtering
- Auto-rebuilds index on startup

**Search Flow**:
```
User Query → Embedding → FAISS Search → Top-K Dishes → Allergen Filter → Results
```

---

### 4. Conversational AI Pipeline (LangGraph)

**File**: `flow/graph.py`

**6-Stage Processing Workflow**:

```mermaid
User Query
    ↓
1. Context Resolver (rebuild conversation history)
    ↓
2. Intent Classifier (menu_search | dish_info | irrelevant)
    ↓
3. Query Part Generator (structured query objects)
    ↓
4. Menu Retriever (FAISS semantic search)
    ↓
5. Information Retriever (detailed allergen/nutrition data)
    ↓
6. Response Synthesizer (formatted JSON response)
    ↓
Frontend
```

**Intent Types**:
- `menu_search`: "Show me pasta dishes"
- `dish_info`: "Does the Caesar salad contain gluten?"
- `irrelevant`: "What's the weather today?"

---

### 5. Chat Session Management

**File**: `services/state_service.py`

- Persistent chat history per user-restaurant pair
- Context resolution from previous messages
- Session state stored in MongoDB

**ChatState Schema**:
```python
{
  "user_id": "user123",
  "session_id": "session456",
  "restaurant_id": "rest789",
  "query": "Show me nut-free desserts",
  "intents": [...],
  "menu_results": [...],
  "response": "Here are 3 nut-free desserts...",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

---

## Data Models

### User Model
```python
{
  "id": "ObjectId",
  "name": "string",
  "username": "string (3-72 chars)",
  "password": "hashed_string",
  "allergen_preferences": ["string"]
}
```

### Restaurant Model
```python
{
  "id": "ObjectId",
  "name": "string",
  "location": "string",
  "cuisine_type": "string",
  "rating": "float (0-5)",
  "menu_items": ["dish_ids"]
}
```

### Dish Model
```python
{
  "id": "ObjectId",
  "restaurant_id": "ObjectId",
  "name": "string",
  "description": "string",
  "ingredients": ["string"],
  "price": "float",
  "allergens": [
    {
      "allergen": "string",
      "confidence": "float (0-1)",
      "reasoning": "string"
    }
  ],
  "nutrition_facts": {
    "calories": "int",
    "protein": "string",
    "carbs": "string",
    "fat": "string"
  },
  "availability": "boolean"
}
```

---

## Environment Configuration

**File**: `.env`

```env
MONGO_URI=mongodb+srv://...
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-key
DB_NAME=foodapp
TEST_DB_NAME=foodapp_test
```

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `pymongo` | MongoDB client |
| `langchain` | LLM orchestration |
| `langgraph` | Conversation pipeline |
| `langchain-openai` | OpenAI integration |
| `faiss-cpu` | Vector similarity search |
| `passlib[bcrypt]` | Password hashing |
| `pydantic` | Data validation |
| `uvicorn` | ASGI server |
| `pytest` | Testing framework |

---

## Usage Example

### Restaurant Menu Upload

```bash
POST /restaurants/
Content-Type: multipart/form-data

{
  "name": "Italian Bistro",
  "location": "Downtown",
  "cuisine_type": "Italian",
  "rating": 4.5,
  "menu_file": "menu.csv"  # Columns: dish_name, description, ingredients, price
}
```

**Backend Process**:
1. Creates restaurant document
2. Parses CSV file
3. For each dish → LLM enrichment (allergens, nutrition)
4. Inserts dishes into MongoDB
5. Updates FAISS index with new embeddings

---

### Conversational Search

```bash
POST /restaurants/search
Authorization: Bearer <token>

{
  "user_id": "user123",
  "restaurant_id": "rest456",
  "query": "I'm allergic to shellfish. What pasta dishes do you have?"
}
```

**Response**:
```json
{
  "menu_results": [
    {
      "dish_name": "Spaghetti Carbonara",
      "safe_for_user": true,
      "allergens": [],
      "price": 14.99
    }
  ],
  "info_results": {
    "ingredients": ["pasta", "eggs", "bacon", "parmesan"],
    "nutrition": {"calories": 450}
  },
  "response": "I found 2 shellfish-free pasta dishes for you. The Spaghetti Carbonara is a great choice..."
}
```

---

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests
pytest -m integration

# With coverage
pytest --cov=app
```

---

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your MongoDB URI and OpenAI API key

# Create database indexes
python -m app.create_indexes

# Generate seed data (optional)
python -m app.generate_seed

# Run server
uvicorn app.main:app --reload --port 8000
```

---

## Architecture Highlights

**Separation of Concerns**:
- **Routers**: API endpoint definitions
- **Services**: Business logic & external integrations
- **Models**: Data validation & schemas
- **Flow**: Conversational AI pipeline

**Scalability**:
- Async FastAPI for high concurrency
- MongoDB for flexible schema & scalability
- FAISS for efficient vector search
- Modular service architecture

**AI Integration**:
- LangChain for agent orchestration
- LangGraph for multi-stage workflows
- OpenAI GPT-4 for intent classification & enrichment
- OpenAI embeddings for semantic search

**Security**:
- JWT authentication
- Bcrypt password hashing
- Environment-based secrets
- CORS configuration

---

## Future Enhancements

- [ ] Redis caching for frequently accessed dishes
- [ ] Multi-language support
- [ ] Image-based menu scanning
- [ ] Nutritional goal tracking
- [ ] Restaurant recommendation engine
- [ ] Real-time menu updates via webhooks

---

## License

[Add your license information here]

## Contributors

[Add contributor information here]
