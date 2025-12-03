"""
FAISS Vector Store & Semantic Retrieval Module

This module provides functionality to embed, index, and semantically search
dish data using OpenAI embeddings and FAISS.
"""
import logging
from datetime import datetime
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
import os,json
import numpy as np
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from ..utils.llm_tracker import LLMUsageTracker
from pymongo import MongoClient
from ..models.faiss_model import DishHit, QueryIntent
from ..models.exception_model import GenericException

logger = logging.getLogger(__name__)

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
dish_collection = db["dishes"]


embeddings = OpenAIEmbeddings(model="text-embedding-3-large",openai_api_key=os.getenv("OPENAI_KEY"))
embedding_dim = 1536
llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"),callbacks=[LLMUsageTracker()])
    

def extract_query_intent(query):
    """
    Extract positive and negative intents from a user query.

    Args:
        query (str): User natural language query.

    Returns:
        QueryIntents: Positive and negative intents.

    Notes:
        Falls back to {"positive": [query], "negative": []} if LLM fails.
    """
    logging.debug(f"Extracting intents for query: {query}")

    intent_prompt = ChatPromptTemplate.from_template("""
        You are an intent extraction expert for food-related natural language queries.

        Your job is to split the query into two lists:
        1. **Positive intents** — what the user explicitly wants or is open to.
        - Expand this list semantically (include closely related dishes, cuisines, or styles).
        2. **Negative intents** — what the user explicitly wants to exclude or avoid.
        - DO NOT over-expand. Keep this list narrowly focused on the specific items, ingredients, or categories mentioned.
        - Avoid including loosely related or parent-category terms.
        - Only include synonyms or direct variants (e.g., "meatballs" → ["meatball", "meat balls", "polpette"], not "beef" or "meat").
        - **IMPORTANT**: For allergen-based exclusions (e.g., "nut-free", "dairy-free", "no peanuts"),
          DO NOT add allergens to the negative list. Leave negative list EMPTY for allergen queries.
          Allergen filtering will be handled by a separate filter system.

        Return the result as **valid JSON**:
        {{"positive": [...], "negative": [...]}}

        Example 1:
        Query: "Gluten-free dishes without cheese"
        Output: {{"positive": ["anything", "gluten-free"], "negative": ["cheese", "dairy cheese", "cheddar", "mozzarella"]}}

        Example 2:
        Query: "Pasta dishes without meatballs"
        Output: {{"positive": ["pasta dishes", "pasta", "spaghetti", "penne", "fettuccine"], "negative": ["meatballs", "meatball", "meat balls", "polpette"]}}

        Example 3:
        Query: "Anything but seafood"
        Output: {{"positive": ["anything", "non-seafood", "meat and poultry", "vegetarian", "vegan"], "negative": ["seafood", "fish", "shellfish", "prawns", "crab"]}}

        Example 4 (ALLERGEN QUERY):
        Query: "List nut-free dishes"
        Output: {{"positive": ["nut-free dishes", "dishes without nuts", "allergen-free"], "negative": []}}

        Example 5 (ALLERGEN QUERY):
        Query: "Show me dairy-free options"
        Output: {{"positive": ["dairy-free", "lactose-free", "non-dairy", "vegan"], "negative": []}}

        Query: {query}
    """)
    try:
        response =  llm.invoke(intent_prompt.format_messages(query=query))

        # Log the raw response for debugging
        logger.debug(f"Raw LLM response for query intent: {response.content}")

        # Check if response is empty
        if not response.content or not response.content.strip():
            logger.warning(f"Empty LLM response for query intent: {query}. Using fallback.")
            return QueryIntent(positive=[query], negative=[])

        # Try to extract JSON from markdown code blocks if present
        content = response.content.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        intents_json = json.loads(content)
        return QueryIntent(**intents_json)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in extract_query_intent. Response: {response.content[:500]}. Error: {str(e)}")
        logger.warning("Falling back to default positive intent")
        return QueryIntent(positive=[query], negative=[])
    except Exception as e:
        logging.error(f"Error in extract_query_intent: {str(e)}")
        return QueryIntent(positive=[query], negative=[])


def create_faiss_index(json_path = "./seed_data/dishes_refined.json"):
    """
    Build a FAISS vector store from dish data JSON.

    Args:
        json_path (str): Path to the dish JSON data.

    Raises:
        FileNotFoundError: If JSON file does not exist.
        GenericException: If index creation fails.
    """
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Dish data file not found: {json_path}")

    try:
        with open(json_path, "r",encoding="utf-8") as f:
            refined_dishes = json.load(f)
        texts,metadatas = [], []
        for i,dish in enumerate(refined_dishes):
            text = f"""
                Dish Name: {dish.get("name", "")}
                Description: {dish.get("description", "")}
                Price: {dish.get("price", "N/A")}
                Ingredients: {', '.join(dish.get("ingredients", []))}
                Serving Size: {dish.get("serving_size", "")}
                Availability: {dish.get("availability", True)}
                Allergens: {', '.join([a.get("allergen", "") for a in dish.get("explicit_allergens", [])])}
                Nutrition: {dish.get("nutrition_facts", {})}
            """
            texts.append(text)

            metadata = {
                "dish_id":dish["_id"],
                "restaurant_id":dish["restaurant_id"],
                "vector_id":i
            }

            metadatas.append(metadata)
        vector_store = FAISS.from_texts(
            texts=texts,
            embedding = embeddings,
            metadatas=metadatas,
        )

        vector_store.save_local("faiss_index_restaurant")
        logging.info("FAISS index created and saved locally.")
    except Exception as e:
        raise GenericException(f"FAISS index creation failed : {str(e)}")
    

def build_faiss_from_db(index_path:str = "faiss_index_restaurant"):
    """
    Build or rebuild the FAISS vector index from all dishes in the database.

    This function scans the `dishes` collection, extracts textual fields,
    embeds them using the configured embedding model, and stores them locally
    in a FAISS vector store for downstream RAG queries.

    Args:
        index_path (str): Directory path where the FAISS index will be saved.

    Raises:
        GenericException: If index creation or database retrieval fails.
    """
    try:
        logger.info("Startting FAISS index rebuild from database....")

        dishes = list(dish_collection.find())

        if not dishes:
            logger.warning("No dishes found in the database; FAISS index not created.")
            return
        
        texts, metadata = [], []

        for i, dish in enumerate(dishes):
            text = f"""
                Dish Name: {dish.get("name", "")}
                Description: {dish.get("description", "")}
                Price: {dish.get("price", "N/A")}
                Ingredients: {', '.join(dish.get("ingredients", []))}
                Availability: {dish.get("availability", True)}
                Allergens: {', '.join([a.get("allergen", "") for a in dish.get("explicit_allergens", [])])}
                Nutrition: {dish.get("nutrition_facts", {})}
            """
            texts.append(text.strip())

            metadata.append({
                "dish_id":dish["_id"],
                "restaurant_id":dish["restaurant_id"],
                "vector_id":i
            })

            vector_store = FAISS.from_texts(texts=texts,embedding = embeddings,metadatas=metadata)
            vector_store.save_local(index_path)

            logger.info(f"FAISS index successfully rebuilt with {len(dishes)} dishes.")
    except Exception as e:
        logger.error(f"Failed to build faiss index: {str(e)} ")
        raise GenericException(f"FAISS rebuild failed : {str(e)}")
    
def update_faiss_index(new_dishes,index_path="faiss_index_restaurant"):
    """
    Incrementally updates (or creates) a FAISS index with new dishes.
    """
    try:
        if os.path.exists(index_path):
            vector_store = FAISS.load_local(index_path, embeddings,allow_dangerous_deserialization=True)
        else:
            vector_store = None
        
        texts, metadata = [], []
        for i, dish in enumerate(new_dishes):
            text = f"""
                Dish Name: {dish.get("name", "")}
                Description: {dish.get("description", "")}
                Price: {dish.get("price", "N/A")}
                Ingredients: {', '.join(dish.get("ingredients", []))}
                Availability: {dish.get("availability", True)}
                Allergens: {', '.join([a.get("allergen", "") for a in dish.get("explicit_allergens", [])])}
                Nutrition: {dish.get("nutrition_facts", {})}
            """
            texts.append(text)

            metadata.append({
                "dish_id":dish["_id"],
                "restaurant_id":dish["restaurant_id"],
                "vector_id":i
            })

            if vector_store:
                vector_store.add_texts(texts=texts, metadatas=metadata)
            else:
                vector_store = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadata)
            
            vector_store.save_local(index_path)
            logging.info(f"FAISS index updated with {len(new_dishes)} dishes.")
    except Exception as e:
        logger.error(f"Failed to update FAISS index : {str(e)}")

def search_dishes(query, restaurant_id=None,top_k=20,threshold=0.8):
    """
    Perform similarity search using FAISS vector store.

    Args:
        query (str): Search query.
        restaurant_id (Optional[str]): Filter dishes by restaurant.
        top_k (int): Max number of results.
        threshold (float): Minimum similarity score to include.

    Returns:
        List[DishHit]: Filtered and structured dish hits.
    """
    try:
        vector_store = FAISS.load_local("faiss_index_restaurant", embeddings,allow_dangerous_deserialization=True)
    except Exception as e:
        raise GenericException("FAISS index could not be loaded.")

    filter_dict = {"restaurant_id":restaurant_id} if restaurant_id else None
    results = vector_store.similarity_search_with_score(query, k=top_k, filter=filter_dict)
    structured_res = []

    for res,score in results:
        if score >= threshold:
            dish = dish_collection.find_one({"_id":res.metadata["dish_id"]})
            if dish:
                structured_res.append(DishHit(
                    dish = dish,
                    score = score,
                    embedding = vector_store.index.reconstruct(res.metadata["vector_id"])
                ))
    return structured_res


def refine_with_centroid(dish_hits,positive_intents,dish_embeddings):
    """
    Refine retrieved dishes by comparing centroid similarity of positive intents.

    Args:
        dish_hits (List[DishHit]): Initial dish hits.
        positive_intents (List[str]): Positive intents extracted from query.
        dish_embeddings (Dict[str, np.ndarray]): Precomputed embeddings of dishes.

    Returns:
        List[DishHit]: Refined and sorted dish hits.
    """
    centroid = np.mean([embeddings.embed_query(intent) for intent in positive_intents],axis=0)
    logging.debug(f"Centroid computed for query intents : {centroid}")
    refined = []
    for hit in dish_hits:
        dish_emb = dish_embeddings.get(hit.dish["_id"])
        if dish_emb is not None:
            sim = cosine_similarity(centroid.reshape(1, -1), dish_emb.reshape(1, -1))[0][0]
            if sim > 0.30:
                hit.centroid_similarity = sim
                refined.append(hit)
    
    refined.sort(key=lambda x: x.centroid_similarity, reverse=True)
    return refined

def semantic_retrieve_with_negation(query,restaurant_id=None):
    """
    Retrieve dishes semantically, respecting positive and negative query intents.

    Args:
        query (str): User query text.
        restaurant_id (Optional[str]): Filter by restaurant ID.

    Returns:
        List[DishHit]: Refined and filtered dish hits.
    """
    logging.debug(f"Semantic retrieve called with query: {query} and restaurant_id: {restaurant_id}")
    
    intents = extract_query_intent(query)
    pos_hits, neg_hits = [],[]

    for p in intents.positive:
        pos_hits.extend(search_dishes(p,restaurant_id=restaurant_id))
    for n in intents.negative:
        neg_hits.extend(search_dishes(n,restaurant_id=restaurant_id))

    neg_ids = set([hit.dish["_id"] for hit in neg_hits])
    filtered_dishes = [hit for hit in pos_hits if hit.dish["_id"] not in neg_ids]

    seen = set()
    unique_filtered_dishes = []
    for hit in filtered_dishes:
        if hit.dish["_id"] not in seen:
            unique_filtered_dishes.append(hit)
            seen.add(hit.dish["_id"])

    dish_embeddings = {hit.dish["_id"]:hit.embedding for hit in unique_filtered_dishes}

    refined = refine_with_centroid(unique_filtered_dishes,intents.positive,dish_embeddings)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "restaurant_id": restaurant_id,
        "intents": intents.dict(),
        "positive_dish_count": len(pos_hits),
        "negative_dish_count": len(neg_hits),
        "filtered_dish_count": len(unique_filtered_dishes),
        "positive_dishes": [hit.dish.get("name", "") for hit in pos_hits],
        "negative_dishes": [hit.dish.get("name", "") for hit in neg_hits],
        "unique_filtered_dishes": [hit.dish.get("name", "") for hit in unique_filtered_dishes],
        "refined_dishes": [hit.dish.get("name", "") for hit in refined]
    }

    try:
        # Append to existing file if exists
        with open("intent_dishes_log.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2))
            f.write(",\n")
    except Exception as e:
        logging.error(f"Logging failed: {e}")

    return refined



# if __name__ == "__main__":
#     create_faiss_index()