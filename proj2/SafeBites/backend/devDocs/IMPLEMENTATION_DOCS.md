# User Preferences Feature - Complete Implementation Documentation

## Overview

This document details the complete implementation of the user preferences feature in SafeBites, which allows users to query their own allergen preferences and account information through natural language queries like "what am I allergic to?".

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Implementation](#backend-implementation)
3. [Frontend Implementation](#frontend-implementation)
4. [Data Flow](#data-flow)
5. [Key Concepts](#key-concepts)
6. [Testing Guide](#testing-guide)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                      (SearchChat.tsx)                            │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP POST /restaurants/search
                               │ {query, user_id, restaurant_id}
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Backend Router                             │
│                  (restaurant_router.py)                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline                            │
│  1. Context Resolver    → Rewrites query with context          │
│  2. Intent Classifier   → Classifies query type                │
│  3. Query Part Generator → Organizes by intent                 │
│  4. Menu Retriever      → Gets dishes (if menu_search)         │
│  5. Dish Info Retriever → Gets dish details (if dish_info)     │
│  6. User Prefs Retriever → Gets user info (if user_preferences)│
│  7. Response Synthesizer → Formats final response               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Final Response                            │
│  {responses: [{type: "user_preferences", result: {...}}]}      │
└─────────────────────────────────────────────────────────────────┘
```

### Intent Classification System

The system classifies user queries into 4 categories:

1. **`menu_search`**: Queries asking for dishes/meals (e.g., "show me pizzas")
2. **`dish_info`**: Questions about specific dishes (e.g., "how many calories in pasta?")
3. **`user_preferences`**: Questions about user's own data (e.g., "what am I allergic to?")
4. **`irrelevant`**: Off-topic queries (e.g., "tell me a joke")

---

## Backend Implementation

### 1. User Preferences Service

**File**: `backend/app/services/user_preferences_service.py`

This is the core service that handles user preference queries.

```python
def get_user_preferences(state):
    """
    Handle user preference queries like "what am I allergic to?"

    Flow:
    1. Extract user_preferences queries from state.query_parts
    2. Look for user_allergens in state.context
    3. Use LLM to format a natural language response
    4. Return structured UserPreferencesResult
    """
```

**Key Features**:
- **Early Return**: If no user_preferences queries exist, returns empty results immediately
- **Context Extraction**: Searches context for `user_allergens` key
- **LLM Formatting**: Uses OpenAI to generate conversational responses
- **Error Handling**: Gracefully handles missing data, JSON parse errors

**Example Context Structure**:
```python
state.context = [
    {
        "user_allergens": ["peanuts", "dairy", "shellfish"],
        "message": "User is allergic to: peanuts, dairy, shellfish"
    },
    # ... previous chat states
]
```

**LLM Prompt**:
```python
"""
You are a helpful assistant answering questions about the user's preferences.

User Query: {query}
User Information:
- Allergen Preferences: {allergens}

Provide a helpful, conversational answer.
If allergens list is empty, tell them they haven't set preferences yet.

Output format (JSON only):
{"answer": "your conversational answer"}
"""
```

---

### 2. User Preferences Models

**File**: `backend/app/models/user_preferences_model.py`

Defines Pydantic models for type safety and validation.

```python
class UserPreferencesResponse(BaseModel):
    """Single query response"""
    answer: str  # Natural language answer

class UserPreferencesResult(BaseModel):
    """Container for all preference queries"""
    preference_results: Dict[str, UserPreferencesResponse]
    # Key: original query, Value: answer
```

**Example**:
```python
UserPreferencesResult(
    preference_results={
        "What am I allergic to?": UserPreferencesResponse(
            answer="You are allergic to peanuts and dairy."
        )
    }
)
```

---

### 3. Intent Classification Updates

**File**: `backend/app/services/intent_service.py`

Enhanced the LLM prompt to correctly classify user preference queries.

**Critical Addition** (Lines 56-59):
```python
⚡ CRITICAL - User preference queries:
- If the query asks "what am I allergic to?", "what are my allergies?",
  "what are my preferences?", or similar → ALWAYS put it in "user_preferences"
- DO NOT put user preference queries in "dish_info" or "menu_search"
- User preference queries are about the USER, not about dishes
```

**Why This Matters**:
Without this explicit rule, the LLM might classify "what am I allergic to?" as `dish_info` because it's asking about allergens, even though it's about the user's own allergens, not dish allergens.

**Example 4** (Lines 117-131):
```json
{
  "menu_search": ["Show me safe desserts"],
  "dish_info": [],
  "user_preferences": ["What am I allergic to?"],
  "irrelevant": []
}
```

---

### 4. Context Resolver Protection

**File**: `backend/app/services/context_resolver.py`

Updated to prevent rewriting user preference queries.

**Key Addition** (Line 71):
```python
**Rules**:
1. **DO NOT rewrite user preference queries**: If the query asks about
   the USER'S OWN preferences, allergens, or account info
   (e.g., "what am I allergic to?"), return it EXACTLY as-is.
```

**Why This Matters**:
The context resolver might see allergen info in the context and try to "improve" the query by adding context, which could confuse the intent classifier. We want "what am I allergic to?" to remain unchanged.

---

### 5. State Service - User Allergen Fetching

**File**: `backend/app/services/state_service.py`

Fetches user allergen preferences from MongoDB and adds to context.

**Implementation** (Lines 119-139):
```python
def rebuild_context(session_id: str, user_id: str = None, last_n: int = 5):
    """
    Reconstructs conversation context including user allergens.

    If user_id provided:
    1. Fetch user document from MongoDB
    2. Extract allergen_preferences field
    3. Add to context as first item with special format
    """
    context = []

    if user_id:
        users = db["users"]
        user_doc = users.find_one({"_id": ObjectId(user_id)})

        if user_doc and user_doc.get("allergen_preferences"):
            allergen_prefs = user_doc.get("allergen_preferences", [])
            context.append({
                "user_allergens": allergen_prefs,
                "message": f"User is allergic to: {', '.join(allergen_prefs)}"
            })

    # Add previous chat states...
    return context
```

**Why the Special Format**:
- `user_allergens`: Used by user_preferences_service to extract allergens
- `message`: Used by other services (like restaurant filters) to understand user needs

---

### 6. Conversation Graph Integration

**File**: `backend/app/flow/graph.py`

Added user_preferences_retriever node to the LangGraph pipeline.

**Node Addition** (Lines 98-108):
```python
graph.add_node("user_preferences_retriever", get_user_preferences)

# Connections:
graph.add_edge("query_part_generator", "user_preferences_retriever")
graph.add_edge("user_preferences_retriever", "format_final_response")
```

**Graph Flow**:
```
context_resolver
      ↓
intent_classifier
      ↓
query_part_generator
      ↓
   ┌──┴────────┬────────────────┐
   ↓           ↓                ↓
menu_retriever dish_info    user_preferences
               _retriever    _retriever
   ↓           ↓                ↓
   └──┬────────┴────────────────┘
      ↓
format_final_response
```

**Parallel Processing**:
All three retrievers run in parallel because LangGraph executes nodes with no dependencies concurrently. If a retriever has no queries to process, it returns empty results immediately.

---

### 7. Response Models Update

**File**: `backend/app/models/responder_model.py`

Added PreferenceResult to the response type union.

**Addition** (Lines 95-102):
```python
class PreferenceResult(BaseModel):
    """Response to user preference queries"""
    answer: str

class QueryResponse(BaseModel):
    query: str
    type: str  # "menu_search" | "dish_info" | "user_preferences" | "irrelevant"
    result: Union[List[DishResult], InfoResult, PreferenceResult, Dict[str, str]]
```

**Why Union Type**:
A `QueryResponse` can contain different result types depending on the query type. Python's Union allows the `result` field to be any of these types, and Pydantic validates it at runtime.

---

### 8. Response Synthesizer

**File**: `backend/app/services/response_synthesizer_tool.py`

Formats preference_results into the final response.

**Implementation** (Lines 84-91):
```python
if state.preference_results and state.preference_results.preference_results:
    for query, pref in state.preference_results.preference_results.items():
        logger.debug(f"Printing Preference results for query {query} : {pref}")
        responses.append(QueryResponse(
            query=query,
            type="user_preferences",
            result=PreferenceResult(**pref.model_dump())
        ))
```

**Final Response Structure**:
```json
{
  "user_id": "67123abc...",
  "session_id": "sess_9962c34137",
  "restaurant_id": "rest_1",
  "original_query": "what am I allergic to?",
  "responses": [
    {
      "query": "What am I allergic to?",
      "type": "user_preferences",
      "result": {
        "answer": "You are allergic to peanuts and dairy."
      }
    }
  ],
  "status": "success",
  "timestamp": "2025-11-26T05:30:15.478999"
}
```

---

### 9. Chat State Model

**File**: `backend/app/flow/state.py`

Added preference_results field to track preference query results.

**Addition** (Lines 69-70, 98):
```python
class ChatState(BaseModel):
    # ... existing fields ...
    preference_results: Optional[UserPreferencesResult] = None
```

**Why Optional**:
Not all queries have preference results. If the query is "show me pizzas", preference_results will be None.

---

### 10. Router Updates

**File**: `backend/app/routers/restaurant_router.py`

Made user_id optional to support both guest and authenticated users.

**Change** (Lines 65-68):
```python
class ChatQuery(BaseModel):
    query: str
    user_id: Optional[str] = None  # Was required, now optional
    restaurant_id: Optional[str] = None
```

**Backward Compatibility** (Lines 80-85):
```python
user_id = payload.user_id or "guest"

# Pass None to rebuild_context if guest
context = state_service.rebuild_context(
    session_id,
    user_id if user_id != "guest" else None
)
```

**Why This Pattern**:
- Frontend can omit user_id for guest users
- Backend treats "guest" specially (no allergen lookup)
- Database sessions still track guest users for conversation history

---

## Frontend Implementation

### 1. User ID Integration

**File**: `frontend/src/pages/SearchChat.tsx`

Added user_id to API requests from localStorage.

**Implementation** (Lines 95-103):
```typescript
const handleSendMessage = async () => {
    // Get user_id from localStorage if logged in
    const user_id = localStorage.getItem("authToken") || undefined;

    // Request body with optional user_id
    const requestBody = {
        query: currentQuery,
        restaurant_id: "rest_1",
        ...(user_id && { user_id }) // Only include user_id if it exists
    };

    // Send to backend...
}
```

**Spread Operator Trick**:
```typescript
...(user_id && { user_id })
```
This is a concise way to conditionally include a field:
- If `user_id` is truthy: spreads `{user_id: "actual_id"}` into the object
- If `user_id` is falsy: spreads nothing (empty object)

**Result**:
```typescript
// Logged in:
{query: "...", restaurant_id: "rest_1", user_id: "67123abc..."}

// Guest:
{query: "...", restaurant_id: "rest_1"}
```

---

### 2. Preference Results Handling

**File**: `frontend/src/pages/SearchChat.tsx`

Added processing for preference_results in API response.

**Implementation** (Lines 198-220):
```typescript
// Extract user preference results (e.g., "what am I allergic to?")
if (data.preference_results && data.preference_results.preference_results) {
    console.log('Found preference_results:', data.preference_results);

    // Build response text from preference results
    const prefTexts: string[] = [];
    Object.entries(data.preference_results.preference_results).forEach(
        ([question, pref]: [string, any]) => {
            console.log(`Preference for "${question}":`, pref);
            if (pref.answer) {
                prefTexts.push(pref.answer);
            }
        }
    );

    if (prefTexts.length > 0) {
        if (assistantContent) {
            assistantContent += '\n\n' + prefTexts.join('\n\n');
        } else {
            assistantContent = prefTexts.join('\n\n');
        }
    }
}
```

**Why Object.entries()**:
The preference_results is an object like:
```typescript
{
    "What am I allergic to?": {answer: "You are allergic to..."}
}
```
`Object.entries()` converts it to an array of `[key, value]` pairs we can iterate over.

---

## Data Flow

### Complete Flow for "what am I allergic to?"

#### 1. Frontend → Backend
```typescript
POST /restaurants/search
{
    "query": "what am I allergic to?",
    "user_id": "67123abc...",
    "restaurant_id": "rest_1"
}
```

#### 2. Router Processing
```python
# restaurant_router.py
user_id = "67123abc..."
session_id = get_or_create_session(user_id, "rest_1")
context = rebuild_context(session_id, user_id)
```

#### 3. Context Building
```python
# state_service.py
users.find_one({"_id": ObjectId("67123abc...")})
# Returns: {allergen_preferences: ["peanuts", "dairy"]}

context = [
    {
        "user_allergens": ["peanuts", "dairy"],
        "message": "User is allergic to: peanuts, dairy"
    }
]
```

#### 4. Context Resolver
```python
# context_resolver.py
# Sees "what am I allergic to?" → user preference query
# Returns query unchanged: "what am I allergic to?"
```

#### 5. Intent Classifier
```python
# intent_service.py
# LLM classifies query
{
    "menu_search": [],
    "dish_info": [],
    "user_preferences": ["What am I allergic to?"],
    "irrelevant": []
}
```

#### 6. Query Part Generator
```python
# graph.py
state.query_parts = {
    "user_preferences": ["What am I allergic to?"]
}
```

#### 7. User Preferences Retriever
```python
# user_preferences_service.py
# Extracts from context
user_allergens = ["peanuts", "dairy"]

# LLM formats response
llm.invoke("Answer: what am I allergic to? Allergens: peanuts, dairy")

# Returns
{
    "preference_results": {
        "What am I allergic to?": {
            "answer": "You are allergic to peanuts and dairy."
        }
    }
}
```

#### 8. Response Synthesizer
```python
# response_synthesizer_tool.py
responses = [
    QueryResponse(
        query="What am I allergic to?",
        type="user_preferences",
        result=PreferenceResult(answer="You are allergic to peanuts and dairy.")
    )
]
```

#### 9. Backend → Frontend
```json
{
    "user_id": "67123abc...",
    "session_id": "sess_9962c34137",
    "restaurant_id": "rest_1",
    "original_query": "what am I allergic to?",
    "responses": [
        {
            "query": "What am I allergic to?",
            "type": "user_preferences",
            "result": {
                "answer": "You are allergic to peanuts and dairy."
            }
        }
    ],
    "status": "success"
}
```

#### 10. Frontend Display
```typescript
// SearchChat.tsx
assistantContent = "You are allergic to peanuts and dairy."
// Displays in chat UI
```

---

## Key Concepts

### 1. LangGraph State Management

**What is LangGraph?**
LangGraph is a framework for building stateful, multi-actor applications with LLMs. Think of it as a state machine where:
- **Nodes** are functions that process state
- **Edges** define the flow between nodes
- **State** is a Pydantic model passed between nodes

**How State Flows**:
```python
state = ChatState(query="what am I allergic to?", ...)

# Node 1
state = context_resolver(state)  # Adds current_context

# Node 2
state = intent_classifier(state)  # Adds intents

# Node 3
state = query_part_generator(state)  # Adds query_parts

# Nodes 4, 5, 6 (parallel)
state = get_menu_items(state)  # Adds menu_results
state = get_dish_info(state)  # Adds info_results
state = get_user_preferences(state)  # Adds preference_results

# Node 7
final_response = format_final_response(state)
```

**State Mutation**:
Each node returns a dictionary with fields to update:
```python
def get_user_preferences(state):
    # ... process ...
    return {"preference_results": UserPreferencesResult(...)}
```
LangGraph merges this into the state object.

---

### 2. Pydantic Models

**What is Pydantic?**
Pydantic provides runtime type validation for Python. When you define a model:
```python
class UserPreferencesResponse(BaseModel):
    answer: str
```

Pydantic ensures:
- `answer` must be a string
- Missing `answer` raises ValidationError
- Extra fields are ignored
- Automatic JSON serialization/deserialization

**Why Use It?**
- **Type Safety**: Catches bugs at runtime
- **Documentation**: Model definitions serve as API docs
- **Validation**: Automatic data validation
- **IDE Support**: Autocomplete and type hints

---

### 3. Context vs Current Context

**`state.context`**: Full conversation history
```python
[
    {"user_allergens": ["peanuts"], "message": "..."},
    {"query": "show me pizzas", "menu_results": {...}},
    {"query": "under $20", "menu_results": {...}}
]
```

**`state.current_context`**: Summarized context for current query
```python
"User previously searched for pizzas under $20.
 Found Pizza Margherita ($15.99) and Pepperoni Pizza ($18.50)."
```

**Why Both?**
- `context`: Used by context_resolver to rewrite queries
- `current_context`: Used by retrieval services to understand what user was doing

---

### 4. Intent Classification with LLMs

**Why Use LLM for Classification?**
Traditional rule-based systems struggle with variations:
- "what am I allergic to?"
- "tell me my allergies"
- "what can't I eat?"
- "show me my allergen preferences"

LLMs understand semantics and can classify these correctly.

**Prompt Engineering**:
The quality of classification depends on the prompt:
```python
# BAD PROMPT:
"Classify this query into categories"

# GOOD PROMPT:
"""
⚡ CRITICAL - User preference queries:
- If the query asks "what am I allergic to?", "what are my allergies?",
  "what are my preferences?", or similar → ALWAYS put it in "user_preferences"
- DO NOT put user preference queries in "dish_info" or "menu_search"
- User preference queries are about the USER, not about dishes
"""
```

**Few-Shot Learning**:
We provide examples in the prompt:
```python
Example 4:
User Query: "What am I allergic to? Also, show me safe desserts."
Output:
{
  "user_preferences": ["What am I allergic to?"],
  "menu_search": ["Show me safe desserts"]
}
```
This teaches the LLM the expected behavior.

---

### 5. Error Handling Strategy

**Graceful Degradation**:
Every service handles errors without crashing:

```python
try:
    response = llm.invoke(prompt)
    data = json.loads(response.content)
    return UserPreferencesResponse(**data)
except json.JSONDecodeError:
    logger.error("JSON parse error")
    return UserPreferencesResponse(
        answer="I encountered an error. Please try again."
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return UserPreferencesResponse(
        answer=f"Error: {str(e)}"
    )
```

**Why This Matters**:
If the LLM returns malformed JSON, we don't crash the entire request. We log the error and return a fallback response.

---

### 6. MongoDB Integration

**User Document Structure**:
```python
{
    "_id": ObjectId("67123abc..."),
    "name": "John Doe",
    "username": "johndoe",
    "password": "$2b$12$hashed...",
    "allergen_preferences": ["peanuts", "dairy", "shellfish"]
}
```

**Fetching User Data**:
```python
users = db["users"]
user_doc = users.find_one({"_id": ObjectId(user_id)})
allergens = user_doc.get("allergen_preferences", [])
```

**Why ObjectId?**
MongoDB uses ObjectId for unique identifiers. We convert the string user_id to ObjectId for database queries.

---

## Testing Guide

### Testing User Preference Queries

#### 1. Create a Test User
```bash
curl -X POST http://localhost:8000/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "username": "testuser",
    "password": "password123",
    "allergen_preferences": ["peanuts", "dairy", "shellfish"]
  }'
```

Response:
```json
{
    "_id": "67123abc...",
    "name": "Test User",
    "username": "testuser",
    "allergen_preferences": ["peanuts", "dairy", "shellfish"]
}
```

#### 2. Login
```typescript
// In frontend: Login.tsx
// After successful login, user_id is stored in localStorage
localStorage.setItem('authToken', '67123abc...')
```

#### 3. Test Queries

**Query 1**: "what am I allergic to?"
Expected Response: "You are allergic to peanuts, dairy, and shellfish."

**Query 2**: "show me my preferences"
Expected Response: Similar allergen list

**Query 3**: "what can't I eat?"
Expected Response: Allergen list with conversational phrasing

#### 4. Guest User Test
```typescript
// Clear localStorage
localStorage.removeItem('authToken')

// Query: "what am I allergic to?"
// Expected: "It looks like you haven't set any allergen preferences yet."
```

---

### Debugging with Logs

**Enable Debug Logging**:
```bash
# In backend terminal, you should see:
Fetching allergen preferences for user_id: 67123abc...
User document: {'_id': ObjectId('67123abc...'), 'allergen_preferences': [...]}
Found allergen preferences: ['peanuts', 'dairy', 'shellfish']
Processing 1 user preference queries
```

**Frontend Console**:
```javascript
=== CHAT API REQUEST ===
Body: {
  "query": "what am I allergic to?",
  "user_id": "67123abc...",
  "restaurant_id": "rest_1"
}

Found preference_results: {...}
Preference for "What am I allergic to?": {answer: "You are allergic to..."}
```

---

## Troubleshooting

### Issue 1: "No user_id provided, skipping allergen preference fetch"

**Cause**: Frontend not sending user_id

**Fix**:
```typescript
// SearchChat.tsx
const user_id = localStorage.getItem("authToken") || undefined;
const requestBody = {
    query: currentQuery,
    restaurant_id: "rest_1",
    ...(user_id && { user_id })
};
```

---

### Issue 2: "No allergen preferences found"

**Cause**: User document doesn't have allergen_preferences field

**Fix**:
```bash
# Update user in MongoDB
db.users.updateOne(
    {_id: ObjectId("67123abc...")},
    {$set: {allergen_preferences: ["peanuts", "dairy"]}}
)
```

---

### Issue 3: Query classified as "dish_info" instead of "user_preferences"

**Cause**: Intent classification prompt not strong enough

**Fix**: Already implemented in intent_service.py (lines 56-59)

**Verify**:
```bash
# Check backend logs for:
"user_preferences": ["What am I allergic to?"]
# NOT:
"dish_info": ["What am I allergic to?"]
```

---

### Issue 4: "user_allergens not found in context"

**Cause**: State service not adding allergens to context

**Verify**:
```python
# Add logging in user_preferences_service.py
logger.debug(f"State context: {state.context}")
```

**Expected**:
```python
[
    {"user_allergens": ["peanuts", "dairy"], "message": "..."},
    # ...
]
```

---

### Issue 5: Frontend not displaying preference results

**Cause**: Frontend not handling preference_results

**Fix**: Already implemented in SearchChat.tsx (lines 198-220)

**Verify Console**:
```javascript
Found preference_results: {preference_results: {...}}
```

---

## Advanced Topics

### 1. Extending to Other User Data

Want to add "what is my address?" support?

**Backend**:
```python
# user_preferences_service.py
def get_user_preferences(state):
    # Extract user data
    user_address = None
    user_allergens = []

    if state.context:
        for ctx_item in state.context:
            if "user_data" in ctx_item:
                user_address = ctx_item.get("address")
                user_allergens = ctx_item.get("allergens")

    # Pass to LLM
    prompt = ChatPromptTemplate.from_template("""
        User Query: {query}
        User Information:
        - Allergens: {allergens}
        - Address: {address}

        Answer the user's query.
        Output: {{"answer": "..."}}
    """)
```

**State Service**:
```python
# state_service.py
context.append({
    "user_data": {
        "allergens": allergen_prefs,
        "address": user_doc.get("address"),
        "phone": user_doc.get("phone")
    }
})
```

---

### 2. Multi-Language Support

Add Spanish support:

**Intent Service**:
```python
Example 5 (Spanish):
User Query: "¿A qué soy alérgico?"
Output:
{
  "user_preferences": ["¿A qué soy alérgico?"]
}
```

**User Preferences Service**:
```python
prompt = ChatPromptTemplate.from_template("""
    User Query: {query}
    User Allergens: {allergens}

    Answer in the SAME LANGUAGE as the query.
    Output: {{"answer": "..."}}
""")
```

---

### 3. Caching User Data

Avoid repeated database calls:

```python
# state_service.py
_user_cache = {}  # Simple in-memory cache

def get_user_allergens(user_id: str):
    if user_id in _user_cache:
        return _user_cache[user_id]

    user_doc = users.find_one({"_id": ObjectId(user_id)})
    allergens = user_doc.get("allergen_preferences", [])

    _user_cache[user_id] = allergens
    return allergens
```

**Warning**: Clear cache when user updates preferences!

---

## Summary

### What We Built

1. **New Intent Type**: `user_preferences` for queries about user's own data
2. **User Preferences Service**: Retrieves and formats user allergen preferences
3. **Context Integration**: Automatically fetches user data from MongoDB
4. **Frontend Integration**: Sends user_id and displays preference results
5. **Complete Pipeline**: End-to-end flow from user query to formatted response

### Key Takeaways

- **LangGraph** enables complex, stateful conversation flows
- **Pydantic** provides type safety and validation
- **LLM Prompts** must be explicit and include examples
- **Error Handling** ensures graceful degradation
- **Context Management** maintains conversation continuity

### Files Modified

**Backend** (9 files):
1. `services/user_preferences_service.py` (NEW)
2. `models/user_preferences_model.py` (NEW)
3. `services/intent_service.py`
4. `services/context_resolver.py`
5. `services/state_service.py`
6. `flow/graph.py`
7. `flow/state.py`
8. `models/responder_model.py`
9. `services/response_synthesizer_tool.py`

**Frontend** (1 file):
1. `pages/SearchChat.tsx`

---

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)

---

**Author**: Claude (Anthropic)
**Date**: November 26, 2025
**Version**: 1.0
