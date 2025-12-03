# SafeBites Architecture Documentation

**Generated**: December 2, 2025

This folder contains comprehensive documentation explaining how the SafeBites backend and frontend work together.

---

## 📚 What's Inside

### 1. **[WORKFLOW_EXPLANATION.md](./WORKFLOW_EXPLANATION.md)** ⭐ START HERE
**Complete end-to-end workflow** tracing a real user query from frontend to backend and back.

**Contents**:
- High-level system overview
- Detailed step-by-step flow (7 stages)
- LangGraph pipeline breakdown (7 nodes)
- Database interactions
- LLM API calls with token counts
- Data transformations at each stage
- Real log examples from your system

**Best for**: Understanding how everything connects together

---

### 2. **[VISUAL_FLOW_DIAGRAM.md](./VISUAL_FLOW_DIAGRAM.md)**
**ASCII diagrams and visual representations** of the entire system architecture.

**Contents**:
- Complete system architecture diagram
- Query processing timeline (17 seconds breakdown)
- Data flow visualization (input → output)
- Component interaction map
- Service dependency graph

**Best for**: Getting a visual overview of the system

---

### 3. **[FILE_REFERENCE.md](./FILE_REFERENCE.md)**
**Complete file listing** with locations, line numbers, and purposes.

**Contents**:
- Directory structure
- Frontend files (10 pages)
- Backend files (routers, services, models)
- Key code locations with line numbers
- Database schema
- How to navigate the codebase
- How to trace a search query
- How to add new features

**Best for**: Finding specific files and code locations

---

## 🎯 Quick Start Guide

### Understanding Your System

1. **If you're new to the project**:
   - Read [WORKFLOW_EXPLANATION.md](./WORKFLOW_EXPLANATION.md) sections 1-2
   - Look at [VISUAL_FLOW_DIAGRAM.md](./VISUAL_FLOW_DIAGRAM.md) architecture diagram
   - Bookmark [FILE_REFERENCE.md](./FILE_REFERENCE.md) for reference

2. **If you're debugging**:
   - Use [WORKFLOW_EXPLANATION.md](./WORKFLOW_EXPLANATION.md) to trace the exact flow
   - Check the "Query Processing Timeline" in [VISUAL_FLOW_DIAGRAM.md](./VISUAL_FLOW_DIAGRAM.md)
   - Find code locations in [FILE_REFERENCE.md](./FILE_REFERENCE.md)

3. **If you're adding features**:
   - See "Adding a New Feature" in [FILE_REFERENCE.md](./FILE_REFERENCE.md)
   - Study the LangGraph pipeline in [WORKFLOW_EXPLANATION.md](./WORKFLOW_EXPLANATION.md)
   - Understand data transformations in [VISUAL_FLOW_DIAGRAM.md](./VISUAL_FLOW_DIAGRAM.md)

---

## 🔍 Key Insights from the Documentation

### System Architecture

**7-Layer Stack**:
1. Frontend (React) → `SearchChat.tsx`
2. API Router (FastAPI) → `restaurant_router.py`
3. Session Management → `state_service.py`
4. LangGraph Pipeline (7 nodes) → `flow/graph.py`
5. Vector Search (FAISS) → `faiss_service.py`
6. Database (MongoDB) → 4 collections
7. External APIs (OpenAI) → GPT-4o-mini + embeddings

### Request Flow

**10 Steps**:
1. User input → SearchChat.tsx
2. POST /restaurants/search → restaurant_router.py
3. Get/create session → state_service.py
4. Rebuild context → MongoDB (users, chat_states)
5. Start LangGraph → graph.py
6. Context resolver → GPT-4o-mini
7. Intent classifier → GPT-4o-mini
8. Menu retriever → FAISS + GPT-4o-mini (4 LLM calls)
9. Response formatter → Aggregate results
10. Save & return → MongoDB + JSON response

### Performance

**Total Time**: ~17 seconds for complex query
- LLM Calls: ~14s (82%)
- Database: ~1s (6%)
- Processing: ~2s (12%)

**LLM Usage**: 6-7 calls per query
- Total tokens: ~5,800 input + ~370 output
- Cost: ~$0.01 per query

---

## 📊 System Components

### Frontend (React + TypeScript)

**10 Pages**:
- Welcome, Login, SignUp, Dashboard
- Home, **SearchChat** ⭐, Settings
- RestaurantDetails, Profile, Admin

**Key File**: `SearchChat.tsx` (453 lines)
- Handles user input
- Sends API requests
- Renders dish cards with allergens/nutrition

### Backend (FastAPI + Python)

**3 Routers**:
- restaurant_router.py (13+ endpoints)
- user_router.py (auth + profile)
- admin_router.py (management)

**9 Services**:
- state_service.py (session management)
- context_resolver.py (query rewriting)
- intent_service.py (classification)
- retrieval_service.py (menu search) ⭐
- faiss_service.py (vector search)
- dish_info_service.py (dish details)
- user_preferences_service.py (allergens)
- response_synthesizer_tool.py (aggregation)
- restaurant_service.py (CRUD)

**LangGraph Pipeline**: 7 nodes
1. Context Resolver
2. Intent Classifier
3. Query Part Generator
4. Menu Retriever ⭐ (core search)
5. Info Retriever
6. Preferences Retriever
7. Response Formatter

### Database (MongoDB)

**4 Collections**:
- **users**: Accounts + allergen_preferences
- **restaurants**: Restaurant metadata
- **dishes**: Menu items + embeddings (1536-dim)
- **chat_states**: Conversation history

### External Services

**OpenAI**:
- gpt-4o-mini-2024-07-18 (chat completions)
- text-embedding-ada-002 (embeddings)

**FAISS**:
- In-memory vector indexes per restaurant
- Cosine similarity search
- Top-K retrieval (K=10)

---

## 🛠️ How the Search Works

### Example Query: "Show me dishes under $20 that are peanut-free"

**Stage 1: Session Creation**
- Get/create session ID: `sess_794b1625a0`
- Fetch user allergens: `["Peanuts"]`
- Fetch last 5 queries from history

**Stage 2: Context Resolver**
- Input: Original query
- Action: GPT-4o-mini rewrites with context
- Output: "Show me dishes under $20 that are peanut-free" (unchanged)

**Stage 3: Intent Classifier**
- Input: Rewritten query
- Action: GPT-4o-mini classifies intent type
- Output: `menu_search: ["Show me dishes under $20..."]`

**Stage 4: Menu Retriever** (4 sub-stages)
1. **Generate search terms**: GPT-4o-mini → `["dishes under $20", "affordable"]`
2. **Vector search**: FAISS → 3 embedding calls → Top 10 dishes
3. **Extract filters**: GPT-4o-mini → `{price: {max: 20}, allergens: {exclude: ["peanuts"]}}`
4. **Filter dishes**: GPT-4o-mini evaluates each dish
   - ✓ dish_14 (Margherita Pizza): Under $20, no peanuts
   - ✗ dish_8: Over $20
   - ✗ dish_4: Contains almonds

**Stage 5: Response Formatter**
- Aggregates results
- Generates text: "I found 1 dish matching your search!"

**Stage 6: Save & Return**
- Saves to MongoDB chat_states
- Returns JSON with menu_results

**Stage 7: Frontend Rendering**
- Parses menu_results
- Renders dish card with:
  - Name: "Margherita Pizza"
  - Price: $15.99
  - Allergens: [dairy, gluten]
  - Nutrition: 750 cal, 28g protein

---

## 📁 File Locations

### Critical Files

**Frontend**:
- Main chat UI: `/frontend/src/pages/SearchChat.tsx`
- API config: `/frontend/src/config/api.ts`

**Backend**:
- Entry point: `/backend/app/main.py`
- Search endpoint: `/backend/app/routers/restaurant_router.py:70-98`
- Pipeline: `/backend/app/flow/graph.py:12-60`
- Session mgmt: `/backend/app/services/state_service.py`
- Menu search: `/backend/app/services/retrieval_service.py:85-150`
- Vector search: `/backend/app/services/faiss_service.py:45-80`

**Database**:
- Connection: `/backend/app/utils/database.py`
- Models: `/backend/app/models/`

---

## 🔧 Debugging Guide

### Frontend Issues

**Check**:
1. Browser console for errors
2. Network tab for API responses
3. `localStorage.getItem("authToken")` for user_id

**Common Issues**:
- CORS errors → Check CORS middleware in `main.py`
- 404 errors → Verify `API_BASE_URL` in `config/api.ts`
- Empty results → Check `menu_results` object structure

### Backend Issues

**Check**:
1. Terminal logs for errors
2. `/backend/logs/llm_usage.csv` for LLM calls
3. MongoDB for saved chat_states

**Common Issues**:
- MongoDB connection → Check `.env` MONGODB_URI
- OpenAI errors → Check `.env` OPENAI_API_KEY
- FAISS not found → Check index building in `main.py` startup

### Pipeline Issues

**Trace the flow**:
1. Context resolver: Check if query is rewritten correctly
2. Intent classifier: Verify intents are classified as `menu_search`
3. Menu retriever: Check FAISS search returns candidates
4. Filter step: Verify LLM filtering logic

**Log locations**:
- Context resolver: `logger.debug("Rewritten Query:", ...)`
- Menu retriever: `logger.info("Processing X menu search queries...")`
- Filters: `logger.debug("Filters:", ...)`

---

## 🚀 Adding New Features

### Add New Intent Type

1. Update `intent_service.py` to recognize new type
2. Add new retriever node in `graph.py`
3. Create service in `/backend/app/services/new_retriever.py`
4. Add edge in graph: `graph.add_edge("query_part_generator", "new_retriever")`

### Add New Filter

1. Update `retrieval_service.py` filter extraction
2. Modify prompt to extract new filter type
3. Update filtering logic to handle new constraint

### Add New Page

1. Create `/frontend/src/pages/NewPage.tsx`
2. Add route in `/frontend/src/App.tsx`:
   ```typescript
   <Route path="/new" element={<NewPage />} />
   ```
3. Add navigation link in header/sidebar

---

## 📖 Further Reading

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **FAISS Docs**: https://faiss.ai/
- **OpenAI API**: https://platform.openai.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Router**: https://reactrouter.com/

---

## 🗑️ Deleting This Folder

This is a **temporary documentation folder**. You can safely delete it once you've reviewed the content:

```bash
rm -rf /home/samarth/CSC_510_Proj3/proj2/SafeBites/temp_readme
```

Or keep it for reference during development.

---

## 📝 Summary

This documentation provides a complete picture of how SafeBites works:

1. **WORKFLOW_EXPLANATION.md** - The detailed walkthrough
2. **VISUAL_FLOW_DIAGRAM.md** - Visual diagrams
3. **FILE_REFERENCE.md** - File locations and code
4. **README.md** (this file) - Navigation guide

Together, these files explain:
- How user queries flow from frontend → backend → database → LLM → response
- Where each piece of code lives
- How to debug issues
- How to add new features

**Start with WORKFLOW_EXPLANATION.md** and use the others as reference!

---

**Questions?**
- Check the existing backend documentation: `/backend/devDocs/BACKEND_ARCHITECTURE.md`
- Review the code comments in each service
- Trace the logs in your terminal output

**Generated by**: Claude Code
**Date**: 2025-12-02
**Based on**: Real system logs and code analysis
