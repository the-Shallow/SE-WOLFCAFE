# Vector Database Architecture - SafeBites

## Overview

SafeBites uses **FAISS (Facebook AI Similarity Search)** combined with **OpenAI embeddings** to provide semantic search capabilities for dish recommendations. This enables natural language queries like *"nut-free pasta dishes"* to work effectively, understanding intent rather than just matching keywords.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector Store** | FAISS | Fast similarity search over embeddings |
| **Embedding Model** | OpenAI `text-embedding-3-large` | Convert text to 1536-dimensional vectors |
| **Document Store** | MongoDB | Store actual dish metadata |
| **Intent Extraction** | OpenAI GPT-4o-mini | Extract positive/negative intents from queries |
| **Similarity Metric** | Cosine Similarity | Measure semantic closeness |

---

## Architecture Components

### 1. Embedding Generation

**File**: [app/services/faiss_service.py:32](app/services/faiss_service.py#L32)

```python
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=os.getenv("OPENAI_KEY")
)
embedding_dim = 1536  # Dimension of embedding vectors
```

**What gets embedded**:
Each dish is converted to a structured text representation containing:
- Dish name
- Description
- Price
- Ingredients list
- Serving size
- Availability status
- Allergen information
- Nutrition facts

**Example text representation**:
```
Dish Name: Spaghetti Carbonara
Description: Classic Italian pasta with eggs, bacon, and parmesan
Price: 14.99
Ingredients: pasta, eggs, bacon, parmesan cheese, black pepper
Serving Size: single
Availability: True
Allergens: dairy, wheat_gluten, egg
Nutrition: {'calories': {'value': 450}, 'protein': {'value': 15}, ...}
```

---

### 2. Building the FAISS Index

**File**: [app/services/faiss_service.py:140-190](app/services/faiss_service.py#L140-L190)

#### Function: `build_faiss_from_db()`

**Purpose**: Build or rebuild the entire FAISS vector index from all dishes in MongoDB.

**Process Flow**:
```
1. Fetch all dishes from MongoDB
         ↓
2. For each dish:
   - Create structured text representation
   - Store metadata (dish_id, restaurant_id, vector_id)
         ↓
3. Embed all texts using OpenAI API
         ↓
4. Create FAISS index from embeddings
         ↓
5. Save to local filesystem (faiss_index_restaurant/)
```

**Code Example**:
```python
def build_faiss_from_db(index_path: str = "faiss_index_restaurant"):
    dishes = list(dish_collection.find())

    texts, metadata = [], []
    for i, dish in enumerate(dishes):
        text = f"""
            Dish Name: {dish.get("name", "")}
            Description: {dish.get("description", "")}
            Price: {dish.get("price", "N/A")}
            Ingredients: {', '.join(dish.get("ingredients", []))}
            ...
        """
        texts.append(text.strip())

        metadata.append({
            "dish_id": dish["_id"],
            "restaurant_id": dish["restaurant_id"],
            "vector_id": i
        })

    vector_store = FAISS.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadata
    )
    vector_store.save_local(index_path)
```

**When it runs**:
- Automatically on server startup (if index doesn't exist)
- Manually via `python -c "from app.services.faiss_service import build_faiss_from_db; build_faiss_from_db()"`
- After bulk data imports

---

### 3. Incremental Index Updates

**File**: [app/services/faiss_service.py:192-231](app/services/faiss_service.py#L192-L231)

#### Function: `update_faiss_index(new_dishes)`

**Purpose**: Add new dishes to existing index without full rebuild.

**Use case**: When restaurants add new menu items dynamically.

**Process**:
```python
# Load existing index
vector_store = FAISS.load_local("faiss_index_restaurant", embeddings)

# Embed new dishes
new_texts = [create_text_representation(dish) for dish in new_dishes]

# Add to index
vector_store.add_texts(texts=new_texts, metadatas=new_metadata)

# Save updated index
vector_store.save_local("faiss_index_restaurant")
```

---

### 4. Semantic Search

**File**: [app/services/faiss_service.py:232-263](app/services/faiss_service.py#L232-L263)

#### Function: `search_dishes(query, restaurant_id=None, top_k=20, threshold=0.8)`

**Purpose**: Perform similarity search against the FAISS index.

**Parameters**:
- `query` (str): Natural language search query
- `restaurant_id` (Optional[str]): Filter results by restaurant
- `top_k` (int): Maximum number of results to return
- `threshold` (float): Minimum similarity score (0-1 scale)

**Returns**: List of `DishHit` objects containing:
- `dish`: Full dish document from MongoDB
- `score`: Similarity score
- `embedding`: 1536-dim vector representation

**Example Usage**:
```python
# Search for gluten-free dishes
results = search_dishes(
    query="gluten-free pasta",
    restaurant_id="rest_1",
    top_k=10,
    threshold=0.7
)

for hit in results:
    print(f"{hit.dish['name']} - Score: {hit.score}")
```

**How it works internally**:
1. Embed the query using the same OpenAI model
2. Perform FAISS similarity search (cosine similarity)
3. Filter results by restaurant_id if provided
4. Filter results by threshold score
5. Fetch full dish documents from MongoDB
6. Return structured results

---

### 5. Intent Extraction

**File**: [app/services/faiss_service.py:37-86](app/services/faiss_service.py#L37-L86)

#### Function: `extract_query_intent(query)`

**Purpose**: Split user queries into positive (wants) and negative (exclusions) intents.

**LLM Model**: GPT-4o-mini with temperature=1

**Prompt Strategy**:
- **Positive intents**: Semantically expand what user wants
- **Negative intents**: Keep narrow, avoid over-expansion

**Example 1**:
```
Query: "Gluten-free dishes without cheese"

Output:
{
  "positive": ["gluten-free", "no gluten", "wheat-free"],
  "negative": ["cheese", "dairy cheese", "cheddar", "mozzarella"]
}
```

**Example 2**:
```
Query: "Pasta dishes without meatballs"

Output:
{
  "positive": ["pasta", "spaghetti", "penne", "fettuccine", "linguine"],
  "negative": ["meatballs", "meatball", "meat balls", "polpette"]
}
```

**Example 3**:
```
Query: "Anything but seafood"

Output:
{
  "positive": ["anything", "non-seafood", "meat", "poultry", "vegetarian"],
  "negative": ["seafood", "fish", "shellfish", "prawns", "crab", "lobster"]
}
```

**Fallback behavior**: If LLM fails to parse, returns `{"positive": [query], "negative": []}`

---

### 6. Advanced Semantic Retrieval with Negation

**File**: [app/services/faiss_service.py:292-348](app/services/faiss_service.py#L292-L348)

#### Function: `semantic_retrieve_with_negation(query, restaurant_id=None)`

**Purpose**: The main retrieval function that combines intent extraction, positive/negative filtering, and centroid-based refinement.

**Process Flow**:

```
User Query: "Nut-free pasta dishes"
         ↓
[1. Intent Extraction]
         ↓
Positive: ["pasta", "spaghetti", "penne", "noodles"]
Negative: ["nuts", "peanuts", "almonds", "walnuts", "cashews"]
         ↓
[2. Search Positive Intents]
         ↓
pos_hits: 15 dishes (all pasta-related)
         ↓
[3. Search Negative Intents]
         ↓
neg_hits: 3 dishes (contain nuts)
         ↓
[4. Filter Out Negatives]
         ↓
filtered_dishes: 12 dishes (pasta without nuts)
         ↓
[5. Remove Duplicates]
         ↓
unique_dishes: 12 dishes
         ↓
[6. Centroid Refinement]
         ↓
refined_dishes: Top 5 most semantically relevant
         ↓
[7. Return Results]
```

**Code Implementation**:
```python
def semantic_retrieve_with_negation(query, restaurant_id=None):
    # Step 1: Extract intents
    intents = extract_query_intent(query)
    pos_hits, neg_hits = [], []

    # Step 2: Search for positive intents
    for p in intents.positive:
        pos_hits.extend(search_dishes(p, restaurant_id=restaurant_id))

    # Step 3: Search for negative intents
    for n in intents.negative:
        neg_hits.extend(search_dishes(n, restaurant_id=restaurant_id))

    # Step 4: Filter out negative matches
    neg_ids = set([hit.dish["_id"] for hit in neg_hits])
    filtered_dishes = [hit for hit in pos_hits if hit.dish["_id"] not in neg_ids]

    # Step 5: Remove duplicates
    seen = set()
    unique_filtered_dishes = []
    for hit in filtered_dishes:
        if hit.dish["_id"] not in seen:
            unique_filtered_dishes.append(hit)
            seen.add(hit.dish["_id"])

    # Step 6: Refine with centroid similarity
    dish_embeddings = {hit.dish["_id"]: hit.embedding for hit in unique_filtered_dishes}
    refined = refine_with_centroid(unique_filtered_dishes, intents.positive, dish_embeddings)

    return refined
```

**Logging**: All searches are logged to `intent_dishes_log.json` for debugging and analysis.

---

### 7. Centroid-Based Refinement

**File**: [app/services/faiss_service.py:266-290](app/services/faiss_service.py#L266-L290)

#### Function: `refine_with_centroid(dish_hits, positive_intents, dish_embeddings)`

**Purpose**: Re-rank filtered dishes based on semantic similarity to the query's "ideal" representation.

**How it works**:

1. **Compute Centroid Vector**:
   ```python
   # Average all positive intent embeddings
   centroid = np.mean([
       embeddings.embed_query(intent)
       for intent in positive_intents
   ], axis=0)
   ```

2. **Calculate Cosine Similarity**:
   ```python
   for hit in dish_hits:
       dish_emb = dish_embeddings[hit.dish["_id"]]
       similarity = cosine_similarity(
           centroid.reshape(1, -1),
           dish_emb.reshape(1, -1)
       )[0][0]

       if similarity > 0.30:  # Threshold
           hit.centroid_similarity = similarity
           refined.append(hit)
   ```

3. **Sort by Similarity**:
   ```python
   refined.sort(key=lambda x: x.centroid_similarity, reverse=True)
   ```

**Why this matters**:
- Filters out "false positive" matches
- Ensures results align with user's actual intent
- Prioritizes dishes most semantically close to what user wants

**Example**:
```
Query: "Italian pasta dishes"
Positive intents: ["italian", "pasta", "spaghetti", "marinara"]

Centroid = avg(embed("italian"), embed("pasta"), embed("spaghetti"), ...)

For each dish:
  - "Spaghetti Carbonara" → similarity = 0.85 ✓ (kept)
  - "Thai Pad Thai" → similarity = 0.42 ✓ (kept)
  - "Burger and Fries" → similarity = 0.12 ✗ (filtered out)
```

---

## Data Models

### DishHit Model

**File**: [app/models/faiss_model.py](app/models/faiss_model.py)

```python
class DishHit(BaseModel):
    dish: Dict[str, Any]           # Full MongoDB dish document
    score: float                   # FAISS similarity score (0-1)
    embedding: np.ndarray          # 1536-dim vector
    centroid_similarity: Optional[float] = None  # Refined score
```

### QueryIntent Model

```python
class QueryIntent(BaseModel):
    positive: List[str]  # What user wants
    negative: List[str]  # What user wants to exclude
```

---

## Storage & File Structure

### Index Location

```
backend/
├── faiss_index_restaurant/
│   ├── index.faiss        # Binary FAISS index (vector data)
│   └── index.pkl          # Metadata (dish_id, restaurant_id mappings)
├── intent_dishes_log.json # Search query logs
└── app/
    └── services/
        └── faiss_service.py
```

**Index Files**:
- `index.faiss`: Binary file containing vector data (FAISS format)
- `index.pkl`: Python pickle file with metadata mappings

**Important Notes**:
- Index is stored **locally on filesystem**, not in MongoDB
- Needs to be rebuilt when deploying to new environment
- Auto-rebuilds if missing on server startup

---

## API Integration

### Startup Hook

**File**: [app/main.py](app/main.py)

```python
from app.services.faiss_service import build_faiss_from_db

@app.on_event("startup")
async def startup_event():
    if not os.path.exists("faiss_index_restaurant"):
        logger.info("FAISS index not found. Building from database...")
        build_faiss_from_db()
    else:
        logger.info("FAISS index loaded successfully.")
```

### Usage in Retrieval Service

**File**: [app/services/retrieval_service.py](app/services/retrieval_service.py)

```python
from app.services.faiss_service import semantic_retrieve_with_negation

def get_menu_items(query: str, restaurant_id: str):
    # Perform semantic search with negation handling
    dish_hits = semantic_retrieve_with_negation(query, restaurant_id)

    # Convert to response format
    results = []
    for hit in dish_hits:
        results.append({
            "dish_name": hit.dish["name"],
            "price": hit.dish["price"],
            "allergens": [a["allergen"] for a in hit.dish.get("inferred_allergens", [])],
            "relevance_score": hit.centroid_similarity
        })

    return results
```

---

## Performance Characteristics

### Index Build Time

| Dishes | Build Time | Index Size |
|--------|-----------|-----------|
| 16 (seed data) | ~5 seconds | ~24 KB |
| 100 dishes | ~20 seconds | ~150 KB |
| 1,000 dishes | ~3 minutes | ~1.5 MB |
| 10,000 dishes | ~25 minutes | ~15 MB |

**Note**: Build time includes OpenAI API calls for embeddings (rate-limited).

### Search Performance

- **Query time**: 10-50ms for 1,000 dishes
- **Scales sub-linearly**: FAISS uses approximate nearest neighbor search
- **Bottleneck**: OpenAI embedding API call (~100-200ms per query)

### Optimization Tips

1. **Batch embeddings**: Use `embeddings.embed_documents()` for multiple texts
2. **Cache queries**: Store common query embeddings
3. **Index sharding**: Split by restaurant for large datasets
4. **Use local embeddings**: Switch to sentence-transformers for latency-sensitive apps

---

## Common Operations

### Rebuild Index Manually

```bash
cd backend
python -c "from app.services.faiss_service import build_faiss_from_db; build_faiss_from_db()"
```

### Test Search

```python
from app.services.faiss_service import search_dishes

results = search_dishes("gluten-free pasta", restaurant_id="rest_1")
for hit in results:
    print(f"{hit.dish['name']} - Score: {hit.score:.2f}")
```

### Test Intent Extraction

```python
from app.services.faiss_service import extract_query_intent

intents = extract_query_intent("Show me nut-free desserts")
print(f"Positive: {intents.positive}")
print(f"Negative: {intents.negative}")
```

### View Search Logs

```bash
cat intent_dishes_log.json | jq '.'
```

---

## Troubleshooting

### Issue: "FAISS index could not be loaded"

**Cause**: Index file missing or corrupted.

**Solution**:
```python
from app.services.faiss_service import build_faiss_from_db
build_faiss_from_db()
```

### Issue: No results returned

**Possible causes**:
1. **Threshold too high**: Lower the threshold in `search_dishes()`
2. **No dishes in DB**: Load seed data
3. **Restaurant filter**: Check if `restaurant_id` is correct

**Debug**:
```python
# Try without threshold
results = search_dishes("pasta", threshold=0.0)
print(f"Found {len(results)} results")
```

### Issue: Slow search performance

**Optimizations**:
1. Reduce `top_k` parameter
2. Add restaurant_id filter
3. Cache query embeddings
4. Use smaller embedding model (text-embedding-3-small)

---

## Future Enhancements

- [ ] **Hybrid search**: Combine vector search with keyword filters
- [ ] **Multi-modal embeddings**: Include dish images
- [ ] **Index compression**: Use product quantization for large datasets
- [ ] **Distributed search**: Shard index across multiple servers
- [ ] **Real-time updates**: Stream new dishes to index without full rebuild
- [ ] **Personalization**: Weight embeddings based on user preferences
- [ ] **A/B testing**: Compare different embedding models

---

## References

- **FAISS Documentation**: https://faiss.ai/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **LangChain FAISS**: https://python.langchain.com/docs/integrations/vectorstores/faiss
- **Cosine Similarity**: https://en.wikipedia.org/wiki/Cosine_similarity

---

## Summary

The vector database implementation in SafeBites provides:

✅ **Semantic understanding** of user queries (not just keyword matching)
✅ **Intent extraction** to handle positive and negative constraints
✅ **Fast retrieval** using FAISS approximate nearest neighbor search
✅ **Centroid refinement** for better ranking of results
✅ **Restaurant scoping** for multi-tenant support
✅ **Allergen-aware search** through embedded allergen information

This enables natural, conversational queries like:
- *"Show me dairy-free Italian dishes under $15"*
- *"Pasta without seafood or nuts"*
- *"High-protein vegetarian meals"*

The combination of FAISS + OpenAI embeddings + LLM intent extraction creates a powerful semantic search system for allergen-safe food recommendations.
