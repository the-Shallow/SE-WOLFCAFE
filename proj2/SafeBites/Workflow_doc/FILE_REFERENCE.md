# SafeBites File Reference Guide

Complete list of all key files with their locations and purposes.

---

## 📁 Directory Structure

```
SafeBites/
├── frontend/                           # React Frontend
│   ├── src/
│   │   ├── pages/                      # Page Components
│   │   ├── components/                 # Reusable Components
│   │   ├── config/                     # Configuration
│   │   └── App.tsx                     # Main App Router
│   ├── public/
│   └── package.json
│
├── backend/                            # FastAPI Backend
│   ├── app/
│   │   ├── routers/                    # API Endpoints
│   │   ├── services/                   # Business Logic
│   │   ├── models/                     # Pydantic Models
│   │   ├── flow/                       # LangGraph Pipeline
│   │   ├── utils/                      # Utilities
│   │   └── main.py                     # FastAPI App Entry
│   ├── logs/                           # Log Files
│   ├── requirements.txt
│   └── .env
│
├── docs/                               # Documentation
└── temp_readme/                        # Generated Documentation (THIS FOLDER)
```

---

## 🎨 Frontend Files

### Core Application

**[/frontend/src/App.tsx](../frontend/src/App.tsx)**
- Main React Router setup
- Route definitions for all pages
- Layout structure

### Pages

**[/frontend/src/pages/SearchChat.tsx](../frontend/src/pages/SearchChat.tsx)** ⭐ MAIN CHAT UI
- Lines 74-116: `handleSendMessage()` - Sends POST to `/restaurants/search`
- Lines 146-252: Response processing and rendering
- Lines 343-404: Dish card rendering
- **Purpose**: Main search/chat interface where users interact with the system

**[/frontend/src/pages/Welcome.tsx](../frontend/src/pages/Welcome.tsx)**
- Landing page
- App introduction

**[/frontend/src/pages/Login.tsx](../frontend/src/pages/Login.tsx)**
- User authentication
- POST to `/users/login`

**[/frontend/src/pages/SignUp.tsx](../frontend/src/pages/SignUp.tsx)**
- User registration
- POST to `/users/register`

**[/frontend/src/pages/Dashboard.tsx](../frontend/src/pages/Dashboard.tsx)**
- Restaurant listing
- GET from `/restaurants/`

**[/frontend/src/pages/Home.tsx](../frontend/src/pages/Home.tsx)**
- User home page after login

**[/frontend/src/pages/Settings.tsx](../frontend/src/pages/Settings.tsx)**
- User profile and allergen preferences
- PATCH to `/users/{user_id}/allergens`

**[/frontend/src/pages/RestaurantDetails.tsx](../frontend/src/pages/RestaurantDetails.tsx)**
- Individual restaurant information
- GET from `/restaurants/{restaurant_id}`

### Configuration

**[/frontend/src/config/api.ts](../frontend/src/config/api.ts)**
```typescript
export const API_BASE_URL = 'http://localhost:8000' || 'https://your-render-url.com'
```
- Centralized API endpoint configuration

### Styling

**[/frontend/src/pages/SearchChat.css](../frontend/src/pages/SearchChat.css)**
- Styles for chat interface
- Message bubbles, dish cards, allergen tags

---

## 🔧 Backend Files

### Main Entry Point

**[/backend/app/main.py](../backend/app/main.py)**
- FastAPI application initialization
- CORS middleware setup
- Router registration
- Database connection
- Startup events (FAISS index building)

### API Routers

**[/backend/app/routers/restaurant_router.py](../backend/app/routers/restaurant_router.py)** ⭐ MAIN SEARCH ENDPOINT
- **Line 70-98**: `chat_search()` - POST `/restaurants/search`
  - Gets/creates session
  - Rebuilds context
  - Invokes LangGraph pipeline
  - Saves state
  - Returns results
- **Line 100-108**: `chat_history()` - GET `/history/{user_id}/{restaurant_id}`
- **Line 31-51**: `create_restaurant()` - POST `/restaurants/`
- **Line 53-63**: `list_restaurants()` - GET `/restaurants/`
- **Line 110-124**: `get_restaurant()` - GET `/restaurants/{restaurant_id}`
- **Line 126-140**: `update_restaurant()` - PATCH `/restaurants/{restaurant_id}`
- **Line 142-156**: `delete_restaurant()` - DELETE `/restaurants/{restaurant_id}`

**[/backend/app/routers/user_router.py](../backend/app/routers/user_router.py)**
- POST `/register` - User registration
- POST `/login` - User authentication
- PATCH `/{user_id}/allergens` - Update allergen preferences
- GET `/{user_id}` - Get user profile

**[/backend/app/routers/admin_router.py](../backend/app/routers/admin_router.py)**
- Admin management endpoints

### Services (Business Logic)

**[/backend/app/services/state_service.py](../backend/app/services/state_service.py)** ⭐ SESSION MANAGEMENT
- **Line 15-35**: `get_or_create_session(user_id, restaurant_id)` → Returns session_id
- **Line 45-85**: `rebuild_context(session_id, user_id)` → Returns context array
  - Fetches user allergen preferences
  - Fetches last 5 chat states
- **Line 90-110**: `save_chat_state(state)` → Saves to MongoDB
- **Line 115-135**: `get_chat_history(session_id)` → Returns chat history

**[/backend/app/services/context_resolver.py](../backend/app/services/context_resolver.py)** ⭐ QUERY REWRITING
- **Line 65-100**: `resolve_context(state: ChatState)` → Rewrites query with context
- Calls GPT-4o-mini to make query self-contained
- **Log output**: "Rewritten Query: Show me dishes under $20 that are peanut-free."

**[/backend/app/services/intent_service.py](../backend/app/services/intent_service.py)** ⭐ INTENT CLASSIFICATION
- **Line 20-60**: `classify_intent(state: ChatState)` → Classifies into intent types
- Returns: `{menu_search: [], dish_info: [], user_preferences: [], irrelevant: []}`
- Calls GPT-4o-mini for classification

**[/backend/app/services/retrieval_service.py](../backend/app/services/retrieval_service.py)** ⭐ CORE SEARCH LOGIC
- **Line 85-150**: `retrieve_menu(state: ChatState)` → Main menu search function
- **Line 160-200**: `generate_search_terms(query, context)` → GPT-4o-mini generates terms
- **Line 210-250**: `extract_structured_filters(query, context)` → GPT-4o-mini extracts filters
- **Line 260-300**: `filter_dishes_with_llm(dishes, filters, query)` → GPT-4o-mini filters dishes
- **Multi-stage process**:
  1. Generate search terms
  2. Vector search with FAISS
  3. Extract structured filters
  4. LLM-based filtering

**[/backend/app/services/faiss_service.py](../backend/app/services/faiss_service.py)** ⭐ VECTOR SEARCH
- **Line 45-80**: `vector_search(query, restaurant_id, k=10)` → FAISS similarity search
- **Line 90-130**: `build_index(restaurant_id)` → Build FAISS index from dishes
- **Line 140-160**: `get_openai_embedding(text)` → Get embedding from OpenAI
- **In-memory indexes** per restaurant

**[/backend/app/services/dish_info_service.py](../backend/app/services/dish_info_service.py)**
- **Line 30-70**: `retrieve_info(state: ChatState)` → Get detailed dish information
- Handles queries like "Tell me about dish 27606"
- Fetches from MongoDB dishes collection

**[/backend/app/services/user_preferences_service.py](../backend/app/services/user_preferences_service.py)**
- **Line 25-60**: `retrieve_preferences(state: ChatState)` → Get user preferences
- Handles queries like "What am I allergic to?"
- Fetches from MongoDB users collection

**[/backend/app/services/response_synthesizer_tool.py](../backend/app/services/response_synthesizer_tool.py)** ⭐ RESPONSE AGGREGATION
- **Line 18-80**: `format_response(state: ChatState)` → Aggregate all results
- Combines menu_results, info_results, preference_results
- Generates final response text
- Sets status (success/failed)

**[/backend/app/services/restaurant_service.py](../backend/app/services/restaurant_service.py)**
- CRUD operations for restaurants
- Menu CSV upload handling
- Calls faiss_service to build indexes

**[/backend/app/services/user_service.py](../backend/app/services/user_service.py)**
- User CRUD operations
- Password hashing with bcrypt
- JWT token generation

### LangGraph Flow

**[/backend/app/flow/graph.py](../backend/app/flow/graph.py)** ⭐ PIPELINE DEFINITION
- **Line 12-60**: `create_chat_graph()` → Creates LangGraph StateGraph
- **7 Nodes**:
  1. context_resolver
  2. intent_classifier
  3. query_part_generator
  4. menu_retriever
  5. info_retriever
  6. preferences_retriever
  7. response_formatter
- **Sequential edges** connecting all nodes
- Returns compiled graph

**[/backend/app/flow/state.py](../backend/app/flow/state.py)** ⭐ STATE MODEL
```python
class ChatState(TypedDict):
    user_id: str
    session_id: str
    restaurant_id: str
    query: str
    intents: dict
    context: list
    current_context: str
    query_parts: dict
    menu_results: dict
    info_results: dict
    preference_results: dict
    data: dict
    response: str
    status: str
```

### Models (Pydantic)

**[/backend/app/models/restaurant_model.py](../backend/app/models/restaurant_model.py)**
```python
class RestaurantCreate(BaseModel):
    name: str
    location: str
    cuisine: List[str]
    rating: float

class RestaurantInDB(RestaurantCreate):
    id: str
```

**[/backend/app/models/user_model.py](../backend/app/models/user_model.py)**
```python
class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    allergen_preferences: List[str] = []

class UserInDB(UserCreate):
    id: str
```

**[/backend/app/models/dish_model.py](../backend/app/models/dish_model.py)**
```python
class DishData(BaseModel):
    dish_id: str
    dish_name: str
    description: str
    price: float
    ingredients: List[str]
    allergens: List[str]
    nutrition_facts: dict
    serving_size: Optional[str]
    embedding: List[float]  # 1536 dimensions
```

### Utilities

**[/backend/app/utils/llm_tracker.py](../backend/app/utils/llm_tracker.py)**
- Tracks LLM API usage
- Logs to `logs/llm_usage.csv`
- **Format**: timestamp, model, input_tokens, output_tokens, cost

**[/backend/app/utils/database.py](../backend/app/utils/database.py)**
- MongoDB connection setup
- Collection references:
  - `users_collection`
  - `restaurants_collection`
  - `dishes_collection`
  - `chat_states_collection`

### Configuration

**[/backend/app/config.py](../backend/app/config.py)**
```python
MONGODB_URI = os.getenv("MONGODB_URI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
```

**[/backend/.env](../backend/.env)**
```
MONGODB_URI=mongodb+srv://...
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-key
```

**[/backend/requirements.txt](../backend/requirements.txt)**
```
fastapi==0.104.1
uvicorn==0.24.0
pymongo==4.5.0
langchain==0.1.0
langgraph==0.0.20
openai==1.3.0
faiss-cpu==1.7.4
bcrypt==4.1.1
pydantic==2.5.0
python-dotenv==1.0.0
```

### Logs

**[/backend/logs/llm_usage.csv](../backend/logs/llm_usage.csv)**
- LLM API call tracking
- Columns: timestamp, model, input_tokens, output_tokens, cost

**[/backend/intent_dishes_log.json](../backend/intent_dishes_log.json)**
- Logs of intent classification and dish results
- Used for debugging and analysis

---

## 📊 Database Schema

### MongoDB Collections

**users**
```json
{
  "_id": ObjectId("692e0fdb05007b7686f86c02"),
  "name": "Samarth Shah",
  "username": "S1",
  "password": "$2b$12$RFEcKCvwi2PlA2rBJ1eZpu...",
  "allergen_preferences": ["Peanuts"]
}
```

**restaurants**
```json
{
  "_id": "rest_1",
  "name": "Pizza Express",
  "location": "Downtown",
  "cuisine": ["Italian", "Pizza"],
  "rating": 4.5
}
```

**dishes**
```json
{
  "_id": "dish_14",
  "restaurant_id": "rest_1",
  "dish_name": "Margherita Pizza",
  "description": "Classic pizza with tomato sauce and mozzarella",
  "price": 15.99,
  "ingredients": ["flour", "tomato", "mozzarella", "basil"],
  "allergens": ["dairy", "gluten"],
  "nutrition_facts": {
    "calories": {"value": 750, "confidence": 0.95},
    "protein": {"value": 28, "confidence": 0.90},
    "fat": {"value": 25, "confidence": 0.85},
    "carbohydrates": {"value": 95, "confidence": 0.88}
  },
  "serving_size": "12 inch",
  "embedding": [0.123, -0.456, 0.789, ...]  // 1536 dimensions
}
```

**chat_states**
```json
{
  "_id": ObjectId("692e578fc25a56ab036be4d6"),
  "user_id": "692e0fdb05007b7686f86c02",
  "session_id": "sess_794b1625a0",
  "restaurant_id": "rest_1",
  "query": "Show me dishes under $20 that are peanut-free",
  "intents": {
    "menu_search": ["Show me dishes under $20 that are peanut-free"],
    "dish_info": [],
    "user_preferences": [],
    "irrelevant": []
  },
  "context": [
    {
      "user_allergens": ["Peanuts"],
      "message": "User is allergic to: Peanuts"
    },
    {
      "query": "show me pizza dishes under $20",
      "menu_results": {...}
    }
  ],
  "current_context": "User is allergic to peanuts...",
  "query_parts": {
    "menu_search": ["Show me dishes under $20 that are peanut-free"],
    "dish_info": [],
    "user_preferences": []
  },
  "menu_results": {
    "Show me dishes under $20 that are peanut-free": [
      {
        "dish_id": "dish_14",
        "dish_name": "Margherita Pizza",
        ...
      }
    ]
  },
  "info_results": {"info_results": {}},
  "preference_results": {"preference_results": {}},
  "response": "I found 1 dish matching your search!",
  "status": "success",
  "timestamp": "2025-12-02T03:04:41.955781+00:00"
}
```

---

## 🔍 Key Code Locations

### User Input → Backend

**Frontend**: [SearchChat.tsx:74-116](../frontend/src/pages/SearchChat.tsx#L74-L116)
```typescript
const response = await fetch(`${API_BASE_URL}/restaurants/search`, {
  method: 'POST',
  body: JSON.stringify({ query, user_id, restaurant_id })
});
```

**Backend**: [restaurant_router.py:70-98](../backend/app/routers/restaurant_router.py#L70-L98)
```python
@router.post("/search")
async def chat_search(payload: ChatQuery):
    final_state = chat_graph.invoke(state)
    return JSONResponse(content=final_state)
```

### Session Management

**Get/Create Session**: [state_service.py:15-35](../backend/app/services/state_service.py#L15-L35)
**Rebuild Context**: [state_service.py:45-85](../backend/app/services/state_service.py#L45-L85)
**Save State**: [state_service.py:90-110](../backend/app/services/state_service.py#L90-L110)

### LangGraph Pipeline

**Graph Definition**: [graph.py:12-60](../backend/app/flow/graph.py#L12-L60)
**State Model**: [state.py:1-30](../backend/app/flow/state.py#L1-L30)

### Search Logic

**Menu Retrieval**: [retrieval_service.py:85-150](../backend/app/services/retrieval_service.py#L85-L150)
**Vector Search**: [faiss_service.py:45-80](../backend/app/services/faiss_service.py#L45-L80)
**LLM Filtering**: [retrieval_service.py:260-300](../backend/app/services/retrieval_service.py#L260-L300)

### Response Rendering

**Backend**: [response_synthesizer_tool.py:18-80](../backend/app/services/response_synthesizer_tool.py#L18-L80)
**Frontend**: [SearchChat.tsx:146-252](../frontend/src/pages/SearchChat.tsx#L146-L252)

---

## 🚀 How to Navigate the Codebase

### Tracing a Search Query

1. **Start**: [SearchChat.tsx:74](../frontend/src/pages/SearchChat.tsx#L74) - User clicks "Send"
2. **API Entry**: [restaurant_router.py:70](../backend/app/routers/restaurant_router.py#L70) - `/search` endpoint
3. **Session**: [state_service.py:15](../backend/app/services/state_service.py#L15) - Get/create session
4. **Context**: [state_service.py:45](../backend/app/services/state_service.py#L45) - Rebuild history
5. **Pipeline**: [graph.py:12](../backend/app/flow/graph.py#L12) - LangGraph invocation
6. **Node 1**: [context_resolver.py:65](../backend/app/services/context_resolver.py#L65) - Rewrite query
7. **Node 2**: [intent_service.py:20](../backend/app/services/intent_service.py#L20) - Classify intent
8. **Node 4**: [retrieval_service.py:85](../backend/app/services/retrieval_service.py#L85) - Search dishes
9. **Node 7**: [response_synthesizer_tool.py:18](../backend/app/services/response_synthesizer_tool.py#L18) - Format response
10. **Save**: [state_service.py:90](../backend/app/services/state_service.py#L90) - Save to MongoDB
11. **Return**: [restaurant_router.py:95](../backend/app/routers/restaurant_router.py#L95) - Send JSON
12. **Render**: [SearchChat.tsx:146](../frontend/src/pages/SearchChat.tsx#L146) - Display dishes

### Adding a New Feature

**Frontend**:
1. Create page in `/frontend/src/pages/NewPage.tsx`
2. Add route in `/frontend/src/App.tsx`
3. Add API call using `/frontend/src/config/api.ts`

**Backend**:
1. Define model in `/backend/app/models/new_model.py`
2. Create service in `/backend/app/services/new_service.py`
3. Add router in `/backend/app/routers/new_router.py`
4. Register router in `/backend/app/main.py`

### Debugging

**Frontend**:
- Check browser console for API errors
- Inspect Network tab for request/response

**Backend**:
- Check logs: `backend/logs/llm_usage.csv`
- Check terminal output for errors
- Check MongoDB for saved states

---

**Generated**: 2025-12-02
**Purpose**: Quick reference for file locations and code navigation
