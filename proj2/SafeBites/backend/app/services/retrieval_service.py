"""
Menu Retrieval Service

This module handles retrieving and filtering menu items for restaurants
based on user queries, semantic search, and applied filters.
"""
import logging
from ..models.dish_info_model import DishData
from .faiss_service import semantic_retrieve_with_negation
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
                serving_size=hit.dish.get("serving_size"),
                availability=hit.dish.get("availability", True),
                allergens=[a["allergen"] for a in hit.dish.get("explicit_allergens", [])],
                nutrition_facts=hit.dish.get("nutrition_facts", {})
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