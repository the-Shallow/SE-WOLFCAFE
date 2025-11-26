# Getting Started with SafeBites - Important Things to Know

## 🚨 Critical Information Before You Start

### 1. **This is NOT a Simple REST API**

SafeBites is a **multi-agent conversational AI system** for food allergy detection. Understanding the architecture is crucial:

```
User Query
    ↓
LangGraph Pipeline (6 stages)
    ↓
Intent Extraction → FAISS Search → Allergen Filtering → Response Synthesis
    ↓
Formatted JSON Response
```

**Key Point**: Most functionality happens through the **conversational search pipeline**, not traditional CRUD operations.

---

## 🔑 Prerequisites & Environment Setup

### Required Accounts & API Keys

You **MUST** have the following before running the project:

1. **OpenAI API Key** (Required)
   - Used for: Embeddings, LLM intent extraction, allergen detection
   - Get from: https://platform.openai.com/api-keys
   - **Cost**: ~$0.10-0.50 per 100 queries (depending on usage)
   - Add to `.env` as `OPENAI_KEY=sk-...`

2. **MongoDB Database** (Required)
   - Recommended: MongoDB Atlas (free tier works)
   - Get from: https://www.mongodb.com/cloud/atlas
   - Add to `.env` as `MONGO_URI=mongodb+srv://...`

3. **JWT Secret** (Required)
   - Any random string for JWT token signing
   - Add to `.env` as `JWT_SECRET=your-secret-key`

### Environment File (`.env`)

Create a `.env` file in `backend/` with:

```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
OPENAI_KEY=sk-proj-...
JWT_SECRET=your-random-secret-key-here
DB_NAME=foodapp
TEST_DB_NAME=foodapp_test
```

**⚠️ NEVER commit `.env` to git!** It's already in `.gitignore`.

---

## 🏗️ Architecture Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────┐
│  API Layer (FastAPI Routers)       │  ← HTTP endpoints
├─────────────────────────────────────┤
│  Service Layer (Business Logic)    │  ← Core functionality
├─────────────────────────────────────┤
│  Data Layer (MongoDB + FAISS)      │  ← Storage
└─────────────────────────────────────┘
```

### Key Services You'll Work With

| Service | File | Purpose | Critical? |
|---------|------|---------|-----------|
| **Intent Service** | `services/intent_service.py` | Classifies user queries (menu_search, dish_info, irrelevant) | 🔴 Critical |
| **FAISS Service** | `services/faiss_service.py` | Semantic search with vector embeddings | 🔴 Critical |
| **Retrieval Service** | `services/retrieval_service.py` | Fetches menu items based on queries | 🔴 Critical |
| **Context Resolver** | `services/context_resolver.py` | Maintains conversation history | 🟡 Important |
| **State Service** | `services/state_service.py` | Manages chat sessions | 🟡 Important |
| **Dish Service** | `services/dish_service.py` | CRUD operations for dishes | 🟢 Standard |
| **Restaurant Service** | `services/restaurant_service.py` | Restaurant management + CSV upload | 🟢 Standard |

---

## 🧠 Understanding the Conversation Pipeline

### The Core Workflow (LangGraph)

**File**: `app/flow/graph.py`

When a user sends a query to `/restaurants/search`, it goes through:

```
1. context_resolver
   ↓ (Rebuilds conversation context from previous messages)
2. intent_classifier
   ↓ (Extracts structured intents: menu_search, dish_info, irrelevant)
3. query_part_generator
   ↓ (Organizes intents into structured query parts)
4. menu_retriever
   ↓ (FAISS semantic search for matching dishes)
5. informative_retriever
   ↓ (Fetches detailed allergen/nutrition info)
6. format_final_response
   ↓ (Synthesizes natural language + JSON response)
```

**State Model**: `ChatState` (in `app/flow/state.py`)
- Stores: user_id, session_id, restaurant_id, query, intents, results, response
- Passed through all pipeline stages

**⚠️ Important**: If you modify the pipeline, you MUST update the ChatState model accordingly.

---

## 🎯 The Three Query Types

The system classifies every query into one of three types:

### 1. **menu_search** - Finding dishes
**Examples**:
- "Show me gluten-free pasta"
- "Any nut-free desserts?"
- "What vegetarian options do you have?"

**Handled by**: FAISS semantic search + allergen filtering

---

### 2. **dish_info** - Detailed information
**Examples**:
- "How many calories in the Caesar salad?"
- "Does the carbonara have dairy?"
- "What are the ingredients in the burger?"

**Handled by**: LLM extraction from dish metadata

---

### 3. **irrelevant** - Off-topic queries
**Examples**:
- "What's the weather today?"
- "Tell me a joke"
- "How do I get there?"

**Handled by**: Polite rejection response

---

## 🔍 FAISS Vector Database - Critical Knowledge

### What You Need to Know

1. **Index Location**: `backend/faiss_index_restaurant/`
   - Not in MongoDB, stored on filesystem
   - **Must be rebuilt** when:
     - Deploying to new environment
     - After loading seed data
     - After bulk dish updates

2. **Embedding Model**: OpenAI `text-embedding-3-large` (1536 dimensions)
   - Each query costs ~$0.0001 to embed
   - Each dish costs ~$0.0001 to embed

3. **Index Rebuilding**:
   ```bash
   # Manual rebuild
   python -c "from app.services.faiss_service import build_faiss_from_db; build_faiss_from_db()"

   # Auto-rebuilds on startup if missing
   uvicorn app.main:app --reload
   ```

4. **Search Process**:
   ```
   Query: "nut-free pasta"
        ↓
   [Extract Intent] → positive: ["pasta"], negative: ["nuts"]
        ↓
   [FAISS Search] → Find pasta dishes
        ↓
   [Filter Negatives] → Remove nut-containing dishes
        ↓
   [Centroid Ranking] → Sort by relevance
   ```

**⚠️ Common Pitfall**: If search returns no results, check:
- Is FAISS index built?
- Is threshold too high? (default: 0.8)
- Are there dishes in the database?

---

## 🍽️ Data Flow: Restaurant → Dishes → FAISS

### How Data Gets Into The System

```
1. Restaurant Creation (POST /restaurants/)
        ↓
2. Upload CSV Menu File
        ↓
3. CSV Parsing (in restaurant_service.py)
        ↓
4. LLM Enrichment for Each Dish:
   - Extract allergens (with confidence scores)
   - Estimate nutrition facts
   - Categorize ingredients
        ↓
5. Insert Dishes into MongoDB
        ↓
6. Update FAISS Index
        ↓
7. Dishes Now Searchable
```

### CSV Format Expected

**Required columns**:
- `dish_name`
- `description`
- `ingredients` (comma-separated)
- `price`

**Optional columns**:
- `allergens`
- `nutrition_info`
- `serving_size`

**Example**:
```csv
dish_name,description,ingredients,price
Margherita Pizza,Classic tomato and mozzarella,"tomato sauce,mozzarella,basil",12.99
Caesar Salad,Romaine with parmesan and croutons,"romaine,parmesan,croutons,caesar dressing",8.50
```

---

## 🚀 Development Workflow

### Initial Setup (First Time)

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env  # (if available, otherwise create manually)
# Edit .env with your credentials

# 5. Generate seed data (costs ~$0.05 in OpenAI API)
python generate_seed.py

# 6. Load seed data into MongoDB
python load_seed_data.py

# 7. Start server
uvicorn app.main:app --reload --port 8000

# Server will auto-build FAISS index on startup
```

### Daily Development

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Start server
uvicorn app.main:app --reload --port 8000

# 3. Check server is running
curl http://localhost:8000/
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run with coverage
pytest --cov=app

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 🧪 Testing Important Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/
# Expected: {"message": "Welcome to SafeBites API"}
```

### 2. Create User
```bash
curl -X POST http://localhost:8000/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "username": "testuser",
    "password": "testpass123",
    "allergen_preferences": ["peanuts", "shellfish"]
  }'
```

### 3. Login
```bash
curl -X POST "http://localhost:8000/users/login?username=testuser&password=testpass123"
# Copy the "access_token" from response
```

### 4. Conversational Search (The Core Feature!)
```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8000/restaurants/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "user_id": "user_id_here",
    "restaurant_id": "rest_1",
    "query": "Show me nut-free pasta dishes"
  }'
```

---

## ⚠️ Common Pitfalls & How to Avoid Them

### 1. **FAISS Index Not Found Error**
**Problem**: `GenericException: FAISS index could not be loaded`

**Solution**:
```python
from app.services.faiss_service import build_faiss_from_db
build_faiss_from_db()
```

### 2. **No Search Results Returned**
**Problem**: Valid query but empty results

**Possible causes**:
- No dishes in database → Load seed data
- Threshold too high → Lower to 0.5 in `search_dishes()`
- Wrong restaurant_id → Check restaurant exists
- FAISS index out of sync → Rebuild index

### 3. **OpenAI Rate Limit Errors**
**Problem**: `RateLimitError: You exceeded your current quota`

**Solutions**:
- Check API key is valid
- Add credits to OpenAI account
- Switch to `gpt-4o-mini` instead of `gpt-4` (cheaper)
- Reduce batch sizes in seed generation

### 4. **MongoDB Connection Timeout**
**Problem**: Can't connect to MongoDB

**Solutions**:
- Check MONGO_URI in `.env`
- Whitelist your IP in MongoDB Atlas
- Check network connectivity
- Verify username/password

### 5. **Slow Startup Time**
**Problem**: Server takes 2-3 minutes to start

**Cause**: FAISS index rebuilding from database

**Solution**: This is normal on first startup. Subsequent starts are faster if index exists.

---

## 🔐 Security Considerations

### What's Implemented

✅ **JWT Authentication** - Token-based auth for protected routes
✅ **Password Hashing** - Bcrypt with salt
✅ **CORS Configuration** - Restricted origins
✅ **Input Validation** - Pydantic models

### What You Should NOT Do

❌ Don't commit `.env` file
❌ Don't hardcode API keys
❌ Don't disable CORS in production
❌ Don't skip user authentication for critical endpoints
❌ Don't trust user input without validation

### Protected Endpoints

Require `Authorization: Bearer <token>` header:
- `GET /users/me`
- `PUT /users/me`
- `DELETE /users/me`
- `POST /restaurants/search`
- `GET /restaurants/history/{user_id}/{restaurant_id}`
- `GET /dishes/filter`

---

## 📊 Monitoring & Debugging

### Log Files

Located in `backend/app/logs/`:
- `safebites.log` - General application logs
- `safebites.log.1` - Rotated logs
- `error.log` - Error-only logs

### LLM Usage Tracking

**File**: `backend/logs/llm_usage.csv`

Tracks:
- Timestamp
- Model used
- Prompt tokens
- Completion tokens
- Total cost

**View usage**:
```bash
cat logs/llm_usage.csv | tail -20
```

### Intent Search Logs

**File**: `backend/intent_dishes_log.json`

Logs every semantic search with:
- Query text
- Extracted intents (positive/negative)
- Dishes found
- Filter results

**View logs**:
```bash
cat intent_dishes_log.json | jq '.' | less
```

---

## 🏷️ Code Style & Best Practices

### Naming Conventions

- **Services**: `verb_noun()` format
  - Good: `create_restaurant()`, `get_user_by_id()`
  - Bad: `restaurant_creator()`, `user()`

- **Models**: `NounModel` or `NounCreate/Update/Out`
  - Example: `UserCreate`, `DishOut`, `RestaurantUpdate`

- **Routes**: RESTful conventions
  - `GET /resources/` - List all
  - `GET /resources/{id}` - Get one
  - `POST /resources/` - Create
  - `PUT /resources/{id}` - Full update
  - `PATCH /resources/{id}` - Partial update
  - `DELETE /resources/{id}` - Delete

### Error Handling

Use custom exceptions from `models/exception_model.py`:

```python
from app.models.exception_model import NotFoundException, BadRequestException

# Good
if not dish:
    raise NotFoundException("Dish not found")

# Bad
if not dish:
    return {"error": "Dish not found"}  # Don't do this
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debug info")    # Development only
logger.info("Important milestones")    # Normal operations
logger.warning("Recoverable issues")   # Warnings
logger.error("Error occurred")         # Errors
```

---

## 🔄 Git Workflow

### Current Branch Structure

**Main Branch**: `master`
- Production-ready code
- Protected branch

**Before Making Changes**:
```bash
# 1. Pull latest changes
git checkout master
git pull origin master

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes, commit often
git add .
git commit -m "Descriptive commit message"

# 4. Push to remote
git push origin feature/your-feature-name

# 5. Create pull request on GitHub
```

### Current Git Status

Modified files (not committed):
- `backend/app/logs/*.log` - Log files (should be in `.gitignore`)
- `backend/app/services/*.py` - Service files with changes
- `backend/generate_seed.py` - Updated to use `gpt-4o-mini`

**New files**:
- `backend/BACKEND_ARCHITECTURE.md` - Architecture documentation
- `backend/VECTOR_DATABASE.md` - Vector DB documentation
- `backend/load_seed_data.py` - Seed data loader script

---

## 🎓 Learning Resources

### Key Technologies to Understand

1. **FastAPI** (Web Framework)
   - Docs: https://fastapi.tiangolo.com/
   - Focus on: Dependency injection, Pydantic models, async/await

2. **LangChain** (LLM Framework)
   - Docs: https://python.langchain.com/
   - Focus on: Prompts, chains, agents, tools

3. **LangGraph** (Workflow Orchestration)
   - Docs: https://langchain-ai.github.io/langgraph/
   - Focus on: State graphs, nodes, edges

4. **FAISS** (Vector Search)
   - Docs: https://faiss.ai/
   - Focus on: Index types, similarity search

5. **MongoDB** (Database)
   - Docs: https://pymongo.readthedocs.io/
   - Focus on: Queries, indexes, aggregations

---

## 🚦 Troubleshooting Checklist

Before asking for help, check:

- [ ] Is `.env` file properly configured?
- [ ] Is MongoDB accessible and has data?
- [ ] Is FAISS index built?
- [ ] Is OpenAI API key valid and has credits?
- [ ] Are all dependencies installed?
- [ ] Is virtual environment activated?
- [ ] Are logs showing any errors?
- [ ] Did you restart the server after code changes?

**Check logs**:
```bash
tail -f app/logs/safebites.log
tail -f app/logs/error.log
```

---

## 🎯 Quick Reference Commands

```bash
# Start server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Rebuild FAISS index
python -c "from app.services.faiss_service import build_faiss_from_db; build_faiss_from_db()"

# Load seed data
python load_seed_data.py

# Generate new seed data
python generate_seed.py

# View MongoDB data
# (Use MongoDB Compass or mongo shell)

# Check server health
curl http://localhost:8000/

# View API docs
open http://localhost:8000/docs
```

---

## 📞 Getting Help

### Project Documentation

1. **Backend Architecture**: See `BACKEND_ARCHITECTURE.md`
2. **Vector Database**: See `VECTOR_DATABASE.md`
3. **This Guide**: See `GETTING_STARTED.md`
4. **API Documentation**: http://localhost:8000/docs (when server running)

### Debugging Steps

1. Check logs in `app/logs/`
2. Review FastAPI automatic docs at `/docs`
3. Test individual services in Python REPL
4. Check MongoDB data directly
5. Verify FAISS index exists

---

## ✅ Pre-Flight Checklist

Before you start coding:

- [ ] I have OpenAI API key with credits
- [ ] I have MongoDB database set up
- [ ] I have `.env` file configured
- [ ] I understand the conversational pipeline
- [ ] I know the difference between menu_search and dish_info
- [ ] I understand FAISS is on filesystem, not MongoDB
- [ ] I know how to rebuild FAISS index
- [ ] I've loaded seed data successfully
- [ ] I can start the server without errors
- [ ] I've tested the `/restaurants/search` endpoint
- [ ] I've read the architecture documentation

---

## 🎉 You're Ready!

Now that you understand the critical components, you can start working on SafeBites. Remember:

1. **The conversation pipeline is the heart** of the system
2. **FAISS index must be in sync** with MongoDB
3. **LLM costs real money** - be mindful during development
4. **Test thoroughly** - allergen detection is safety-critical
5. **Log everything** - debugging AI systems is hard without logs

Good luck! 🚀
