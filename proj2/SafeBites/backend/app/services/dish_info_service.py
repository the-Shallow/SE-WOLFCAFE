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
    - "general_knowledge" (when query is conceptual or unrelated to a restaurant's menu,
      OR when the context already contains sufficient information to answer)

    Args:
        query (str): The user's natural language question (may include context).

    Returns:
        dict: JSON-like dictionary containing:
            - type (str): Either "requires_menu_data" or "general_knowledge".
            - message (Optional[str]): Error message if parsing fails.
    """
    logging.debug(f"Deriving intent for query: {query}")

    prompt = ChatPromptTemplate.from_template("""
        You are an intent analyzer for a food assistant.

        Given a query (which may include additional context), decide whether you need to fetch restaurant menu data or if you can answer from the provided context.

        Possible outputs:
        - "requires_menu_data" → if the question is about dishes, ingredients, allergens, or calories AND the context does not contain the answer.
        - "general_knowledge" → if (1) the question is conceptual/general, OR (2) the "Additional context" section already contains sufficient information to answer the query.

        **CRITICAL**: If the query includes an "Additional context:" section that contains the answer to the user's question, return "general_knowledge".

        Query: {query}

        CRITICAL: Your response must ONLY be valid JSON. Do not include any explanation, markdown formatting, or additional text.

        Output format (JSON only):
        {{"type": "requires_menu_data"}} OR {{"type": "general_knowledge"}}

        Remember: Output ONLY the JSON object, nothing else.
    """)
    response = llm.invoke(prompt.format_messages(query=query))
    logging.debug(f"LLM Intent Response: {response.content}")
    try:
        # Check if response is empty
        if not response.content or not response.content.strip():
            logger.warning(f"Empty LLM response for derive_dish_info_intent query: {query}. Defaulting to general_knowledge.")
            return IntentResponse(type="general_knowledge")

        content = response.content.strip()

        # Try to extract JSON from markdown code blocks if present
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        intent_json = json.loads(content)
        return IntentResponse(**intent_json)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in derive_dish_info_intent. Response: {response.content[:500]}. Error: {str(e)}")
        logger.warning("Falling back to general_knowledge due to JSON parse error")
        return IntentResponse(type="general_knowledge")
    except Exception as e:
        logging.error(f"Error in derive_dish_info_intent: {str(e)}")
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

        CRITICAL: Your response must ONLY be valid JSON. Do not include any explanation, markdown formatting, or additional text.

        Output format (JSON only):
        {{"answer": "your answer to the query"}}

        Remember: Output ONLY the JSON object, nothing else.
    """)
    response = llm.invoke(prompt.format_messages(query=query))
    logging.debug(f"LLM Response: {response.content}")
    try:
        # Check if response is empty
        if not response.content or not response.content.strip():
            logger.warning(f"Empty LLM response for general knowledge query: {query}. Returning error message.")
            return GeneralKnowledgeResponse(answer="I apologize, but I couldn't generate a response. Please try again.")

        content = response.content.strip()

        # Try to extract JSON from markdown code blocks if present
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        answer_json = json.loads(content)
        return GeneralKnowledgeResponse(**answer_json)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in handle_general_knowledge. Response: {response.content[:500]}. Error: {str(e)}")
        return GeneralKnowledgeResponse(answer=f"I understand you're asking: {query}. However, I encountered an error processing the response. Please try rephrasing your question.")
    except Exception as e:
        logger.error(f"Error in handle_general_knowledge: {str(e)}")
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
            serving_size=dish.get("serving_size"),
            availability=dish.get("availability", True),
            allergens=[a["allergen"] for a in dish.get("explicit_allergens", [])],
            nutrition_facts=dish.get("nutrition_facts", {})
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
            f"Serving Size: {d.serving_size or 'N/A'}\n"
            f"Availability: {d.availability}\n"
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
            # Check if response is empty
            if not response.content or not response.content.strip():
                logger.warning(f"Empty LLM response for dish info query: {query}")
                results[query] = DishInfoResponse(
                    dish_name=None,
                    requested_info="No response generated",
                    source_data=[]
                )
                continue

            # Try to extract JSON from markdown code blocks if present
            content = response.content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            response_json = json.loads(content)
            results[query] = DishInfoResponse(**response_json)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in get_dish_info. Response: {response.content[:500]}. Error: {str(e)}")
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info="Could not parse LLM Response",
                source_data=[]
            )
        except Exception as e:
            logger.error(f"Error parsing dish info response: {str(e)}")
            results[query] = DishInfoResponse(
                dish_name=None,
                requested_info="Could not parse LLM Response",
                source_data=[]
            )

    # return {"info_results":results}
    logger.debug(f"Printing Info Results: {results}")
    return {"info_results":DishInfoResult(info_results=results)}
