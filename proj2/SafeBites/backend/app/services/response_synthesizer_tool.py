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

from langchain_openai import ChatOpenAI
from ..flow.state import ChatState
from ..models.responder_model import QueryResponse, DishResult, InfoResult, FinalResponse, ValidationResult

load_dotenv()

logger = logging.getLogger(__name__)

def format_final_response(state:ChatState):
    """
    Aggregate and format the final response from a given chat state.

    This function collects results from different sources in the chat state:
    - Menu search results (`menu_results`)
    - Dish information results (`info_results`)
    - Gibberish or unrecognized queries (`query_parts["gibberish"]`)

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
                    result=[DishResult(**dish) for dish in dishes]
                ))

        if state.info_results.info_results:
            for query, info in state.info_results.info_results.items():
                logger.debug(f"Printing Info results for query {query} : {info}")
                responses.append(QueryResponse(
                    query=query,
                    type="dish_info",
                    result=InfoResult(**info.model_dump())
                ))

        if state.query_parts and state.query_parts.get("gibberish"):
            for query in state.query_parts["gibberish"]:
                responses.append(QueryResponse(
                    query=query,
                    type="gibberish",
                    result={"message":"Sorry, I couldn't understand your query.Pleas rephrase it."}
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
    



VALIDATOR_SYSTEM_PROMPT = """
You are a strict response validator for a restaurant menu chatbot.

Your job is to validate the assistant's final response before it is shown to the user.

Check:
1. If the response mentions menu dishes, those dishes must exist in the provided candidates.
2. Extract dish_ids for dishes that should be shown as UI cards.
3. Do not include dish_ids for dishes not present in candidates.
4. If the user asked for filters, verify the response respects them.
7. Detect hallucinated dishes, unsupported claims, or wrong dietary/allergen claims.

Return only structured validation output.

Important:
- dish_ids should only come from retrieved_candidates or filtered_candidates.
- Prefer filtered_candidates over retrieved_candidates when available.
- Do not rewrite the response unless a small correction is obvious.
"""

validator_llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY")).with_structured_output(ValidationResult)

def validator_node(state:ChatState):
    user_query = state.query
    response_markdown = state.data.get("final_response_markdown", "") or state.data.get("response", "")

    retrieved_candidates = state.data.get("retrieved_candidates", [])
    filtered_candidates = state.data.get("filtered_candidates", [])
    applied_filters = state.data.get("applied_filters", [])

    validator_input = f"""

    User Query: {user_query}
    Assistant Response: {response_markdown}

    Retrieved Candidates: {retrieved_candidates}

    Filtered Candidates: {filtered_candidates}
    Applied Filters: {applied_filters}

    """

    validation : ValidationResult = validator_llm.invoke(
        [
            ("system", VALIDATOR_SYSTEM_PROMPT),
            ("user", validator_input) 
        ]
    )

    validation_dict = validation.model_dump()
    state.data["validation"] = validation_dict
    state.data["dish_ids_to_show"] = validation.dish_ids
    
    if validation.corrected_response:
        state.data["response_markdown"] = validation.corrected_response
        state.data["response"] = validation.corrected_response

    return state


REPAIR_SYSTEM_PROMPT = """
You are repairing a restaurant chatbot response.

Rewrite the response using the validator feedback.

Rules:
- Only mention dishes that exist in the provided candidates.
- Respect the user's filters.
- Do not invent ingredients, dietary labels, prices, or allergens.
- Do not answer unrelated/non-menu parts of the user query.
- Do not provide code, general knowledge, jokes, weather, resume help, or other non-menu content.
- For unrelated parts, briefly say that SafeBites can only help with restaurant/menu-related questions.
- Keep the answer concise and user-friendly.
- Use Markdown formatting with headings or bullets when helpful.
"""

repair_llm = ChatOpenAI(model="gpt-5",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"))

def repair_node(state:ChatState):
    validation = state.data.get("validation", {})

    repair_input = f"""
User query:
{state.query}

Original response:
{state.data.get("response_markdown") or state.data.get("response")}

Validator issues:
{validation.get("issues")}

Repair instructions:
{validation.get("repair_instructions")}

Retrieved candidates:
{state.data.get("retrieved_candidates", [])}

Filtered candidates:
{state.data.get("filtered_candidates", [])}
    """

    repaired = repair_llm.invoke(
        [
            ("system", REPAIR_SYSTEM_PROMPT),
            ("user", repair_input)
        ]
    )

    state.data["response_markdown"] = repaired.content
    state.data["response"] = repaired.content
    state.data["repair_attempted"] = True

    return state


def normalize_dish_cards(item:dict):
    explicit = item.get("explicit_allergens" , [])
    inferred = item.get("inferred_allergens", [])

    allergens = []
    
    for a in explicit:
        if isinstance(a, dict):
            allergens.append(a.get("allergen"))
        else:
            allergens.append(a)

    for a in inferred:
        if isinstance(a, dict):
            allergens.append(a.get("allergen"))
        else:
            allergens.append(a)

    return {
        "dish_id": item.get("dish_id"),
        "dish_name": item.get("name"),
        "name": item.get("name"),
        "description": item.get("description"),
        "price": item.get("price"),
        "ingredients": item.get("ingredients", []),
        "allergens": [a for a in allergens if a],
        "nutrition_facts": item.get("nutrition_facts", {}),
        "availability": item.get("availability", True),
    }

def final_response_node(state:ChatState):
    dish_ids = state.data.get("dish_ids_to_show", [])
    retrieved_candidates = state.data.get("retrieved_candidates", [])
    filtered_candidates = state.data.get("filtered_candidates", [])

    candidate_pool = (
        filtered_candidates if filtered_candidates else retrieved_candidates
    )

    candidate_map = {
        item["dish_id"]: item for item in candidate_pool
    }

    cards = [
        candidate_map[dish_id] for dish_id in dish_ids if dish_id in candidate_map
    ]

    final_text = (
        state.data.get("response_markdown")
        or state.data.get("response")
        or state.response
        or ""
    )

    state.data["final_output"] = {
        "response_markdown": final_text,
        "dish_ids": dish_ids,
        "cards": cards,
        "status": "success",
        "response": final_text
    }

    return state
