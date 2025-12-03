# SafeBites Backend - Improvement Roadmap

## Executive Summary

Based on comprehensive code analysis, **80+ actionable improvements** were identified across code quality, performance, architecture, testing, documentation, and security. This document prioritizes these improvements into actionable sprints.

---

## 🚨 Critical Issues (Fix Immediately)

### Priority 1: Data Integrity & Runtime Errors

#### Issue #1: Typo - "availaibility" vs "availability"
**Impact**: Runtime `KeyError` exceptions
**Files Affected**:
- [services/dish_info_service.py:131](app/services/dish_info_service.py#L131)
- [services/retrieval_service.py:50](app/services/retrieval_service.py#L50)
- [tests/integration/test_chat_integration.py:26](app/tests/integration/test_chat_integration.py#L26)

**Solution**:
```bash
# Find and replace across codebase
grep -r "availaibility" backend/
# Replace with "availability"
```

**Estimated Effort**: 15 minutes

---

### Priority 2: Security Vulnerabilities

#### Issue #2: Weak Authentication System
**Impact**: Critical security vulnerability - users can be impersonated
**File**: [services/user_service.py:93-94](app/services/user_service.py#L93-L94)

**Current Code**:
```python
# INSECURE: User ID as token
return {"access_token": str(user["_id"]), "token_type": "bearer"}
```

**Solution**: Implement proper JWT tokens
```python
import jwt
from datetime import datetime, timedelta

def create_access_token(user_id: str, expires_delta: timedelta = timedelta(hours=24)):
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
```

**Estimated Effort**: 2-3 hours

---

#### Issue #3: Hardcoded User ID in Chat Endpoint
**Impact**: Breaks multi-user support, all chats attributed to same user
**File**: [routers/restaurant_router.py:79, 85](app/routers/restaurant_router.py#L79)

**Current Code**:
```python
session_id = state_service.get_or_create_session("u123", restaurant_id)
state = ChatState(user_id="u123", ...)
```

**Solution**:
```python
from fastapi import Depends
from app.services.user_service import get_current_user

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    user_id = verify_token(token)
    return user_id

@router.post("/search")
async def chat_search(
    payload: ChatQuery,
    user_id: str = Depends(get_current_user_id)
):
    session_id = state_service.get_or_create_session(user_id, payload.restaurant_id)
    state = ChatState(user_id=user_id, ...)
```

**Estimated Effort**: 1 hour

---

#### Issue #4: NoSQL Injection Risk
**Impact**: Potential code execution vulnerability
**File**: [services/dish_service.py:66-69](app/services/dish_service.py#L66-L69)

**Solution**:
```python
ALLOWED_QUERY_FIELDS = {"restaurant_id", "ingredients", "name", "availability"}

def sanitize_query(query: dict) -> dict:
    """Prevent NoSQL injection by validating query fields."""
    sanitized = {}
    for key, value in query.items():
        # Reject MongoDB operators
        if key.startswith("$"):
            raise BadRequestException(f"Operator queries not allowed: {key}")
        # Only allow whitelisted fields
        if key not in ALLOWED_QUERY_FIELDS:
            raise BadRequestException(f"Invalid query field: {key}")
        sanitized[key] = value
    return sanitized

def list_dishes(filter_query: dict, user_id: str = None):
    safe_query = sanitize_query(filter_query)
    docs = list(db.dishes.find(safe_query).limit(100))
```

**Estimated Effort**: 1 hour

---

#### Issue #5: Unvalidated File Upload
**Impact**: Disk exhaustion, malicious files
**File**: [services/restaurant_service.py:38-65](app/services/restaurant_service.py#L38-L65)

**Solution**:
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["text/csv", "application/vnd.ms-excel"]

async def validate_csv_upload(file: UploadFile):
    """Validate uploaded CSV file."""
    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise BadRequestException("Only CSV files allowed")

    # Check file size
    size = 0
    file.file.seek(0)
    while chunk := await file.read(8192):
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise BadRequestException("File too large (max 10MB)")
    file.file.seek(0)
    return True

@router.post("/")
async def create_restaurant(
    restaurant: RestaurantCreate,
    menu_csv: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    await validate_csv_upload(menu_csv)
    # ... rest of logic
```

**Estimated Effort**: 1 hour

---

### Priority 3: Performance - Database Indexes

#### Issue #6: Missing Critical Database Indexes
**Impact**: Slow queries as data grows
**File**: [create_indexes.py:10-13](app/create_indexes.py#L10-L13)

**Current Issues**:
1. Index uses `"restaurant"` field but code uses `"restaurant_id"`
2. Missing indexes for common query patterns

**Solution**:
```python
def create_indexes():
    """Create all required database indexes."""
    db = get_db()

    # Users
    db.users.create_index("username", unique=True)
    db.users.create_index("email", unique=True, sparse=True)

    # Dishes - FIX: restaurant_id not restaurant
    db.dishes.create_index("restaurant_id")
    db.dishes.create_index("availability")
    db.dishes.create_index([("restaurant_id", 1), ("name", 1)], unique=True)
    db.dishes.create_index([("restaurant_id", 1), ("availability", 1)])

    # Restaurants
    db.restaurants.create_index("name")

    # Chat sessions
    db.sessions.create_index([("user_id", 1), ("restaurant_id", 1)])
    db.sessions.create_index([("user_id", 1), ("restaurant_id", 1), ("active", 1)])

    # Chat states
    db.chat_states.create_index("session_id")
    db.chat_states.create_index([("session_id", 1), ("timestamp", -1)])
    db.chat_states.create_index([("user_id", 1), ("restaurant_id", 1)])

    logger.info("All database indexes created successfully")
```

**Estimated Effort**: 30 minutes

---

## ⚡ High Priority (Fix This Sprint)

### Code Quality Issues

#### Issue #7: Duplicate Code - FAISS Services
**Impact**: Maintenance burden, inconsistent behavior
**Files**:
- [utils/faiss_index.py](app/utils/faiss_index.py) (327 lines)
- [services/faiss_service.py](app/services/faiss_service.py) (353 lines)

**Solution**:
1. Keep `services/faiss_service.py` (better error handling)
2. Delete `utils/faiss_index.py`
3. Update all imports

**Estimated Effort**: 1 hour

---

#### Issue #8: Replace Print Statements with Logging
**Impact**: Cannot control log levels in production
**Count**: 47 instances across multiple files

**Files**:
- `dish_service.py`: 7 instances
- `restaurant_service.py`: 11 instances
- `state_service.py`: 2 instances
- `utils/faiss_index.py`: 15+ instances

**Solution**:
```bash
# Find all print statements
grep -rn "print(" app/services/

# Replace pattern:
# print(f"Debug info: {var}") → logger.debug(f"Debug info: {var}")
# print("Important event") → logger.info("Important event")
```

**Estimated Effort**: 1 hour

---

#### Issue #9: Bare Exception Handling
**Impact**: Masks specific errors, makes debugging difficult
**Count**: 44 instances of `except Exception as e:`

**Solution Pattern**:
```python
# Before
try:
    result = db.users.insert_one(doc)
except Exception as e:
    raise DatabaseException(f"Failed: {e}")

# After
try:
    result = db.users.insert_one(doc)
except PyMongoError as e:
    logger.error(f"Database error creating user: {e}")
    raise DatabaseException(f"Failed to create user: {e}")
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    raise BadRequestException(str(e))
except Exception as e:
    logger.exception("Unexpected error creating user")
    raise GenericException(f"Unexpected error: {e}")
```

**Files to Update**:
- `user_service.py` (4 instances)
- `dish_service.py` (7 instances)
- `restaurant_service.py` (11 instances)
- `faiss_service.py` (6 instances)

**Estimated Effort**: 3 hours

---

#### Issue #10: Missing Input Validation
**Impact**: Data integrity issues, potential security risks

**Examples**:

1. **User Update** - `user_service.py:177`
```python
ALLOWED_UPDATE_FIELDS = {"name", "allergen_preferences"}

def update_user(user_id: str, update_data: dict):
    if not update_data:
        raise BadRequestException("No fields to update")

    # Validate only allowed fields
    invalid_fields = set(update_data.keys()) - ALLOWED_UPDATE_FIELDS
    if invalid_fields:
        raise BadRequestException(f"Cannot update fields: {invalid_fields}")

    # Validate allergen_preferences format
    if "allergen_preferences" in update_data:
        if not isinstance(update_data["allergen_preferences"], list):
            raise BadRequestException("allergen_preferences must be a list")

    # ... proceed with update
```

2. **Dish Filtering** - `dish_service.py:106`
```python
def list_dishes(filter_query: dict, user_id: str = None):
    # Validate user_id format
    if user_id:
        try:
            ObjectId(user_id)
        except:
            raise BadRequestException("Invalid user_id format")
    # ...
```

**Estimated Effort**: 2 hours

---

### Performance Improvements

#### Issue #11: MongoDB Connection Pooling
**Impact**: Connection exhaustion under load
**File**: [db.py:12](app/db.py#L12)

**Current**:
```python
client = MongoClient(MONGO_URI)
```

**Solution**:
```python
client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000,
    connectTimeoutMS=5000,
    serverSelectionTimeoutMS=5000,
    retryWrites=True,
    w='majority'
)

# Add connection verification
try:
    client.admin.command('ping')
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise
```

**Estimated Effort**: 30 minutes

---

#### Issue #12: Async File I/O
**Impact**: Blocking async endpoints
**File**: [services/restaurant_service.py:60-65](app/services/restaurant_service.py#L60-L65)

**Solution**:
```bash
pip install aiofiles
```

```python
import aiofiles

async def create_restaurant(restaurant: RestaurantCreate, menu_csv, background_tasks):
    # ...
    file_path = os.path.join(tmp_dir, f"{result.inserted_id}_menu.csv")
    contents = await menu_csv.read()

    # Use async file I/O
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    background_tasks.add_task(process_menu_file, file_path, str(result.inserted_id))
```

**Estimated Effort**: 30 minutes

---

#### Issue #13: Inefficient FAISS Vector Reconstruction
**Impact**: Unnecessary computation in search results
**File**: [services/faiss_service.py:261](app/services/faiss_service.py#L261)

**Current**:
```python
structured_res.append(DishHit(
    dish = dish,
    score = score,
    embedding = vector_store.index.reconstruct(res.metadata["vector_id"])  # Expensive!
))
```

**Solution**:
```python
# Only reconstruct when needed for centroid refinement
structured_res.append(DishHit(
    dish = dish,
    score = score,
    embedding = None  # Don't reconstruct yet
))

# In refine_with_centroid, reconstruct only when needed
def refine_with_centroid(dish_hits, positive_intents, vector_store):
    centroid = np.mean([embeddings.embed_query(intent) for intent in positive_intents], axis=0)
    refined = []
    for hit in dish_hits:
        # Reconstruct on-demand
        if hit.embedding is None:
            hit.embedding = vector_store.index.reconstruct(hit.dish["vector_id"])
        # ... rest of logic
```

**Estimated Effort**: 1 hour

---

## 🎯 Medium Priority (Next Sprint)

### Architecture Improvements

#### Issue #14: Implement Repository Pattern
**Impact**: Better testability, easier to switch databases

**Create**: `app/repositories/`

**Example - User Repository**:
```python
# repositories/user_repository.py
from typing import Optional, List
from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    def find_by_username(self, username: str) -> Optional[dict]:
        pass

    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def create(self, user_data: dict) -> str:
        pass

    @abstractmethod
    def update(self, user_id: str, update_data: dict) -> bool:
        pass

class MongoUserRepository(UserRepository):
    def __init__(self, db):
        self.collection = db.users

    def find_by_username(self, username: str) -> Optional[dict]:
        return self.collection.find_one({"username": username})

    # ... implement other methods

# In services
def create_user(user_create: UserCreate, repo: UserRepository = Depends(get_user_repo)):
    existing = repo.find_by_username(user_create.username)
    if existing:
        raise ConflictException("Username already exists")
    # ...
```

**Estimated Effort**: 8-10 hours (for all repositories)

---

#### Issue #15: Break Up God Object - ChatState
**Impact**: Better maintainability, clearer responsibilities
**File**: [flow/state.py:24-101](app/flow/state.py#L24-L101)

**Current**: 14 fields in one class

**Solution**:
```python
class UserContext(BaseModel):
    user_id: str
    session_id: str
    restaurant_id: str

class QueryState(BaseModel):
    query: str
    intents: Optional[IntentExtractionResult] = None
    query_parts: Optional[Dict[str, Any]] = None

class ResultState(BaseModel):
    menu_results: Optional[MenuResultResponse] = None
    info_results: Optional[DishInfoResult] = None

class ConversationContext(BaseModel):
    previous_messages: List[Dict[str, Any]] = []
    current_context: str = ""

class ChatState(BaseModel):
    user_context: UserContext
    query_state: QueryState
    results: ResultState
    conversation: ConversationContext
    response: str = ""
    status: str = "pending"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**Estimated Effort**: 4 hours

---

#### Issue #16: Add Caching Layer
**Impact**: Reduce LLM costs, improve response times

**Install**:
```bash
pip install redis
```

**Implementation**:
```python
# utils/cache.py
from redis import Redis
from functools import wraps
import json
import hashlib

redis_client = Redis(host='localhost', port=6379, decode_responses=True)

def cache_result(ttl=3600, prefix=""):
    """Decorator to cache function results in Redis."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_data = f"{prefix}:{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached)

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))
            logger.debug(f"Cache set: {cache_key}")

            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=1800, prefix="user_allergens")
def get_user_allergen_preferences(user_id: str) -> List[str]:
    user = db.users.find_one({"_id": ObjectId(user_id)})
    return user.get("allergen_preferences", [])

@cache_result(ttl=300, prefix="intent")
def extract_query_intent(query: str) -> QueryIntent:
    # LLM call here - results cached for 5 minutes
    # ...
```

**Estimated Effort**: 3 hours

---

### Testing Improvements

#### Issue #17: Increase Test Coverage to 70%+
**Current**: Limited coverage, many services untested

**Priority Areas**:
1. **FAISS Service** (0% coverage, 350+ lines)
2. **Intent Service** (0% coverage)
3. **Context Resolver** (0% coverage)
4. **Retrieval Service** (0% coverage)

**Example - FAISS Service Tests**:
```python
# tests/unit/test_faiss_service.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.faiss_service import (
    extract_query_intent,
    search_dishes,
    semantic_retrieve_with_negation,
    build_faiss_from_db
)

class TestIntentExtraction:
    @patch('app.services.faiss_service.llm')
    def test_extract_positive_and_negative_intents(self, mock_llm):
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"positive": ["pasta"], "negative": ["nuts"]}'
        mock_llm.invoke.return_value = mock_response

        result = extract_query_intent("pasta without nuts")

        assert "pasta" in result.positive
        assert "nuts" in result.negative

    @patch('app.services.faiss_service.llm')
    def test_extract_intent_handles_invalid_json(self, mock_llm):
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.content = 'invalid json'
        mock_llm.invoke.return_value = mock_response

        result = extract_query_intent("test query")

        # Should fallback gracefully
        assert result.positive == ["test query"]
        assert result.negative == []

class TestFAISSSearch:
    @pytest.fixture
    def mock_vector_store(self):
        with patch('app.services.faiss_service.FAISS.load_local') as mock_load:
            mock_store = Mock()
            mock_store.similarity_search_with_score.return_value = [
                (Mock(metadata={"dish_id": "dish_1", "vector_id": 0}), 0.9)
            ]
            mock_load.return_value = mock_store
            yield mock_store

    def test_search_dishes_returns_results(self, mock_vector_store, monkeypatch):
        # Mock database
        mock_dish = {"_id": "dish_1", "name": "Test Dish"}
        monkeypatch.setattr("app.services.faiss_service.dish_collection.find_one",
                           lambda x: mock_dish)

        results = search_dishes("chocolate", threshold=0.8)

        assert len(results) == 1
        assert results[0].dish["name"] == "Test Dish"

    def test_search_dishes_filters_by_threshold(self, mock_vector_store):
        # Score 0.9 > threshold 0.95 should be filtered out
        results = search_dishes("chocolate", threshold=0.95)

        assert len(results) == 0

# Run tests
# pytest tests/unit/test_faiss_service.py -v --cov=app/services/faiss_service
```

**Estimated Effort**: 12-16 hours for comprehensive test suite

---

#### Issue #18: Add Integration Tests
**Missing**: End-to-end flow tests

**Example**:
```python
# tests/integration/test_chat_flow.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_token(client):
    # Create user and get token
    client.post("/users/signup", json={
        "username": "testuser",
        "password": "testpass123",
        "name": "Test User",
        "allergen_preferences": ["peanuts"]
    })
    response = client.post("/users/login?username=testuser&password=testpass123")
    return response.json()["access_token"]

def test_full_chat_flow(client, auth_token):
    """Test complete conversation flow from query to response."""
    # Create restaurant with dishes
    restaurant_response = client.post("/restaurants/", json={
        "name": "Test Restaurant",
        "cuisine": ["Italian"]
    })
    restaurant_id = restaurant_response.json()["_id"]

    # Perform chat search
    response = client.post(
        "/restaurants/search",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "user_id": "...",
            "restaurant_id": restaurant_id,
            "query": "Show me nut-free pasta"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "menu_results" in data
    assert "response" in data

    # Verify allergen filtering worked
    for dish in data["menu_results"]:
        allergens = [a["allergen"] for a in dish.get("inferred_allergens", [])]
        assert "peanuts" not in allergens
```

**Estimated Effort**: 6-8 hours

---

## 📚 Documentation Improvements

#### Issue #19: Add Comprehensive API Documentation
**Impact**: Better developer experience

**Solution**: Add detailed docstrings with examples

```python
@router.post("/signup", response_model=UserOut)
def signup(payload: UserCreate):
    """
    Register a new user account.

    Creates a new user with hashed password and optional allergen preferences.
    Usernames must be unique across the system.

    Args:
        payload: User registration data
            - username: 3-72 characters, unique
            - password: 3-72 characters (will be bcrypt hashed)
            - name: User's display name
            - allergen_preferences: Optional list of allergens to avoid

    Returns:
        UserOut: Created user object (excluding password)

    Raises:
        409 Conflict: Username already exists
        400 Bad Request: Invalid input data
        500 Internal Server Error: Database error

    Example Request:
        ```json
        {
            "username": "john_doe",
            "password": "secure123",
            "name": "John Doe",
            "allergen_preferences": ["peanuts", "shellfish"]
        }
        ```

    Example Response:
        ```json
        {
            "_id": "507f1f77bcf86cd799439011",
            "username": "john_doe",
            "name": "John Doe",
            "allergen_preferences": ["peanuts", "shellfish"]
        }
        ```

    Notes:
        - Password is hashed using bcrypt before storage
        - Passwords longer than 72 chars are truncated (bcrypt limitation)
        - Allergen preferences can be updated later via PUT /users/me
    """
    return user_service.create_user(payload)
```

**Estimated Effort**: 4 hours

---

## 🔧 Additional Improvements

### Issue #20: Add Rate Limiting
**File**: Create `app/middleware/rate_limit.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# In main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In routers
@router.post("/search")
@limiter.limit("10/minute")  # Expensive LLM operations
async def chat_search(request: Request, payload: ChatQuery):
    ...

@router.post("/signup")
@limiter.limit("5/hour")  # Prevent spam accounts
async def signup(request: Request, payload: UserCreate):
    ...
```

**Estimated Effort**: 2 hours

---

### Issue #21: Add Health Check Endpoint
**File**: [main.py](app/main.py)

```python
@app.get("/health", tags=["monitoring"])
async def health_check():
    """
    System health check endpoint.

    Verifies:
    - Database connectivity
    - FAISS index availability
    - OpenAI API key validity

    Returns:
        Health status and individual component checks
    """
    checks = {}

    # Database check
    try:
        db.client.admin.command('ping')
        checks["database"] = {"status": "healthy", "latency_ms": "..."}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # FAISS index check
    checks["faiss_index"] = {
        "status": "healthy" if os.path.exists("faiss_index_restaurant") else "missing"
    }

    # OpenAI API check
    try:
        # Quick test call
        embeddings.embed_query("test")
        checks["openai_api"] = {"status": "healthy"}
    except Exception as e:
        checks["openai_api"] = {"status": "unhealthy", "error": str(e)}

    overall_status = "healthy" if all(
        c.get("status") == "healthy" for c in checks.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": "1.0.0"
    }
```

**Estimated Effort**: 1 hour

---

### Issue #22: Add Pagination Support
**Impact**: Better UX for large datasets

```python
# models/pagination_model.py
from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')

class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 50

    def validate(self):
        if self.limit > 100:
            raise BadRequestException("Limit cannot exceed 100")
        if self.skip < 0:
            raise BadRequestException("Skip must be non-negative")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool

    @classmethod
    def create(cls, items: List[T], total: int, skip: int, limit: int):
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items)) < total
        )

# Usage in router
@router.get("/dishes", response_model=PaginatedResponse[DishOut])
def list_dishes(
    pagination: PaginationParams = Depends(),
    restaurant_id: Optional[str] = None
):
    pagination.validate()

    query = {"restaurant_id": restaurant_id} if restaurant_id else {}
    total = db.dishes.count_documents(query)
    docs = list(db.dishes.find(query).skip(pagination.skip).limit(pagination.limit))

    return PaginatedResponse.create(
        items=[DishOut(**doc) for doc in docs],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit
    )
```

**Estimated Effort**: 3 hours

---

### Issue #23: Add Audit Logging
**Impact**: Compliance, debugging, security

```python
# services/audit_service.py
from datetime import datetime
from enum import Enum

class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    SEARCH = "SEARCH"

def audit_log(
    user_id: str,
    action: AuditAction,
    resource: str,
    resource_id: str,
    details: dict = None,
    ip_address: str = None
):
    """Log an audit event."""
    db.audit_log.insert_one({
        "user_id": user_id,
        "action": action.value,
        "resource": resource,  # "dish", "user", "restaurant"
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address,
        "timestamp": datetime.utcnow()
    })

# Usage
def delete_dish(dish_id: str, current_user: str = Depends(get_current_user)):
    dish = db.dishes.find_one({"_id": ObjectId(dish_id)})
    if not dish:
        raise NotFoundException("Dish not found")

    db.dishes.delete_one({"_id": ObjectId(dish_id)})

    # Audit log
    audit_log(
        user_id=current_user["_id"],
        action=AuditAction.DELETE,
        resource="dish",
        resource_id=dish_id,
        details={"dish_name": dish.get("name")}
    )
```

**Estimated Effort**: 2-3 hours

---

## 📊 Sprint Planning

### Sprint 1: Critical Fixes (1 week)
- [ ] Fix "availaibility" typo
- [ ] Implement proper JWT authentication
- [ ] Remove hardcoded user ID
- [ ] Add database indexes
- [ ] Add file upload validation
- [ ] Implement NoSQL injection protection

**Total Effort**: ~8-10 hours

---

### Sprint 2: Code Quality (1 week)
- [ ] Remove duplicate FAISS code
- [ ] Replace print() with logging
- [ ] Improve exception handling
- [ ] Add input validation
- [ ] Remove unused imports
- [ ] Add connection pooling

**Total Effort**: ~10-12 hours

---

### Sprint 3: Performance & Architecture (2 weeks)
- [ ] Implement repository pattern
- [ ] Add caching layer (Redis)
- [ ] Break up ChatState god object
- [ ] Optimize FAISS operations
- [ ] Add async file I/O
- [ ] Add pagination

**Total Effort**: ~25-30 hours

---

### Sprint 4: Testing & Documentation (2 weeks)
- [ ] Write FAISS service tests
- [ ] Write integration tests
- [ ] Achieve 70%+ coverage
- [ ] Add comprehensive API docs
- [ ] Add health check endpoint
- [ ] Add rate limiting

**Total Effort**: ~25-30 hours

---

### Sprint 5: Advanced Features (1-2 weeks)
- [ ] Implement audit logging
- [ ] Add background job management (Celery)
- [ ] Improve error messages
- [ ] Add monitoring/observability
- [ ] Performance profiling

**Total Effort**: ~15-20 hours

---

## 🛠️ Recommended Tools

### Development Tools
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Code quality
pip install ruff black mypy isort

# Testing
pip install pytest pytest-cov pytest-mock pytest-asyncio pytest-benchmark

# Security
pip install bandit safety

# Performance
pip install py-spy memory-profiler
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/psf/black
    rev: 23.10.0
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']
```

---

## 📈 Success Metrics

Track improvements with:

- **Code Coverage**: Target 70%+ (currently ~30%)
- **Security Score**: Bandit score improvement
- **Performance**: Response time < 500ms for 95th percentile
- **Code Quality**: Ruff/Mypy warnings reduced to 0
- **Test Count**: 100+ tests across unit/integration

---

## 🎯 Quick Wins (Do First!)

These can be done in < 1 hour each:

1. ✅ Fix "availaibility" typo
2. ✅ Add database indexes
3. ✅ Add connection pooling
4. ✅ Add health check endpoint
5. ✅ Remove duplicate FAISS file
6. ✅ Add file size validation
7. ✅ Replace print with logging

**Total Time**: ~5-6 hours for immediate impact

---

## Conclusion

This roadmap prioritizes **80+ improvements** based on impact and effort. Focus on:

1. **Week 1**: Security & critical bugs
2. **Week 2-3**: Code quality & performance
3. **Week 4-5**: Architecture & testing
4. **Week 6+**: Advanced features

Following this roadmap will transform SafeBites into a production-ready, maintainable, and secure application.
