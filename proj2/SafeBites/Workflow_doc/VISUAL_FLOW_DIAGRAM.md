# SafeBites Visual Flow Diagrams

## Complete System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              SAFEBITES SYSTEM                               │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND LAYER                              │
│                           (React + TypeScript)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Welcome    │  │    Login     │  │   SignUp     │  │  Dashboard   │  │
│  │   Page       │  │    Page      │  │    Page      │  │    Page      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │     Home     │  │  SearchChat  │  │   Settings   │  │  Restaurant  │  │
│  │    Page      │  │  🔍 (MAIN)  │  │    Page      │  │    Details   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    API Configuration                                │  │
│  │  - Base URL: http://localhost:8000 or Render                       │  │
│  │  - Authentication: Bearer Token (localStorage)                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP POST /restaurants/search
                                      │ {query, user_id, restaurant_id}
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND API LAYER                              │
│                         (FastAPI + Python 3.10)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  │
│  │  restaurant_router   │  │    user_router       │  │  admin_router   │  │
│  │  - POST /search      │  │  - POST /register    │  │  - Mgmt tools   │  │
│  │  - GET /history      │  │  - POST /login       │  │                 │  │
│  │  - CRUD endpoints    │  │  - PATCH /allergens  │  │                 │  │
│  └──────────────────────┘  └──────────────────────┘  └─────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ chat_search() invokes
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SESSION/STATE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    state_service.py                                │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │  get_or_create_session(user_id, restaurant_id)                    │    │
│  │    └─► Returns: "sess_794b1625a0"                                 │    │
│  │                                                                    │    │
│  │  rebuild_context(session_id, user_id)                             │    │
│  │    ├─► Fetch user allergen_preferences from MongoDB               │    │
│  │    ├─► Fetch last 5 chat_states from MongoDB                      │    │
│  │    └─► Returns: context array with history + allergens            │    │
│  │                                                                    │    │
│  │  save_chat_state(final_state)                                     │    │
│  │    └─► Insert into MongoDB chat_states collection                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ State passed to LangGraph
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LANGGRAPH PIPELINE (7 NODES)                        │
│                              flow/graph.py                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 1: Context Resolver                                            │   │
│  │ File: services/context_resolver.py                                  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Input:  "Show me dishes under $20 that are peanut-free"            │   │
│  │ Context: [User allergens: Peanuts, Previous: pizza search]         │   │
│  │                                                                     │   │
│  │ Action: Call GPT-4o-mini to rewrite query with context             │   │
│  │                                                                     │   │
│  │ Output: "Show me dishes under $20 that are peanut-free"            │   │
│  │         (Already self-contained, no rewrite needed)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 2: Intent Classifier                                           │   │
│  │ File: services/intent_service.py                                    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Input: Rewritten query                                              │   │
│  │                                                                     │   │
│  │ Action: Call GPT-4o-mini to classify into intent types              │   │
│  │                                                                     │   │
│  │ Output:                                                             │   │
│  │   {                                                                 │   │
│  │     "menu_search": ["Show me dishes under $20 peanut-free"],       │   │
│  │     "dish_info": [],                                               │   │
│  │     "user_preferences": [],                                        │   │
│  │     "irrelevant": []                                               │   │
│  │   }                                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 3: Query Part Generator                                        │   │
│  │ File: flow/graph.py (node function)                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Input: Classified intents                                           │   │
│  │                                                                     │   │
│  │ Action: Organize intents into structured query_parts               │   │
│  │                                                                     │   │
│  │ Output: state.query_parts = {                                      │   │
│  │   "menu_search": [...],                                            │   │
│  │   "dish_info": [],                                                 │   │
│  │   "user_preferences": []                                           │   │
│  │ }                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 4: Menu Retriever 🔍 (CORE SEARCH)                            │   │
│  │ File: services/retrieval_service.py                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │ STAGE 1: Generate Search Terms                               │  │   │
│  │  ├──────────────────────────────────────────────────────────────┤  │   │
│  │  │ Input: "Show me dishes under $20 that are peanut-free"      │  │   │
│  │  │ Action: GPT-4o-mini generates semantic search terms         │  │   │
│  │  │ Output: {"positive": ["dishes under $20", "affordable"],    │  │   │
│  │  │          "negative": []}                                    │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │ STAGE 2: Vector Search (FAISS)                               │  │   │
│  │  │ File: services/faiss_service.py                              │  │   │
│  │  ├──────────────────────────────────────────────────────────────┤  │   │
│  │  │ For each search term:                                        │  │   │
│  │  │   1. Get OpenAI embedding (1536 dimensions)                 │  │   │
│  │  │   2. Search FAISS index for restaurant                      │  │   │
│  │  │   3. Get top 10 similar dishes                              │  │   │
│  │  │                                                              │  │   │
│  │  │ Returns: [dish_14, dish_8, dish_4, ...]                     │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │ STAGE 3: Extract Structured Filters                         │  │   │
│  │  ├──────────────────────────────────────────────────────────────┤  │   │
│  │  │ Action: GPT-4o-mini extracts constraints                    │  │   │
│  │  │ Output: {                                                   │  │   │
│  │  │   "price": {"max": 20, "min": 0},                          │  │   │
│  │  │   "allergens": {"exclude": ["peanuts"]},                   │  │   │
│  │  │   "ingredients": {"include": [], "exclude": []},           │  │   │
│  │  │   "nutrition": {}                                          │  │   │
│  │  │ }                                                           │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                          │                                          │   │
│  │                          ▼                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │ STAGE 4: LLM-Based Filtering                                │  │   │
│  │  ├──────────────────────────────────────────────────────────────┤  │   │
│  │  │ For each candidate dish:                                    │  │   │
│  │  │   - Send to GPT-4o-mini with filters                        │  │   │
│  │  │   - Get include/exclude decision + reason                   │  │   │
│  │  │                                                              │  │   │
│  │  │ Results:                                                     │  │   │
│  │  │   ✓ dish_14: include (under $20, no peanuts)               │  │   │
│  │  │   ✗ dish_8:  exclude (price > $20)                         │  │   │
│  │  │   ✗ dish_4:  exclude (contains almonds)                    │  │   │
│  │  │                                                              │  │   │
│  │  │ Final: [dish_14]                                            │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │ Output: state.menu_results = {                                     │   │
│  │   "Show me dishes under $20 that are peanut-free": [              │   │
│  │     {dish_id: "dish_14", dish_name: "Margherita Pizza", ...}      │   │
│  │   ]                                                                │   │
│  │ }                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 5: Info Retriever                                              │   │
│  │ File: services/dish_info_service.py                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Purpose: Get detailed info about specific dishes                   │   │
│  │          (e.g., "Tell me about dish 27606")                        │   │
│  │                                                                     │   │
│  │ For this query: No dish_info intents → Skip                        │   │
│  │                                                                     │   │
│  │ Output: state.info_results = {"info_results": {}}                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 6: Preferences Retriever                                       │   │
│  │ File: services/user_preferences_service.py                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Purpose: Answer questions about user preferences                   │   │
│  │          (e.g., "What am I allergic to?")                          │   │
│  │                                                                     │   │
│  │ For this query: No user_preferences intents → Skip                 │   │
│  │                                                                     │   │
│  │ Output: state.preference_results = {"preference_results": {}}      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ NODE 7: Response Formatter                                          │   │
│  │ File: services/response_synthesizer_tool.py                         │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Input: All results from previous nodes                              │   │
│  │                                                                     │   │
│  │ Action: Aggregate into final response                               │   │
│  │                                                                     │   │
│  │ Logic:                                                              │   │
│  │   - Count total dishes in menu_results                              │   │
│  │   - Extract text from info_results                                  │   │
│  │   - Extract text from preference_results                            │   │
│  │   - Combine all parts                                               │   │
│  │                                                                     │   │
│  │ Output:                                                             │   │
│  │   state.response = "I found 1 dish matching your search!"          │   │
│  │   state.status = "success"                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ final_state returned
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE LAYER                                 │
│                              (MongoDB Atlas)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    users     │  │ restaurants  │  │    dishes    │  │ chat_states  │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤  │
│  │ _id          │  │ _id          │  │ _id          │  │ _id          │  │
│  │ name         │  │ name         │  │ dish_name    │  │ user_id      │  │
│  │ username     │  │ location     │  │ price        │  │ session_id   │  │
│  │ password     │  │ cuisine[]    │  │ ingredients[]│  │ restaurant_id│  │
│  │ allergen_    │  │ rating       │  │ allergens[]  │  │ query        │  │
│  │ preferences[]│  │              │  │ nutrition_   │  │ intents      │  │
│  │              │  │              │  │ facts{}      │  │ menu_results │  │
│  │              │  │              │  │ embedding[]  │  │ response     │  │
│  │              │  │              │  │              │  │ timestamp    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ FAISS indexes built from dishes
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          VECTOR SEARCH LAYER                                │
│                         (FAISS - In Memory)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ FAISS Indexes (Per Restaurant)                                      │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │ rest_1:                                                             │   │
│  │   ├─ dish_1: [0.123, -0.456, 0.789, ... ] (1536 dims)             │   │
│  │   ├─ dish_2: [0.234, -0.567, 0.890, ... ]                         │   │
│  │   ├─ dish_14: [0.345, -0.678, 0.901, ... ] ← Margherita Pizza     │   │
│  │   └─ ...                                                           │   │
│  │                                                                     │   │
│  │ rest_2:                                                             │   │
│  │   └─ ...                                                           │   │
│  │                                                                     │   │
│  │ Search Algorithm:                                                   │   │
│  │   1. Query embedding: [0.111, -0.222, 0.333, ... ]                │   │
│  │   2. Cosine similarity with all dish embeddings                    │   │
│  │   3. Return top K matches (K=10)                                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Embeddings generated by
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL APIs LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ OpenAI API                                                           │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │ Model: gpt-4o-mini-2024-07-18                                       │  │
│  │ Usage: Query rewriting, intent classification, filtering            │  │
│  │ Calls: ~6-7 per search query                                        │  │
│  │ Cost: ~$0.01 per 1000 input tokens                                  │  │
│  │                                                                      │  │
│  │ Model: text-embedding-ada-002                                       │  │
│  │ Usage: Generate 1536-dim embeddings                                 │  │
│  │ Calls: 3-4 per search query                                         │  │
│  │ Cost: ~$0.0001 per 1000 tokens                                      │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

```

---

## Query Processing Timeline

```
Time (s)  │ Action                                │ Component
──────────┼───────────────────────────────────────┼─────────────────────────────
0.000     │ User clicks "Send"                    │ Frontend
0.050     │ POST /restaurants/search              │ Frontend → Backend
0.100     │ Get/create session                    │ state_service
0.150     │ Fetch user allergens from MongoDB     │ state_service
0.200     │ Fetch chat history from MongoDB       │ state_service
0.250     │ Start LangGraph pipeline              │ graph.py
──────────┼───────────────────────────────────────┼─────────────────────────────
0.300     │ NODE 1: Context Resolver starts       │ context_resolver.py
0.350     │   └─ Call GPT-4o-mini                 │ OpenAI API
2.500     │   └─ Response received                │ (2.15s latency)
──────────┼───────────────────────────────────────┼─────────────────────────────
2.550     │ NODE 2: Intent Classifier starts      │ intent_service.py
2.600     │   └─ Call GPT-4o-mini                 │ OpenAI API
2.750     │   └─ Call GPT-4o-mini (context)       │ OpenAI API
5.900     │   └─ Response received                │ (3.15s latency)
──────────┼───────────────────────────────────────┼─────────────────────────────
5.950     │ NODE 3: Query Part Generator          │ graph.py (instant)
──────────┼───────────────────────────────────────┼─────────────────────────────
6.000     │ NODE 4: Menu Retriever starts         │ retrieval_service.py
6.050     │   ├─ Generate search terms (GPT)      │ OpenAI API
7.100     │   ├─ Get embeddings (3 calls)         │ OpenAI API
7.150     │   │   └─ Call 1: "dishes under $20"   │
9.950     │   │   └─ Call 2: "affordable"          │ (+2.8s)
12.400    │   │   └─ Call 3: original query        │ (+2.45s)
12.450    │   ├─ FAISS search (3x)                │ faiss_service.py
12.500    │   ├─ Extract filters (GPT)            │ OpenAI API
14.700    │   ├─ Filter dishes (GPT)              │ OpenAI API (+2.2s)
16.500    │   └─ Filtering complete                │ (+1.8s)
──────────┼───────────────────────────────────────┼─────────────────────────────
16.550    │ NODE 5: Info Retriever (skip)         │ dish_info_service.py
16.600    │ NODE 6: Preferences Retriever (skip)  │ user_preferences_service.py
──────────┼───────────────────────────────────────┼─────────────────────────────
16.650    │ NODE 7: Response Formatter            │ response_synthesizer_tool.py
16.700    │   └─ Aggregate results                │ (instant)
──────────┼───────────────────────────────────────┼─────────────────────────────
16.750    │ Save chat state to MongoDB            │ state_service
16.850    │ Return JSON response                  │ Backend → Frontend
──────────┼───────────────────────────────────────┼─────────────────────────────
16.900    │ Parse response                        │ Frontend
16.950    │ Render dish cards                     │ Frontend (React)
17.000    │ Display to user ✓                     │ UI Update
──────────┴───────────────────────────────────────┴─────────────────────────────

Total Time: ~17 seconds
  - LLM Calls: ~14s (82%)
  - Database: ~1s (6%)
  - Processing: ~2s (12%)
```

---

## Data Flow Visualization

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          REQUEST DATA FLOW                               │
└──────────────────────────────────────────────────────────────────────────┘

INPUT (Frontend)
┌────────────────────────────────────────┐
│ {                                      │
│   query: "Show me dishes under $20    │
│            that are peanut-free",     │
│   user_id: "692e0fdb...",             │
│   restaurant_id: "rest_1"             │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
SESSION CREATION
┌────────────────────────────────────────┐
│ session_id = "sess_794b1625a0"        │
│                                        │
│ context = [                            │
│   {                                    │
│     user_allergens: ["Peanuts"],      │
│     message: "User is allergic to..." │
│   },                                   │
│   {                                    │
│     query: "pizza under $20",         │
│     menu_results: {...}               │
│   }                                    │
│ ]                                      │
└────────────────────────────────────────┘
              │
              ▼
CONTEXT RESOLVER
┌────────────────────────────────────────┐
│ rewritten_query:                       │
│   "Show me dishes under $20            │
│    that are peanut-free"               │
│                                        │
│ current_context:                       │
│   "User allergic to peanuts,          │
│    previously searched pizza..."      │
└────────────────────────────────────────┘
              │
              ▼
INTENT CLASSIFIER
┌────────────────────────────────────────┐
│ intents: {                             │
│   menu_search: [                       │
│     "Show me dishes under $20          │
│      that are peanut-free"            │
│   ],                                   │
│   dish_info: [],                       │
│   user_preferences: [],                │
│   irrelevant: []                       │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
QUERY PART GENERATOR
┌────────────────────────────────────────┐
│ query_parts: {                         │
│   menu_search: [...],                  │
│   dish_info: [],                       │
│   user_preferences: []                 │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
MENU RETRIEVER (4 Stages)
┌────────────────────────────────────────┐
│ STAGE 1: Search Terms                 │
│ {                                      │
│   positive: [                          │
│     "dishes under $20",               │
│     "affordable dishes"               │
│   ],                                   │
│   negative: []                         │
│ }                                      │
├────────────────────────────────────────┤
│ STAGE 2: Vector Search                │
│ candidates = [                         │
│   dish_14 (score: 0.89),              │
│   dish_8  (score: 0.85),              │
│   dish_4  (score: 0.82),              │
│   ...                                  │
│ ]                                      │
├────────────────────────────────────────┤
│ STAGE 3: Structured Filters            │
│ {                                      │
│   price: {max: 20, min: 0},           │
│   allergens: {exclude: ["peanuts"]},  │
│   ingredients: {...},                  │
│   nutrition: {}                        │
│ }                                      │
├────────────────────────────────────────┤
│ STAGE 4: LLM Filtering                 │
│ [                                      │
│   {dish_14, include: true},           │
│   {dish_8,  include: false},          │
│   {dish_4,  include: false}           │
│ ]                                      │
└────────────────────────────────────────┘
              │
              ▼
MENU RESULTS
┌────────────────────────────────────────┐
│ menu_results: {                        │
│   "Show me dishes...": [              │
│     {                                  │
│       dish_id: "dish_14",             │
│       dish_name: "Margherita Pizza",  │
│       price: 15.99,                   │
│       allergens: ["dairy","gluten"],  │
│       nutrition_facts: {              │
│         calories: {value: 750},       │
│         protein: {value: 28}          │
│       }                                │
│     }                                  │
│   ]                                    │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
INFO RETRIEVER (Empty)
┌────────────────────────────────────────┐
│ info_results: {                        │
│   info_results: {}                     │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
PREFERENCES RETRIEVER (Empty)
┌────────────────────────────────────────┐
│ preference_results: {                  │
│   preference_results: {}               │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
RESPONSE FORMATTER
┌────────────────────────────────────────┐
│ response:                              │
│   "I found 1 dish matching             │
│    your search!"                       │
│                                        │
│ status: "success"                      │
└────────────────────────────────────────┘
              │
              ▼
SAVE TO DATABASE
┌────────────────────────────────────────┐
│ MongoDB: chat_states.insert_one({      │
│   _id: ObjectId(...),                  │
│   user_id: "692e0fdb...",             │
│   session_id: "sess_794b1625a0",      │
│   query: "Show me dishes...",         │
│   menu_results: {...},                 │
│   response: "I found 1 dish...",      │
│   timestamp: "2025-12-02T03:04:41"    │
│ })                                     │
└────────────────────────────────────────┘
              │
              ▼
OUTPUT (Backend → Frontend)
┌────────────────────────────────────────┐
│ {                                      │
│   menu_results: {...},                 │
│   info_results: {...},                 │
│   preference_results: {...},           │
│   response: "I found 1 dish...",      │
│   status: "success"                    │
│ }                                      │
└────────────────────────────────────────┘
              │
              ▼
FRONTEND RENDERING
┌────────────────────────────────────────┐
│ ┌────────────────────────────────────┐│
│ │ 🤖 Assistant                       ││
│ │ I found 1 dish matching your       ││
│ │ search! 🍽️                         ││
│ │                                    ││
│ │ ┌────────────────────────────────┐││
│ │ │ Margherita Pizza      $15.99   │││
│ │ │                                │││
│ │ │ Classic pizza with tomato...   │││
│ │ │                                │││
│ │ │ Allergens: [dairy] [gluten]    │││
│ │ │ Nutrition: 750 cal • 28g pro   │││
│ │ └────────────────────────────────┘││
│ └────────────────────────────────────┘│
└────────────────────────────────────────┘
```

---

## Component Interaction Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SAFEBITES COMPONENT INTERACTIONS                     │
└─────────────────────────────────────────────────────────────────────────┘

Frontend Components
├── App.tsx (Router)
│   ├── Welcome.tsx
│   ├── Login.tsx
│   │   └─► POST /users/login → user_router.py
│   ├── SignUp.tsx
│   │   └─► POST /users/register → user_router.py
│   ├── Dashboard.tsx
│   │   └─► GET /restaurants/ → restaurant_router.py
│   ├── Home.tsx
│   ├── SearchChat.tsx ⭐
│   │   ├─► POST /restaurants/search → restaurant_router.py
│   │   └─► GET /restaurants/history/{user_id}/{restaurant_id}
│   ├── Settings.tsx
│   │   └─► PATCH /users/{user_id}/allergens → user_router.py
│   └── RestaurantDetails.tsx
│       └─► GET /restaurants/{restaurant_id} → restaurant_router.py

Backend Routers
├── restaurant_router.py
│   ├── POST /search
│   │   ├─► state_service.get_or_create_session()
│   │   ├─► state_service.rebuild_context()
│   │   ├─► create_chat_graph().invoke()
│   │   └─► state_service.save_chat_state()
│   ├── GET /history/{user_id}/{restaurant_id}
│   │   └─► state_service.get_chat_history()
│   └── CRUD endpoints
│       └─► restaurant_service.*()
├── user_router.py
│   ├── POST /register → user_service.create_user()
│   ├── POST /login → user_service.authenticate()
│   └── PATCH /{user_id}/allergens → user_service.update_allergens()
└── admin_router.py
    └── Management tools

Backend Services
├── state_service.py
│   ├─► MongoDB: chat_states (find, insert)
│   ├─► MongoDB: users (find)
│   └─► Returns: session_id, context, chat_history
├── restaurant_service.py
│   ├─► MongoDB: restaurants (CRUD)
│   ├─► MongoDB: dishes (CRUD)
│   └─► faiss_service.build_index()
├── user_service.py
│   └─► MongoDB: users (CRUD)
├── context_resolver.py
│   └─► OpenAI: gpt-4o-mini (query rewriting)
├── intent_service.py
│   └─► OpenAI: gpt-4o-mini (intent classification)
├── retrieval_service.py
│   ├─► OpenAI: gpt-4o-mini (search terms, filters, filtering)
│   ├─► OpenAI: text-embedding-ada-002 (embeddings)
│   └─► faiss_service.vector_search()
├── faiss_service.py
│   ├─► OpenAI: text-embedding-ada-002 (dish embeddings)
│   ├─► FAISS: index.search()
│   └─► MongoDB: dishes (document retrieval)
├── dish_info_service.py
│   └─► MongoDB: dishes (find by dish_id)
├── user_preferences_service.py
│   └─► MongoDB: users (allergen_preferences)
└── response_synthesizer_tool.py
    └─► Aggregates: menu_results, info_results, preference_results

LangGraph Flow
├── graph.py (create_chat_graph)
│   ├── NODE 1: resolve_context (context_resolver.py)
│   ├── NODE 2: classify_intent (intent_service.py)
│   ├── NODE 3: generate_query_parts (inline)
│   ├── NODE 4: retrieve_menu (retrieval_service.py)
│   ├── NODE 5: retrieve_info (dish_info_service.py)
│   ├── NODE 6: retrieve_preferences (user_preferences_service.py)
│   └── NODE 7: format_response (response_synthesizer_tool.py)
└── state.py (ChatState model)

External Services
├── OpenAI API
│   ├── gpt-4o-mini-2024-07-18 (chat completions)
│   └── text-embedding-ada-002 (embeddings)
└── MongoDB Atlas
    ├── users collection
    ├── restaurants collection
    ├── dishes collection
    └── chat_states collection
```

---

**Generated**: 2025-12-02
**Purpose**: Visual reference for SafeBites architecture and data flow
