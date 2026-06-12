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
from langchain_core.messages import ToolMessage
from ..services.intent_service import extract_query_intent
from ..services.retrieval_service import get_menu_items, retrieve_menu_candidates
from ..services.dish_info_service import get_dish_info
from ..services.dish_service import get_dish_details
from ..services.response_synthesizer_tool import format_final_response, validator_node, repair_node, final_response_node
from ..services.context_resolver import resolve_context
from ..services.primary_agent import primary_agent
from ..services.restaurant_service import apply_menu_filters, handle_irrelvant_query

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
    
    return state


def tool_node(state:ChatState):
    # print(f"Tool Node : {state}")
    state.data["tool_call_count"] = state.data.get("tool_call_count", 0)
    last_ai_message = state.data.get("last_ai_message")
    tool_messages = []

    for tool_call in last_ai_message.tool_calls:
        state.data["tool_call_count"] += 1

        if state.data["tool_call_count"] > 10:
            result = {
                "error": "tool_call_limit_exceeded",
                "message": "Tool call limit exceeded for this query. Stop calling tools and answer using the information already available."
            }

            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )
            continue
        if tool_call["name"] == "get_dish_details":
            result = get_dish_details.invoke(tool_call["args"])
        elif tool_call["name"] == "retrieve_menu_candidates":
            # print(f"State: {state}")
            if state.data.get("retrieval_already_done"):
                result = {
                    "error": "retrieval_already_done",
                    "message": (
                        "Menu candidates have already been retrieved for this user query. "
                        "Do not call retrieve_menu_candidates again. Use apply_menu_filters "
                        "with existing candidates or answer from existing candidates."
                    ),
                    "existing_candidates": state.data.get("retrieved_candidates", [])
                }
            else:
                result = retrieve_menu_candidates.invoke(tool_call["args"])
                print(f"Results: {result}")
                state.data["retrieval_already_done"] = True
                state.data["retrieved_candidates"] = result.get("candidates", [])
        elif tool_call["name"] == "apply_menu_filters":
            result = apply_menu_filters.invoke(tool_call["args"])
        elif tool_call["name"] == "handle_irrelvant_query":
            result = handle_irrelvant_query.invoke(tool_call["args"])

        tool_messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
            )
        )
        
    state.data["tool_messages"] = tool_messages
    # state.data["last_ai_message"] = None
    return state
    

def after_validation(state: ChatState):
    validation = state.data.get("validation", {})
    if validation.get("is_valid"):
        return "end"
    
    if state.data.get("repair_attempted"):
        return "end"
    
    return "repair_agent"

def should_continue(state:ChatState):
    state.data["agent_step_count"] = state.data.get("agent_step_count", 0) + 1

    if state.data["agent_step_count"] > 6:
        state.status = "success"
        state.response = (
            state.data.get("response") or state.data.get("response_markdown")
        )
        return "end"

    # last_ai_message = state.data.get("last_ai_message")
    # print(f"Should continue : {last_ai_message}")
    if state.status == "tool_required":
        return "tools"
    
    return "end"

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
        6. **format_final_response** – Synthesizes a natural language response.

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

    # graph.add_node("intent_classifier",extract_query_intent)
    # graph.add_node("context_resolver",resolve_context)
    # graph.add_node("query_part_generator",generate_query_parts)
    # graph.add_node("menu_retriever",get_menu_items)
    # graph.add_node("informative_retriever",get_dish_info)
    # graph.add_node("format_final_response",format_final_response)
    # graph.set_entry_point("context_resolver")
    # graph.add_edge("context_resolver","intent_classifier")
    # graph.add_edge("intent_classifier","query_part_generator")
    # graph.add_edge("query_part_generator","menu_retriever")
    # graph.add_edge("query_part_generator","informative_retriever")
    # graph.add_edge("menu_retriever","format_final_response")
    # graph.add_edge("informative_retriever","format_final_response")
    # graph.set_finish_point("format_final_response")

    graph.add_node("main_agent", primary_agent)
    graph.add_node("tools", tool_node)
    graph.add_node("validator", validator_node)
    graph.add_node("repair_agent", repair_node)
    graph.add_node("final_response", final_response_node)

    graph.set_entry_point("main_agent")
    graph.add_conditional_edges(
        "main_agent",
        should_continue,
        {
            "tools": "tools",
            "end": "validator",
        }
    )

    graph.add_edge("tools", "main_agent")

    graph.add_conditional_edges(
        "validator",
        after_validation,
        {
            "repair_agent": "repair_agent",
            "end" : "final_response"
        }
    )

    graph.add_edge("repair_agent", "validator")
    graph.add_edge("final_response", END)
    return graph.compile()