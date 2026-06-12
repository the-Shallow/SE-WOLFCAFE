"""
Menu Retrieval Service

This module handles retrieving and filtering menu items for restaurants
based on user queries, semantic search, and applied filters.
"""
import logging
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from ..models.dish_info_model import DishData
from .faiss_service import semantic_retrieve_with_negation, semantic_retrieve_candidates
from .restaurant_service import apply_filters, validate_retrieved_dishes
from ..models.exception_model import GenericException
from ..models.restaurant_model import MenuResultResponse



logger = logging.getLogger(__name__)

def get_menu_items(state):
    """
    Retrieve and filter menu items for the given restaurant based on user query parts.

    Args:
        state (ChatState): Current conversation or session state containing restaurant_id and query_parts.

    Returns:
        Dict[str, Any]: Dictionary with structure { "menu_results": {query: [filtered_dishes, ...] } }
    """
    results = {}
    restaurant_id = getattr(state,"restaurant_id",None)
    query_parts = getattr(state,"query_parts",{}).get("menu_search",[])

    if not query_parts:
        logger.warning("No menu_search query parts found in state.")
        return MenuResultResponse(menu_results=results)

    logger.info(f"Processing {len(query_parts)} menu search queries for restaurant {restaurant_id}")
    for q in query_parts:
        logging.debug(f"Retrieving menu items for query: {q} and restaurant_id: {restaurant_id}")
        try:
            if state.current_context:
                logging.debug(f"Appending current context to query: {state.current_context}")
                q = f"{q}\n\nAdditional context:\n{state.current_context}"
            hits = semantic_retrieve_with_negation(q, restaurant_id)
            logging.debug(f"Retrieved data from semantic search: {hits}")
            dish_results = [DishData(
                dish_id=hit.dish["_id"],
                dish_name=hit.dish["name"],
                description=hit.dish["description"],
                price=hit.dish["price"],
                ingredients=hit.dish["ingredients"],
                serving_size=hit.dish["serving_size"],
                availability=hit.dish["availaibility"],
                allergens=[a["allergen"] for a in hit.dish["inferred_allergens"]],
                nutrition_facts=hit.dish["nutrition_facts"]
            ) for hit in hits]

            if not dish_results:
                logger.warning(f"No dishes found for query= {q}")
                results[q] = []
                continue
            
            dish_results = apply_filters(q,dish_results)
            dish_results = validate_retrieved_dishes(q,dish_results)
            results[q] = dish_results
        except Exception as e:
            logger.error(f"Error processing query '{q}': {e}", exc_info=True)
            results[q] = []
            # raise GenericException(str(e))
        
    # return {"menu_results":results}
    return MenuResultResponse(menu_results=results)



@tool
def retrieve_menu_candidates(query:str, restaurant_id: str | None = None, limit:int = 10):
    """
    Retrieve candidate dishes from a restaurant menu using semantic search.
    Use this for broad menu queries like:
    - show me gluten-free dishes
    - list vegetarian options
    - find chicken dishes
    - show desserts
    - high protein meals

    This tool only retrieves possible candidates.
    It does not apply strict allergy, ingredient, price, or nutrition filters.
    """
    hits = semantic_retrieve_candidates(query, restaurant_id=restaurant_id)

    hits = hits[:limit]

    results = []
    for hit in hits:
        dish = hit.dish
        results.append({
            "dish_id": str(dish.get("_id")),
            "restaurant_id": dish.get("restaurant_id"),
            "name": dish.get("name"),
            "description": dish.get("description"),
            "price": dish.get("price"),
            "ingredients": dish.get("ingredients", []),
            "explicit_allergens": dish.get("explicit_allergens", []),
            "inferred_allergens": dish.get("inferred_allergens", []),
            "nutrition_facts": dish.get("nutrition_facts", {}),
            "availability": dish.get("availability", True),
            "retrieval_score": hit.score,
            "centroid_similarity": hit.centroid_similarity,
        })

    return {
        "found": bool(results),
        "query": query,
        "restaurant_id": restaurant_id,
        "count": len(results),
        "candidates": results,
    }