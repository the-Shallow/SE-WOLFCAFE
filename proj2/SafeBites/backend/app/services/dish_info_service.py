"""
Dish Information Service Module

This module provides functionality for retrieving, filtering, and summarizing
dish-related information for a food delivery assistant application. It integrates
semantic search, LLM-based intent analysis, and structured output formatting
to answer user queries about dishes, ingredients, allergens, calories, and general
food knowledge.
"""
import logging
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os, json
from dotenv import load_dotenv
from ..models.dish_info_model import DishInfoResponse, DishData, DishInfoResult, GeneralKnowledgeResponse, IntentResponse
from app.services.faiss_service import semantic_retrieve_with_negation
from .restaurant_service import apply_filters, validate_retrieved_dishes
from ..utils.llm_tracker import LLMUsageTracker
from app.models.exception_model import NotFoundException, BadRequestException, DatabaseException,GenericException


logger = logging.getLogger(__name__)

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"),callbacks=[LLMUsageTracker()])

def derive_dish_info_intent(query):
    """
    Determine whether a user query requires restaurant-specific menu data or general food knowledge.

    This function uses an LLM to analyze the query and classify it as either:
    - "requires_menu_data" (when query involves dishes, ingredients, allergens, or calories)
    - "general_knowledge" (when query is conceptual or unrelated to a restaurant’s menu)

    Args:
        query (str): The user's natural language question.

    Returns:
        dict: JSON-like dictionary containing:
            - type (str): Either "requires_menu_data" or "general_knowledge".
            - message (Optional[str]): Error message if parsing fails.
    """
    logging.debug(f"Deriving intent for query: {query}")

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
    response = llm.invoke(prompt.format_messages(query=query))
    logging.debug(f"LLM Intent Response: {response.content}")
    try:
        intent_json = json.loads(response.content)
        return IntentResponse(**intent_json)
    except Exception as e:
        logging.error(str(e))
        raise GenericException(f"Unexpected error: {str(e)}")


def handle_general_knowledge(query):
    """
    Handle general food knowledge queries.

    Args:
        query (str): User query text.

    Returns:
        GeneralKnowledgeResponse: Pydantic model with answer text.
    """
    logging.debug(f"Handling general knowledge query: {query}")
    prompt = ChatPromptTemplate.from_template("""
        You are a food assistant. Answer the following query using general food knowledge only. 
        Do NOT assume restaurant-specific information unless explicitly mentioned.
        Query: {query}
                                                    
        Format the response in JSON:
        - "answer": your answer to the query
    """)
    response = llm.invoke(prompt.format_messages(query=query))
    logging.debug(f"LLM Response: {response.content}")
    try:
        answer_json = json.loads(response.content)
        return GeneralKnowledgeResponse(**answer_json)
    except Exception as e:
        raise GenericException(str(e))

def handle_food_item_query(query, restaurant_id=None):
    """
        Retrieve and structure dish data from the semantic search.

        Args:
            query (str): User query text.
            restaurant_id (Optional[str]): Restaurant identifier.

        Returns:
            List[DishData]: List of structured dish data.

        Raises:
            NotFoundException: If no dishes are found.
    """
    logging.debug(f"Handling food item query: {query} for restaurant_id: {restaurant_id}")
    hits = semantic_retrieve_with_negation(query, restaurant_id=restaurant_id)

    if not hits:
        raise NotFoundException(f"No relevant dishes found for query {query}")

    results = []
    for hit in hits:
        dish = hit.dish
        logger.debug(f"Retrieved dish from hit: {dish}")
        results.append(DishData(
            dish_id= dish["_id"],
            dish_name=dish["name"],
            description=dish["description"],
            price=dish["price"],
            ingredients=dish["ingredients"],
            serving_size=dish["serving_size"],
            availability=dish["availaibility"],
            allergens=[a["allergen"] for a in dish["inferred_allergens"]],
            nutrition_facts=dish["nutrition_facts"]
        ))
    logging.debug(f"Food item query results: {results}")
    return results


def get_dish_info(state):
    """
    Extracts and summarizes detailed dish information for one or more user queries.

    This function orchestrates a multi-step retrieval and reasoning pipeline:
      1. **Intent Derivation:** Determines whether the query is food-related, factual,
         or general knowledge.
      2. **Data Retrieval:** Fetches dishes from the target restaurant based on the query.
      3. **Filtering & Validation:** Applies user- or query-based filters (e.g., allergens, price)
         and ensures retrieved dishes meet relevance criteria.
      4. **LLM Summarization:** Passes dish data and the user query to a language model to
         generate a structured JSON response.

    Args:
        state: An object containing:
            - `restaurant_id` (str): The target restaurant to query.
            - `query_parts` (dict): Parsed user intents grouped by category.
            - `current_context` (str, optional): Prior summarized conversation context.

    Returns:
        dict: A mapping with a single key `"info_results"` containing a `DishInfoResult`
        object, which includes structured results per query:
        {
            "info_results": {
                "What is in the pasta?": DishInfoResponse(
                    dish_name="Penne Alfredo",
                    requested_info="It includes pasta, cream, garlic, and cheese.",
                    source_data=[...]
                )
            }
        }

    Raises:
        Logs errors internally and continues for each query. Does not raise exceptions outward.
    """
    results = {}
    restaurant_id = state.restaurant_id
    for query in state.query_parts.get("dish_info",[]):
        logging.debug(f"Getting dish info for query: {query} and restaurant_id: {restaurant_id}")

        if state.current_context:
            logging.debug(f"Appending current context to query: {state.current_context}")
            query = f"{query}\n\nAdditional context:\n{state.current_context}"
        
        try:
            intent = derive_dish_info_intent(query)
        except GenericException as e:
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info="Intent derivation failed",
                source_data=[]
            )
            continue
        
        logging.debug(f"Query intent: {intent}")
        if intent.type == "general_knowledge":
            response = handle_general_knowledge(query=query)
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info=response.answer,
                source_data=[]
            ) 
            continue
            
        try:
            dishes = handle_food_item_query(query, restaurant_id=restaurant_id)
            dishes = apply_filters(query,dishes)
            dishes = validate_retrieved_dishes(query,dishes)
        except NotFoundException as e:
            logger.error(str(e))
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info=str(e),
                source_data=[]
            )
            continue
        except Exception as e:
            logger.error(str(e))
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info=f"Unexpected error: {str(e)}",
                source_data=[]
            )
            continue
    
        context = ""
        context = "\n".join([
            f"Dish Name : {d.dish_name}\n"
            f"Description : {d.description}\n"
            f"Price : {d.price}\n"
            f"Ingredients : {', '.join(d.ingredients or [])}\n"
            f"Serving Size: {d.serving_size}\n"
            f"Availibility: {d.availibility}\n"
            f"Allergens : {', '.join(d.allergens or [])}\n"
            f"Nutrition : {d.nutrition_facts}\n"
            for d in dishes
        ])
            
        prompt = ChatPromptTemplate.from_template("""
    You are a food information assistant.
        Using ONLY the following dish data, answer the user's query.
        Format the response as JSON:
        - "dish_name" - name of the dish being referred to.
        - "requested_info" - string answer to the user's query.
        - "source_data" - list of relevant dish data used to answer the query.

        User Query: {query}

        Dish Data: {context}
        """)
        response = llm.invoke(prompt.format_messages(query=query,context=context))
        logging.debug(f"LLM Response: {response.content}")
        
        try:
            response_json = json.loads(response.content)
            results[query] = DishInfoResponse(**response_json)
        except Exception as e:
            logger.error(str(e))
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info="Could not parse LLM Response",
                source_data=[]
            )

    # return {"info_results":results}
    logger.debug(f"Printing Info Results: {results}")
    return {"info_results":DishInfoResult(info_results=results)}
