# SafeBites Backend-to-Frontend Workflow

## Complete Request Flow: "Show me dishes under $20 that are peanut-free"

This document traces the complete execution flow from user input in the frontend to the response displayed back to the user.

---

## 📋 Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Detailed Step-by-Step Flow](#detailed-step-by-step-flow)
3. [File Workflow Diagram](#file-workflow-diagram)
4. [Key Components](#key-components)
5. [Data Transformations](#data-transformations)

---

## 🎯 High-Level Overview

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│   Frontend  │─────▶│  API Router  │─────▶│  LangGraph  │─────▶│   MongoDB    │
│ SearchChat  │      │  /search     │      │  Pipeline   │      │   + FAISS    │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────────┘
       ▲                                           │                      │
       │                                           ▼                      │
       │                                    ┌──────────────┐             │
       └────────────────────────────────────│   Response   │◀────────────┘
                                            │  Formatter   │
                                            └──────────────┘
```

**Tech Stack:**
- **Frontend**: React + TypeScript (SearchChat.tsx)
- **Backend**: FastAPI + Python
- **AI**: LangGraph (7-node pipeline) + OpenAI GPT-4o-mini
- **Search**: FAISS (vector similarity) + OpenAI embeddings
- **Database**: MongoDB (users, restaurants, dishes, sessions, chat_states)

---

## 🔄 Detailed Step-by-Step Flow

### **STAGE 1: Frontend User Input**

**File**: `/frontend/src/pages/SearchChat.tsx`

**Lines**: 74-116

```typescript
// User types: "Show me dishes under $20 that are peanut-free"
const handleSendMessage = async () => {
  const requestBody = {
    query: "Show me dishes under $20 that are peanut-free",
    restaurant_id: "rest_1",
    user_id: "692e0fdb05007b7686f86c02"  // From localStorage
  };

  // POST to backend
  const response = await fetch(`${API_BASE_URL}/restaurants/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody)
  });
}
```

**What Happens:**
1. User enters query in textarea
2. Clicks "Send" or presses Enter
3. Creates user message bubble in UI
4. Extracts `user_id` from localStorage (if logged in)
5. Sends POST request to `/restaurants/search`

---

### **STAGE 2: API Router Entry Point**

**File**: `/backend/app/routers/restaurant_router.py`

**Lines**: 70-98

```python
@router.post("/search")
async def chat_search(payload: ChatQuery):
    # Extract request data
    query = payload.query  # "Show me dishes under $20 that are peanut-free"
    user_id = payload.user_id  # "692e0fdb05007b7686f86c02"
    restaurant_id = payload.restaurant_id  # "rest_1"

    # STEP 1: Get or create session
    session_id = state_service.get_or_create_session(user_id, restaurant_id)
    # Returns: "sess_794b1625a0"

    # STEP 2: Rebuild context from chat history
    context = state_service.rebuild_context(session_id, user_id)
    # Returns: Array of previous queries and results for context

    # STEP 3: Create LangGraph pipeline
    chat_graph = create_chat_graph()

    # STEP 4: Initialize state
    state = ChatState(
        user_id=user_id,
        session_id=session_id,
        restaurant_id=restaurant_id,
        query=query,
        context=context,
        query_parts={},
        current_context=""
    )

    # STEP 5: Run the pipeline
    final_state = chat_graph.invoke(state)

    # STEP 6: Save to database
    state_service.save_chat_state(final_state)

    # STEP 7: Return response
    return JSONResponse(content=final_state)
```

**Key Files Involved:**
- `/backend/app/services/state_service.py` - Session and context management
- `/backend/app/flow/graph.py` - LangGraph pipeline definition

---

### **STAGE 3: Session & Context Management**

**File**: `/backend/app/services/state_service.py`

**Function**: `get_or_create_session(user_id, restaurant_id)`

```python
def get_or_create_session(user_id: str, restaurant_id: str) -> str:
    # Check MongoDB for existing session
    existing_session = chat_states_collection.find_one({
        "user_id": user_id,
        "restaurant_id": restaurant_id
    })

    if existing_session:
        return existing_session["session_id"]
    else:
        # Generate new session ID
        session_id = f"sess_{secrets.token_hex(5)}"
        return session_id
```

**Function**: `rebuild_context(session_id, user_id)`

```python
def rebuild_context(session_id: str, user_id: Optional[str]) -> list:
    # Fetch all previous chat states for this session
    chat_history = chat_states_collection.find({
        "session_id": session_id
    }).sort("timestamp", 1).limit(5)  # Last 5 interactions

    context = []

    # Add user allergen preferences if logged in
    if user_id:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user and user.get("allergen_preferences"):
            context.append({
                "user_allergens": user["allergen_preferences"],
                "message": f"User is allergic to: {', '.join(user['allergen_preferences'])}"
            })

    # Add previous queries and results
    for state in chat_history:
        context.append({
            "query": state.get("query"),
            "intents": state.get("intents"),
            "menu_results": state.get("menu_results"),
            "info_results": state.get("info_results")
        })

    return context
```

**Output Example** (from your logs):
```python
context = [
    {
        "user_allergens": ["Peanuts"],
        "message": "User is allergic to: Peanuts"
    },
    {
        "query": "show me pizza dishes under $20",
        "intents": {...},
        "menu_results": {...}
    },
    # ... more previous queries
]
```

---

### **STAGE 4: LangGraph Pipeline (7 Nodes)**

**File**: `/backend/app/flow/graph.py`

```python
def create_chat_graph():
    graph = StateGraph(ChatState)

    # Add 7 sequential nodes
    graph.add_node("context_resolver", resolve_context)
    graph.add_node("intent_classifier", classify_intent)
    graph.add_node("query_part_generator", generate_query_parts)
    graph.add_node("menu_retriever", retrieve_menu)
    graph.add_node("info_retriever", retrieve_info)
    graph.add_node("preferences_retriever", retrieve_preferences)
    graph.add_node("response_formatter", format_response)

    # Define edges (sequential flow)
    graph.set_entry_point("context_resolver")
    graph.add_edge("context_resolver", "intent_classifier")
    graph.add_edge("intent_classifier", "query_part_generator")
    graph.add_edge("query_part_generator", "menu_retriever")
    graph.add_edge("menu_retriever", "info_retriever")
    graph.add_edge("info_retriever", "preferences_retriever")
    graph.add_edge("preferences_retriever", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile()
```

---

### **NODE 1: Context Resolver**

**File**: `/backend/app/services/context_resolver.py`

**Function**: `resolve_context(state: ChatState) -> ChatState`

**Purpose**: Rewrite the query using conversation context to resolve implicit references

**Your Log Output:**
```
2025-12-02 20:50:04,741 | DEBUG | Rewritten Query: Show me dishes under $20 that are peanut-free.
```

**What Happened:**
```python
def resolve_context(state: ChatState) -> ChatState:
    # Build context summary from previous queries
    context_summary = build_context_summary(state.context)
    # Example: "The user has a peanut allergy and previously searched for pizza under $20"

    # Call GPT-4o-mini to rewrite query
    prompt = f"""
    Context: {context_summary}
    User Query: {state.query}

    Rewrite the query to be self-contained, resolving any implicit references.
    """

    response = llm.invoke(prompt)
    rewritten_query = response.content
    # "Show me dishes under $20 that are peanut-free."

    state.query = rewritten_query
    state.current_context = context_summary
    return state
```

**LLM Call**:
- **Model**: gpt-4o-mini
- **Input Tokens**: 852
- **Output Tokens**: 11
- **Output**: "Show me dishes under $20 that are peanut-free."

---

### **NODE 2: Intent Classifier**

**File**: `/backend/app/services/intent_service.py`

**Function**: `classify_intent(state: ChatState) -> ChatState`

**Purpose**: Classify the query into intent types

**Intent Types:**
1. **menu_search** - Search for dishes
2. **dish_info** - Get details about specific dish
3. **user_preferences** - Questions about user's allergens/preferences
4. **irrelevant** - Off-topic queries

**Your Log Output:**
```json
{
  "menu_search": ["Show me dishes under $20 that are peanut-free"],
  "dish_info": [],
  "user_preferences": [],
  "irrelevant": []
}
```

**Code:**
```python
def classify_intent(state: ChatState) -> ChatState:
    prompt = f"""
    Classify this query into categories:
    Query: {state.query}
    Context: {state.current_context}

    Return JSON with arrays for: menu_search, dish_info, user_preferences, irrelevant
    """

    response = llm.invoke(prompt)
    intents = json.loads(response.content)

    state.intents = intents
    return state
```

**LLM Call**:
- **Model**: gpt-4o-mini
- **Input Tokens**: 745
- **Output Tokens**: 41

---

### **NODE 3: Query Part Generator**

**File**: `/backend/app/flow/graph.py` (node function)

**Purpose**: Organize intents into structured query parts

**Code:**
```python
def generate_query_parts(state: ChatState) -> ChatState:
    state.query_parts = {
        "menu_search": state.intents.get("menu_search", []),
        "dish_info": state.intents.get("dish_info", []),
        "user_preferences": state.intents.get("user_preferences", [])
    }
    return state
```

**Output:**
```python
state.query_parts = {
    "menu_search": ["Show me dishes under $20 that are peanut-free"],
    "dish_info": [],
    "user_preferences": []
}
```

---

### **NODE 4: Menu Retriever** 🔍

**File**: `/backend/app/services/retrieval_service.py`

**Function**: `retrieve_menu(state: ChatState) -> ChatState`

**This is the CORE search logic!**

**Your Log Output:**
```
2025-12-02 20:50:08,819 | INFO | Processing 1 menu search queries for restaurant rest_1
```

**Multi-Stage Search Process:**

#### **Stage 4.1: Generate Search Terms**

**Your Log:**
```json
{"positive": ["dishes under $20", "affordable dishes"], "negative": []}
```

**Code:**
```python
def generate_search_terms(query: str, context: str) -> dict:
    prompt = f"""
    Query: {query}
    Context: {context}

    Generate search terms to find relevant dishes.
    Return JSON: {{"positive": [...], "negative": [...]}}
    """

    response = llm.invoke(prompt)
    return json.loads(response.content)
```

**LLM Call**:
- **Model**: gpt-4o-mini
- **Input Tokens**: 712
- **Output Tokens**: 24

#### **Stage 4.2: Vector Search with FAISS**

**File**: `/backend/app/services/faiss_service.py`

```python
def vector_search(query: str, restaurant_id: str, k: int = 10):
    # Get embedding for query
    embedding = get_openai_embedding(query)
    # [0.123, -0.456, 0.789, ...] (1536 dimensions)

    # Load FAISS index for restaurant
    index = faiss_indexes[restaurant_id]

    # Search for similar dishes
    distances, indices = index.search(embedding, k)

    # Retrieve dish documents
    dishes = [dish_documents[idx] for idx in indices]
    return dishes
```

**Your Log:**
```
2025-12-02 20:50:09,827 | INFO | HTTP Request: POST https://api.openai.com/v1/embeddings
2025-12-02 20:50:12,868 | INFO | HTTP Request: POST https://api.openai.com/v1/embeddings
```

**Multiple Embedding Calls:**
1. "dishes under $20" → embedding
2. "affordable dishes" → embedding
3. "Show dishes under $20" → embedding (original query)

#### **Stage 4.3: Extract Structured Filters**

**Your Log Output:**
```json
{
  "price": {"max": 20, "min": 0},
  "ingredients": {"include": [], "exclude": []},
  "allergens": {"exclude": ["peanuts"]},
  "nutrition": {}
}
```

**Code:**
```python
def extract_structured_filters(query: str, context: str) -> dict:
    prompt = f"""
    Query: {query}
    Context: {context}

    Extract structured filters as JSON:
    {{
      "price": {{"max": X, "min": Y}},
      "ingredients": {{"include": [], "exclude": []}},
      "allergens": {{"exclude": []}},
      "nutrition": {{}}
    }}
    """

    response = llm.invoke(prompt)
    return json.loads(response.content)
```

**LLM Call**:
- **Model**: gpt-4o-mini
- **Input Tokens**: 1568 (1024 cached)
- **Output Tokens**: 49

#### **Stage 4.4: Filter Results**

**Your Log Output:**
```json
[
    {"dish_id": "dish_14", "include": true, "reason": "Price is under $20 and does not contain peanuts."},
    {"dish_id": "dish_8", "include": false, "reason": "Price is over $20."},
    {"dish_id": "dish_4", "include": false, "reason": "Contains almonds, a tree nut."}
]
```

**Code:**
```python
def filter_dishes_with_llm(dishes: list, filters: dict, query: str) -> list:
    # For each dish, ask LLM to evaluate
    prompt = f"""
    Filters: {filters}
    Query: {query}

    Evaluate these dishes:
    {json.dumps(dishes, indent=2)}

    For each dish, return:
    {{"dish_id": "...", "include": true/false, "reason": "..."}}
    """

    response = llm.invoke(prompt)
    evaluations = json.loads(response.content)

    # Keep only included dishes
    filtered = [
        dish for dish, eval in zip(dishes, evaluations)
        if eval["include"]
    ]
    return filtered
```

**LLM Call**:
- **Model**: gpt-4o-mini
- **Input Tokens**: 977
- **Output Tokens**: 86

**Final Result:**
- Only **dish_14** passes all filters
- Dish 8: Excluded (price > $20)
- Dish 4: Excluded (contains almonds)

#### **Stage 4.5: Store Results**

```python
state.menu_results = {
    "Show me dishes under $20 that are peanut-free": [
        {
            "dish_id": "dish_14",
            "dish_name": "Margherita Pizza",
            "description": "Classic pizza with tomato sauce and mozzarella",
            "price": 15.99,
            "ingredients": ["flour", "tomato", "mozzarella", "basil"],
            "allergens": ["dairy", "gluten"],
            "nutrition_facts": {
                "calories": {"value": 750},
                "protein": {"value": 28},
                "fat": {"value": 25},
                "carbohydrates": {"value": 95}
            }
        }
    ]
}
```

---

### **NODE 5: Info Retriever**

**File**: `/backend/app/services/dish_info_service.py`

**Purpose**: Get detailed info about specific dishes

**For Your Query:** No dish_info intents, so this node returns empty results.

```python
def retrieve_info(state: ChatState) -> ChatState:
    if not state.query_parts.get("dish_info"):
        state.info_results = {"info_results": {}}
        return state

    # ... (would fetch detailed dish info if requested)
```

---

### **NODE 6: Preferences Retriever**

**File**: `/backend/app/services/user_preferences_service.py`

**Purpose**: Answer questions like "What am I allergic to?"

**For Your Query:** No user_preferences intents, so returns empty.

```python
def retrieve_preferences(state: ChatState) -> ChatState:
    if not state.query_parts.get("user_preferences"):
        state.preference_results = {"preference_results": {}}
        return state

    # ... (would fetch user preferences if requested)
```

---

### **NODE 7: Response Formatter**

**File**: `/backend/app/services/response_synthesizer_tool.py`

**Purpose**: Aggregate all results into final response

```python
def format_response(state: ChatState) -> ChatState:
    response_parts = []

    # Add menu results summary
    if state.menu_results:
        total_dishes = sum(len(dishes) for dishes in state.menu_results.values())
        if total_dishes > 0:
            response_parts.append(
                f"I found {total_dishes} dish{'es' if total_dishes > 1 else ''} matching your search!"
            )

    # Add info results
    if state.info_results and state.info_results.get("info_results"):
        for info in state.info_results["info_results"].values():
            response_parts.append(info.get("requested_info", ""))

    # Add preference results
    if state.preference_results and state.preference_results.get("preference_results"):
        for pref in state.preference_results["preference_results"].values():
            response_parts.append(pref.get("answer", ""))

    # Fallback
    if not response_parts:
        response_parts.append("I couldn't find any results for your query.")

    state.response = "\n\n".join(response_parts)
    state.status = "success" if response_parts else "failed"

    return state
```

**Final State:**
```python
{
    "user_id": "692e0fdb05007b7686f86c02",
    "session_id": "sess_794b1625a0",
    "restaurant_id": "rest_1",
    "query": "Show me dishes under $20 that are peanut-free",
    "menu_results": {
        "Show me dishes under $20 that are peanut-free": [
            {
                "dish_id": "dish_14",
                "dish_name": "Margherita Pizza",
                "price": 15.99,
                # ... full dish data
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

### **STAGE 5: Save to Database**

**File**: `/backend/app/services/state_service.py`

```python
def save_chat_state(state: ChatState):
    chat_states_collection.insert_one({
        "_id": ObjectId(),
        "user_id": state.user_id,
        "session_id": state.session_id,
        "restaurant_id": state.restaurant_id,
        "query": state.query,
        "intents": state.intents,
        "context": state.context,
        "current_context": state.current_context,
        "query_parts": state.query_parts,
        "menu_results": state.menu_results,
        "info_results": state.info_results,
        "preference_results": state.preference_results,
        "data": state.data,
        "response": state.response,
        "status": state.status,
        "timestamp": datetime.utcnow()
    })
```

**MongoDB Collection**: `chat_states`

---

### **STAGE 6: Return Response to Frontend**

**File**: `/backend/app/routers/restaurant_router.py` (line 95)

```python
return JSONResponse(status_code=200, content=jsonable_encoder(final_state))
```

**HTTP Response:**
```json
{
  "user_id": "692e0fdb05007b7686f86c02",
  "session_id": "sess_794b1625a0",
  "restaurant_id": "rest_1",
  "query": "Show me dishes under $20 that are peanut-free",
  "menu_results": {
    "Show me dishes under $20 that are peanut-free": [
      {
        "dish_id": "dish_14",
        "dish_name": "Margherita Pizza",
        "description": "Classic pizza with tomato sauce and mozzarella",
        "price": 15.99,
        "ingredients": ["flour", "tomato", "mozzarella", "basil"],
        "allergens": ["dairy", "gluten"],
        "nutrition_facts": {
          "calories": {"value": 750},
          "protein": {"value": 28}
        }
      }
    ]
  },
  "info_results": {"info_results": {}},
  "preference_results": {"preference_results": {}},
  "response": "I found 1 dish matching your search!",
  "status": "success"
}
```

---

### **STAGE 7: Frontend Renders Response**

**File**: `/frontend/src/pages/SearchChat.tsx` (lines 146-252)

```typescript
// Parse response
const data = await response.json();

let assistantContent = '';
let menuResults: DishResult[] = [];

// Extract menu results
if (data.menu_results && Object.keys(data.menu_results).length > 0) {
  Object.entries(data.menu_results).forEach(([query, results]: [string, any]) => {
    if (Array.isArray(results)) {
      menuResults = [...menuResults, ...results];
    }
  });

  if (menuResults.length > 0) {
    assistantContent = `I found ${menuResults.length} dish${menuResults.length > 1 ? 'es' : ''} matching your search! 🍽️`;
  }
}

// Create assistant message
const assistantMessage: Message = {
  id: (Date.now() + 1).toString(),
  type: 'assistant',
  content: assistantContent,
  timestamp: new Date(),
  menuResults: menuResults.length > 0 ? menuResults : undefined
};

setMessages(prev => [...prev, assistantMessage]);
```

**UI Rendering** (lines 343-404):

```tsx
{messages.map((message) => (
  <div className={`message-bubble ${message.type}`}>
    <p>{message.content}</p>

    {/* Render dishes */}
    {message.menuResults && (
      <div className="results-container">
        {message.menuResults.map((dish) => (
          <div className="result-card">
            <h4>{dish.dish_name}</h4>
            <span>${dish.price.toFixed(2)}</span>
            <p>{dish.description}</p>

            {/* Allergens */}
            <div className="allergen-tags">
              {dish.allergens.map(allergen => (
                <span className="allergen-tag">{allergen}</span>
              ))}
            </div>

            {/* Nutrition */}
            <div className="result-nutrition">
              {dish.nutrition_facts.calories && (
                <span>{dish.nutrition_facts.calories.value} cal</span>
              )}
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
))}
```

---

## 📁 File Workflow Diagram

```
FRONTEND
--------
/frontend/src/pages/SearchChat.tsx
  └─ handleSendMessage() [Line 74]
      │
      └─ POST /restaurants/search
          │
          ▼
BACKEND API ROUTER
------------------
/backend/app/routers/restaurant_router.py
  └─ chat_search() [Line 70]
      │
      ├─ state_service.get_or_create_session()
      │   └─ /backend/app/services/state_service.py [Line 15]
      │       └─ MongoDB: chat_states collection
      │
      ├─ state_service.rebuild_context()
      │   └─ /backend/app/services/state_service.py [Line 45]
      │       ├─ MongoDB: users collection (allergens)
      │       └─ MongoDB: chat_states collection (history)
      │
      ├─ create_chat_graph()
      │   └─ /backend/app/flow/graph.py [Line 12]
      │       │
      │       └─ 7-Node Pipeline:
      │           │
      │           ├─ NODE 1: resolve_context
      │           │   └─ /backend/app/services/context_resolver.py [Line 65]
      │           │       └─ OpenAI GPT-4o-mini (query rewriting)
      │           │
      │           ├─ NODE 2: classify_intent
      │           │   └─ /backend/app/services/intent_service.py [Line 20]
      │           │       └─ OpenAI GPT-4o-mini (intent classification)
      │           │
      │           ├─ NODE 3: generate_query_parts
      │           │   └─ /backend/app/flow/graph.py [Node function]
      │           │
      │           ├─ NODE 4: retrieve_menu 🔍
      │           │   └─ /backend/app/services/retrieval_service.py [Line 85]
      │           │       │
      │           │       ├─ generate_search_terms()
      │           │       │   └─ OpenAI GPT-4o-mini
      │           │       │
      │           │       ├─ vector_search()
      │           │       │   └─ /backend/app/services/faiss_service.py [Line 45]
      │           │       │       ├─ OpenAI Embeddings API
      │           │       │       ├─ FAISS Index Search
      │           │       │       └─ MongoDB: dishes collection
      │           │       │
      │           │       ├─ extract_structured_filters()
      │           │       │   └─ OpenAI GPT-4o-mini
      │           │       │
      │           │       └─ filter_dishes_with_llm()
      │           │           └─ OpenAI GPT-4o-mini
      │           │
      │           ├─ NODE 5: retrieve_info
      │           │   └─ /backend/app/services/dish_info_service.py [Line 30]
      │           │       └─ MongoDB: dishes collection
      │           │
      │           ├─ NODE 6: retrieve_preferences
      │           │   └─ /backend/app/services/user_preferences_service.py [Line 25]
      │           │       └─ MongoDB: users collection
      │           │
      │           └─ NODE 7: format_response
      │               └─ /backend/app/services/response_synthesizer_tool.py [Line 18]
      │
      ├─ state_service.save_chat_state()
      │   └─ MongoDB: chat_states collection
      │
      └─ return JSONResponse(final_state)
          │
          ▼
FRONTEND RESPONSE HANDLING
--------------------------
/frontend/src/pages/SearchChat.tsx
  └─ Process response [Line 146]
      │
      ├─ Extract menu_results
      ├─ Extract info_results
      ├─ Extract preference_results
      │
      └─ Render UI [Line 343]
          ├─ Assistant message bubble
          ├─ Dish cards with:
          │   ├─ Name & Price
          │   ├─ Description
          │   ├─ Allergen tags
          │   └─ Nutrition facts
          └─ Auto-scroll to bottom
```

---

## 🔑 Key Components

### **1. Session Management**
- **File**: `/backend/app/services/state_service.py`
- **Purpose**: Track conversations per user + restaurant
- **Session ID Format**: `sess_{random_hex}`
- **Storage**: MongoDB `chat_states` collection

### **2. Context Rebuilding**
- **Fetches**:
  - User allergen preferences from `users` collection
  - Last 5 queries from `chat_states` collection
- **Provides**:
  - Conversation history to LLM
  - User dietary restrictions

### **3. LangGraph Pipeline**
- **Framework**: LangGraph (LangChain)
- **Nodes**: 7 sequential processing steps
- **State**: ChatState object passed through all nodes
- **Benefit**: Clean separation of concerns, easy to debug

### **4. Vector Search (FAISS)**
- **Embeddings**: OpenAI `text-embedding-ada-002` (1536 dimensions)
- **Index**: FAISS (Facebook AI Similarity Search)
- **Storage**: In-memory indexes per restaurant
- **Purpose**: Semantic similarity search (not just keyword matching)

### **5. LLM-Based Filtering**
- **Why**: Complex logic (allergens, price, nutrition) hard to code
- **How**: Send candidate dishes + filters to GPT-4o-mini
- **Output**: Boolean decision + reasoning for each dish
- **Cost**: ~1000 tokens per filter call

### **6. MongoDB Collections**
- **users**: User accounts + allergen_preferences
- **restaurants**: Restaurant metadata
- **dishes**: Menu items (name, price, ingredients, allergens, nutrition)
- **chat_states**: Conversation history
- **sessions**: Active sessions (optional)

---

## 📊 Data Transformations

### **Input (Frontend)**
```typescript
{
  query: "Show me dishes under $20 that are peanut-free",
  user_id: "692e0fdb05007b7686f86c02",
  restaurant_id: "rest_1"
}
```

### **After Context Resolver**
```python
{
  query: "Show me dishes under $20 that are peanut-free",  # Unchanged
  current_context: "User is allergic to peanuts. Previously searched for pizza under $20."
}
```

### **After Intent Classifier**
```python
{
  intents: {
    "menu_search": ["Show me dishes under $20 that are peanut-free"],
    "dish_info": [],
    "user_preferences": [],
    "irrelevant": []
  }
}
```

### **After Query Part Generator**
```python
{
  query_parts: {
    "menu_search": ["Show me dishes under $20 that are peanut-free"],
    "dish_info": [],
    "user_preferences": []
  }
}
```

### **After Menu Retriever**
```python
{
  menu_results: {
    "Show me dishes under $20 that are peanut-free": [
      {
        "dish_id": "dish_14",
        "dish_name": "Margherita Pizza",
        "price": 15.99,
        "allergens": ["dairy", "gluten"],
        # ... full dish object
      }
    ]
  }
}
```

### **After Response Formatter**
```python
{
  response: "I found 1 dish matching your search!",
  status: "success"
}
```

### **Output (Backend → Frontend)**
```json
{
  "menu_results": { ... },
  "info_results": {"info_results": {}},
  "preference_results": {"preference_results": {}},
  "response": "I found 1 dish matching your search!",
  "status": "success"
}
```

### **Rendered (Frontend UI)**
```
┌─────────────────────────────────────────┐
│ 🤖 Assistant                            │
│ I found 1 dish matching your search! 🍽️│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ Margherita Pizza         $15.99     ││
│ │ Classic pizza with tomato sauce     ││
│ │                                     ││
│ │ Allergens: [dairy] [gluten]         ││
│ │ Nutrition: 750 cal • 28g protein    ││
│ └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

---

## 🎯 Summary

### **Request Flow (10 Steps)**

1. **User Input** → SearchChat.tsx sends POST request
2. **API Router** → Receives request, gets/creates session
3. **Context Rebuild** → Fetches user allergens + chat history
4. **LangGraph Start** → Initializes ChatState
5. **Context Resolver** → Rewrites query with context
6. **Intent Classifier** → Identifies query type (menu_search)
7. **Menu Retriever** → Vector search + LLM filtering
8. **Response Formatter** → Aggregates results
9. **Save State** → Stores in MongoDB
10. **Frontend Render** → Displays dishes in UI

### **LLM Calls (7 Total)**

| Step | Purpose | Model | Input Tokens | Output Tokens |
|------|---------|-------|--------------|---------------|
| 1 | Query rewriting | gpt-4o-mini | 852 | 11 |
| 2 | Context summary | gpt-4o-mini | 577 | 162 |
| 3 | Intent classification | gpt-4o-mini | 745 | 41 |
| 4 | Search term generation | gpt-4o-mini | 712 | 24 |
| 5 | Structured filter extraction | gpt-4o-mini | 1568 (1024 cached) | 49 |
| 6 | Dish filtering | gpt-4o-mini | 977 | 86 |
| 7 | Embeddings (3 calls) | text-embedding-ada-002 | - | - |

**Total**: ~5,431 input tokens, ~373 output tokens

### **Database Queries (6 Total)**

1. Find existing session
2. Fetch user allergen preferences
3. Fetch chat history (last 5)
4. Vector search in FAISS
5. Fetch dish details from MongoDB
6. Insert chat state

---

## 📝 Notes

- **Context Window**: Last 5 queries kept in context
- **FAISS Index**: Loaded in memory on startup
- **LLM Provider**: OpenAI (gpt-4o-mini, text-embedding-ada-002)
- **Session Lifetime**: Persistent (not time-limited)
- **Allergen Handling**: Automatically injected from user profile
- **Error Handling**: Graceful fallbacks at each stage

---

**Generated**: 2025-12-02
**Based On**: Backend logs and code analysis
