"""
Defines the conversational flow graph for the SafeBites chat assistant using LangGraph.

This module constructs a directed graph of nodes that represent each step
in processing a user's chat query. It integrates context resolution,
intent extraction, query part generation, data retrieval (menu and dish info),
and response synthesis into a cohesive pipeline.

Key Functions:
- generate_query_parts(state): Organizes extracted intents into structured query parts.
- create_chat_graph(): Builds and compiles the full LangGraph conversational flow.

The graph operates on ChatState objects, allowing stateful management of
user context, intents, queries, and responses throughout the conversation.
"""
import logging
from langgraph.graph import StateGraph
from .state import ChatState
from langgraph.constants import END
from ..services.intent_service import extract_query_intent
from ..services.retrieval_service import get_menu_items
from ..services.dish_info_service import get_dish_info
from ..services.user_preferences_service import get_user_preferences
from ..services.response_synthesizer_tool import format_final_response
from ..services.context_resolver import resolve_context

logger = logging.getLogger(__name__)

def generate_query_parts(state):
    """
    Generate structured query parts from identified user intents.

    This function processes the intents extracted from the user's input
    and organizes them into categorized query parts (e.g., dish info,
    restaurant menu). These query parts are later used by the retrieval
    services to fetch the relevant data.

    Args:
        state (ChatState): The current state of the chat, which includes
            user intents and contextual information.

    Returns:
        ChatState: The updated state with `query_parts` populated, mapping
        intent types to their corresponding query strings.

    Example:
        If the extracted intents are:
            [
                {"type": "menu", "query": "show me Italian restaurants"},
                {"type": "dish_info", "query": "what is pasta carbonara"}
            ]
        Then the resulting `query_parts` in state will be:
            {
                "menu": ["show me Italian restaurants"],
                "dish_info": ["what is pasta carbonara"]
            }
    """
    for item in state.intents.intents:
        state.query_parts.setdefault(item.type, []).append(item.query)

    logger.debug(f"Generated query_parts: {state.query_parts}")
    return state

def create_chat_graph():
    """
    Construct and compile the LangGraph-based conversational flow for the chat system.

    This function defines a directed graph of conversation processing nodes
    that represent each stage of the dialogue handling pipeline — from
    context resolution to final response synthesis.

    The pipeline flow:
        1. **context_resolver** – Resolves conversation context and user state.
        2. **intent_classifier** – Extracts user intents from their input.
        3. **query_part_generator** – Organizes intents into structured queries.
        4. **menu_retriever** – Retrieves menu or restaurant data based on queries.
        5. **informative_retriever** – Fetches detailed dish information.
        6. **user_preferences_retriever** – Handles user preference queries.
        7. **format_final_response** – Synthesizes a natural language response.

    The graph uses `ChatState` to store and update intermediate information
    throughout the conversation.

    Returns:
        langgraph.graph.CompiledGraph: A compiled conversation graph that
        orchestrates all service nodes and their transitions.

    Example:
        >>> graph = create_chat_graph()
        >>> response = graph.invoke(ChatState(user_message="Tell me about pizza"))
        >>> print(response.output)
        "Pizza is a popular Italian dish available at..."
    """
    graph = StateGraph(ChatState)

    graph.add_node("intent_classifier",extract_query_intent)
    graph.add_node("context_resolver",resolve_context)
    graph.add_node("query_part_generator",generate_query_parts)
    graph.add_node("menu_retriever",get_menu_items)
    graph.add_node("informative_retriever",get_dish_info)
    graph.add_node("user_preferences_retriever",get_user_preferences)
    graph.add_node("format_final_response",format_final_response)
    graph.set_entry_point("context_resolver")
    graph.add_edge("context_resolver","intent_classifier")
    graph.add_edge("intent_classifier","query_part_generator")
    graph.add_edge("query_part_generator","menu_retriever")
    graph.add_edge("query_part_generator","informative_retriever")
    graph.add_edge("query_part_generator","user_preferences_retriever")
    graph.add_edge("menu_retriever","format_final_response")
    graph.add_edge("informative_retriever","format_final_response")
    graph.add_edge("user_preferences_retriever","format_final_response")
    graph.set_finish_point("format_final_response")
    return graph.compile()