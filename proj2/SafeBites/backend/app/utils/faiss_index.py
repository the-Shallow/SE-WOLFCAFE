from datetime import datetime
from langchain_openai import OpenAIEmbeddings, ChatOpenAI, OpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
import json
import numpy as np
import os
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# db = get_db()

from pymongo import MongoClient
# from ..config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
dish_collection = db["dishes"]


embeddings = OpenAIEmbeddings(model="text-embedding-3-large",openai_api_key=os.getenv("OPENAI_KEY"))
embedding_dim = 1536


def derive_dish_info_intent(query):
    print(f"Deriving intent for query: {query}")

    prompt = ChatPromptTemplate.from_template("""
                                              
You are an intent analyzer for a food assistant.

Given a query, decide whether the answer requires fetching restaurant menu data.

Possible outputs:
- "requires_menu_data" → if the question is about dishes, ingredients, allergens, calories, or menu items that might exist in the restaurant data.
- "general_knowledge" → if the question is conceptual and doesn’t depend on any restaurant data.

Query: {query}

Format the response in JSON:
- type: "requires_menu_data" or "general_knowledge"

""")
    llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"))
    response = llm.invoke(prompt.format_messages(query=query))
    print(f"LLM Response: {response.content}")
    try:
        refined = json.loads(response.content)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print("Response content:", response.content)
        refined = {"message": "Could not parse response."}
    return refined


def handle_general_knowledge(query):
    print(f"Handling general knowledge query: {query}")

    prompt = ChatPromptTemplate.from_template("""
You are a food assistant. Answer the following query using general food knowledge only. 
Do NOT assume restaurant-specific information unless explicitly mentioned.
Query: {query}
                                              
Format the response in JSON:
- "answer": your answer to the query
                                              """)
    llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"))
    response = llm.invoke(prompt.format_messages(query=query))
    print(f"LLM Response: {response.content}")
    try:
        refined = json.loads(response.content)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print("Response content:", response.content)
        refined = {"message": "Could not parse response."}
    return refined

def handle_food_item_query(query, restaurant_id=None):
    print(f"Handling food item query: {query} for restaurant_id: {restaurant_id}")
    hits = semantic_retrieve_with_negation(query, restaurant_id=restaurant_id)
    if not hits:
        return {"message": "No relevant dishes found."}
    results = []
    for hit in hits:
        dish = hit["dish"]
        results.append({
            "dish_name": dish.get("name", "N/A"),
            "description": dish.get("description", "N/A"),
            "price": dish.get("price", "N/A"),
            "ingredients": dish.get("ingredients", []),
            "availability": dish.get("availability", "N/A"),
            "allergens": [a['allergen'] for a in dish.get("explicit_allergens", [])],
            "nutrition_info": dish.get("nutrition_info", {})
        })
    print(f"Food item query results: {results}")
    return results


def get_dish_info(query, restaurant_id=None):
    print(f"Getting dish info for query: {query} and restaurant_id: {restaurant_id}")

    query = query.strip()
    query_intent = derive_dish_info_intent(query)
    print(f"Query intent: {query_intent}")
    if query_intent.get("type") == "general_knowledge":
        return handle_general_knowledge(query)
    
    dish = handle_food_item_query(query, restaurant_id=restaurant_id)
    
    context = ""
    for result in dish:
        dish = result
        print(dish)
        context += f"""

    Dish Name: {dish.get('dish_name', 'N/A')}
    Description: {dish.get('description', 'N/A')}
    Price: {dish.get('price', 'N/A')}
    Ingredients: {', '.join(dish.get('ingredients', []))}
    Availability: {dish.get('availability', 'N/A')}
    Allergens: {', '.join([a for a in dish.get('allergens', [])])}
    Nutrition: {dish.get('nutrition_info', {})}
        
    """
    print(f"Context for LLM: {context}")
        
    prompt = ChatPromptTemplate.from_template("""
You are a food information assistant.
    Using ONLY the following dish data, answer the user's query.
    Format the response as JSON:
    - "dish_name"
    - "requested_info"
    - "source_data"

    User Query: {query}

    Dish Data: {context}
    """)
    llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"))
    response = llm.invoke(prompt.format_messages(query=query,context=context))
    print(f"LLM Response: {response.content}")
    try:
        refined = json.loads(response.content)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print("Response content:", response.content)
        refined = {"message": "Could not parse response."}
    return refined



def extract_query_intent(query):
    llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"))
    intent_prompt = ChatPromptTemplate.from_template("""
    You are an intent extraction expert for food-related natural language queries.

    Your job is to split the query into two lists:
    1. **Positive intents** — what the user explicitly wants or is open to.
       - Expand this list semantically (include closely related dishes, cuisines, or styles).
    2. **Negative intents** — what the user explicitly wants to exclude or avoid.
       - DO NOT over-expand. Keep this list narrowly focused on the specific items, ingredients, or categories mentioned.
       - Avoid including loosely related or parent-category terms.
       - Only include synonyms or direct variants (e.g., "meatballs" → ["meatball", "meat balls", "polpette"], not "beef" or "meat").

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

    Query: {query}
""")
    response =  llm.invoke(intent_prompt.format_messages(query=query))
    try:
        intents = json.loads(response.content)
    except Exception as e:
        print("Error parsing JSON:", e)
        print("Response content:", response.content)
        intents = {"positive":[query],"negative":[]}
    return intents


def create_faiss_index():
    # try:
        texts = []
        metadatas = []
    #     index = faiss.read_index("dish_index.faiss")
    #     with open("dish_ids.pkl","rb") as f:
    #         dish_ids = pickle.load(f)
    # except FileNotFoundError:
        for i,dish in enumerate(dish_collection.find()):
            text = f"""
    Dish Name : {dish["name"]}
Description : {dish["description"]}
Price : {dish["price"]}
Ingredients : {', '.join(dish.get("ingredients",[]))}
Availability : {dish.get("availability",True)}
Allergens : {', '.join([a["allergen"] for a in dish.get("explicit_allergens",[])])}
Nutrtion : {dish.get("nutrition_info",{})}
"""
            texts.append(text)

            metadata = {
                "dish_id":dish["_id"],
                "restaurant_id":dish["restaurant_id"],
                "vector_id":i
            }

            metadatas.append(metadata)
        # print(texts,metadatas)
        vector_store = FAISS.from_texts(
            texts=texts,
            embedding = embeddings,
            metadatas=metadatas,
        )

        vector_store.save_local("faiss_index_restaurant")
        print("FAISS index created and saved locally.")

def search_dishes(query, restaurant_id=None,top_k=20,threshold=0.8):
    vector_store = FAISS.load_local("faiss_index_restaurant", embeddings,allow_dangerous_deserialization=True)
    filter_dict = {"restaurant_id":restaurant_id} if restaurant_id else None
    results = vector_store.similarity_search_with_score(query, k=top_k, filter=filter_dict)
    structured_res = []
    for res,score in results:
        if score >= threshold:
            dish = dish_collection.find_one({"_id":res.metadata["dish_id"]})
            if dish:
                structured_res.append({
                    "dish":dish,
                    "score":score,
                    "embedding":vector_store.index.reconstruct(res.metadata["vector_id"])
                })
    return structured_res


def refine_with_centroid(dish_hits,positive_intents,dish_embeddings):
    centroid = np.mean([embeddings.embed_query(intent) for intent in positive_intents],axis=0)
    print("Centroid:", centroid)
    refined = []
    for hit in dish_hits:
        dish_emb = dish_embeddings.get(hit["dish"]["_id"])
        print("Dish:", hit["dish"].get("name", str(hit["dish"])))
        print("Dish Embedding:", dish_emb)
        if dish_emb is not None:
            sim = cosine_similarity(centroid.reshape(1, -1), dish_emb.reshape(1, -1))[0][0]
            print("Similarity:", sim)
            if sim > 0.45:
                hit["centroid_similarity"] = sim
                refined.append(hit)
    
    refined.sort(key=lambda x: x["centroid_similarity"], reverse=True)
    return refined

def semantic_retrieve_with_negation(query,restaurant_id=None):
    intents = extract_query_intent(query)
    pos_hits, neg_hits = [],[]

    for p in intents["positive"]:
        pos_hits.extend(search_dishes(p,restaurant_id=restaurant_id))
    for n in intents["negative"]:
        neg_hits.extend(search_dishes(n,restaurant_id=restaurant_id))

    neg_ids = set([hit["dish"]["_id"] for hit in neg_hits])
    filtered_dishes = [hit for hit in pos_hits if hit["dish"]["_id"] not in neg_ids]

    seen = set()
    unique_filtered_dishes = []
    for hit in filtered_dishes:
        if hit["dish"]["_id"] not in seen:
            unique_filtered_dishes.append(hit)
            seen.add(hit["dish"]["_id"])

    dish_embeddings = {hit["dish"]["_id"]:hit["embedding"] for hit in unique_filtered_dishes}

    refined = refine_with_centroid(unique_filtered_dishes,intents["positive"],dish_embeddings)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "restaurant_id": restaurant_id,
        "intents": intents,
        "positive_dish_count": len(pos_hits),
        "negative_dish_count": len(neg_hits),
        "filtered_dish_count": len(unique_filtered_dishes),
        "positive_dishes": [hit["dish"].get("name", str(hit["dish"])) for hit in pos_hits],
        "negative_dishes": [hit["dish"].get("name", str(hit["dish"])) for hit in neg_hits],
        "unique_filtered_dishes": [hit["dish"].get("name", str(hit["dish"])) for hit in unique_filtered_dishes],
        "refined_dishes": [hit["dish"].get("name", str(hit["dish"])) for hit in refined]
    }

    try:
        # Append to existing file if exists
        with open("intent_dishes_log.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2))
            f.write(",\n")
    except Exception as e:
        print(f"Logging failed: {e}")

    return refined

if __name__ == "__main__":
    # create_faiss_index()
    # dishes = search_dishes("Which dishes are not gluten?",restaurant_id="rest_1")
    # for dish in dishes:
        # print(dish)
        # print("-----" * 10)
    # intents = extract_query_intent("Anything but seafood")
    # print(intents)
    # semantic_retrieve_with_negation("Dishes that have chocolate", restaurant_id="rest_1")
    print(get_dish_info("What are the different kind of hotdogs in this world?", restaurant_id="rest_1"))