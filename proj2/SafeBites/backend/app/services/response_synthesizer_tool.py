"""
Response Formatter Module

This module aggregates results from different stages of the chat pipeline
(menu search, dish info, and unrecognized queries) into a structured
FinalResponse object for the end user.
"""
import os
import logging
from dotenv import load_dotenv
from typing import List
from ..flow.state import ChatState
from ..models.responder_model import QueryResponse, DishResult, InfoResult, PreferenceResult, FinalResponse

load_dotenv()

logger = logging.getLogger(__name__)

def format_final_response(state:ChatState):
    """
    Aggregate and format the final response from a given chat state.

    This function collects results from different sources in the chat state:
    - Menu search results (`menu_results`)
    - Dish information results (`info_results`)
    - User preference results (`preference_results`)
    - Irrelevant or unrecognized queries (`query_parts["irrelevant"]`)

    It combines all results into a structured `FinalResponse` object.

    Parameters
    ----------
    state : ChatState
        The current state of the chat, containing user info, queries,
        menu results, dish info, and other context.

    Returns
    -------
    FinalResponse
        A Pydantic model representing the aggregated response to the user,
        including:
        - `user_id`, `session_id`, `restaurant_id`, `original_query`
        - `responses`: list of `QueryResponse` objects for each query type
        - `status`: "success" if any response was generated, "failed" otherwise

    Raises
    ------
    Exception
        Re-raises any exception that occurs during formatting, while logging
        detailed error information.
    """
    try:
        logger.debug(f"Formatting final response from the state {state}")
        responses : List[QueryResponse] = []

        if state.menu_results and state.menu_results.menu_results:
            for query, dishes in state.menu_results.menu_results.items():
                responses.append(QueryResponse(
                    query=query,
                    type="menu_search",
                    result=[DishResult(
                        _id=dish.dish_id,
                        restaurant_id=state.restaurant_id,
                        name=dish.dish_name,
                        description=dish.description,
                        price=dish.price,
                        ingredients=dish.ingredients or [],
                        inferred_allergens=[],
                        explicit_allergens=dish.allergens or [],
                        nutrition_facts=dish.nutrition_facts,
                        availability=dish.availability,
                        serving_size=dish.serving_size
                    ) for dish in dishes]
                ))

        if state.info_results and state.info_results.info_results:
            for query, info in state.info_results.info_results.items():
                logger.debug(f"Printing Info results for query {query} : {info}")
                responses.append(QueryResponse(
                    query=query,
                    type="dish_info",
                    result=InfoResult(**info.model_dump())
                ))

        if state.preference_results and state.preference_results.preference_results:
            for query, pref in state.preference_results.preference_results.items():
                logger.debug(f"Printing Preference results for query {query} : {pref}")
                responses.append(QueryResponse(
                    query=query,
                    type="user_preferences",
                    result=PreferenceResult(**pref.model_dump())
                ))

        if state.query_parts and state.query_parts.get("irrelevant"):
            for query in state.query_parts["irrelevant"]:
                responses.append(QueryResponse(
                    query=query,
                    type="irrelevant",
                    result={"message":"Sorry, I couldn't understand your query. Please rephrase it."}
                ))

        logger.debug(f"Final formatted responses: {responses}")
        final = FinalResponse(
            user_id=state.user_id,
            session_id=state.session_id,
            restaurant_id=state.restaurant_id,
            original_query=state.query,
            responses=responses,
            status="success" if responses else "failed"
        )
        logger.debug(f"Final Response Object: {final}")
        return final
    except Exception as e:
        logger.error(f"Error formatting final response: {e}", exc_info=True)
        raise e