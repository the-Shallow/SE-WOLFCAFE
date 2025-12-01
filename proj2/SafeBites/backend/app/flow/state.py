"""
Defines the ChatState Pydantic model used to maintain the full conversational
state for a single user session in SafeBites.

This module provides a structured representation of all data flowing through
the chat pipeline, including user metadata, extracted intents, contextual
information, intermediate query parts, menu and dish results, and the final
system response. Instances of `ChatState` are passed between the various
nodes in the LangGraph-based conversation graph to preserve state and
ensure continuity across multiple turns in the dialogue.

Key Components:
- ChatState: The main Pydantic model capturing all relevant information for
  processing a user's chat query, including context, retrieval results, and
  final response.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from ..models.dish_info_model import DishInfoResult, DishInfoResponse, DishData
from ..models.intent_model import IntentExtractionResult
from ..models.restaurant_model import MenuResultResponse
from ..models.user_preferences_model import UserPreferencesResult

class ChatState(BaseModel):
    """
    Represents the conversational state for a single chat interaction.

    This model encapsulates all contextual, intent-related, and response data
    required to process a user query through the conversation pipeline.
    It acts as a shared data structure passed between different nodes in the
    LangGraph conversation graph.

    Each field represents a step or piece of information derived or produced
    during the chat processing lifecycle — including user metadata, extracted
    intents, retrieved menu and dish information, and the final system response.

    Attributes:
        user_id (str): Unique identifier of the user initiating the chat.
        session_id (str): Identifier for the chat session, used to track
            conversation continuity across multiple turns.
        restaurant_id (str): The ID of the restaurant currently being queried
            or discussed in the conversation.
        query (str): The raw input text provided by the user.

        intents (Optional[IntentExtractionResult]): 
            Output of the intent classification stage, containing a structured
            list of extracted intents and their associated queries.

        context (Optional[List[Dict[str, Any]]]): 
            Contextual metadata or entities from previous interactions that
            can help resolve ambiguous queries or maintain dialogue continuity.

        current_context (Optional[str]): 
            A textual summary of the active context used during intent or
            retrieval processing.

        query_parts (Optional[Dict[str, Any]]): 
            A structured mapping of intent types (e.g., "menu", "dish_info") 
            to their corresponding query fragments, used by retrieval modules.

        menu_results (Optional[MenuResultResponse]): 
            Data structure holding results retrieved from the menu retrieval
            service (restaurant or dish listings).

        info_results (Optional[DishInfoResult]):
            Contains detailed dish-level information returned by the dish
            information service.

        preference_results (Optional[UserPreferencesResult]):
            Contains responses to user preference queries like "what am I allergic to?"

        data (Dict[str, Any]): 
            A general-purpose container for intermediate computation results,
            cache data, or node-specific metadata during chat flow execution.

        response (str): 
            The final formatted response generated for the user.

        status (str): 
            Indicates the current state of the chat processing pipeline.
            Possible values include `"pending"`, `"processing"`, or `"completed"`.

        timestamp (str): 
            ISO 8601 UTC timestamp marking when the state was created.
            Useful for session tracking and debugging.

    """
    user_id:str
    session_id:str
    restaurant_id:str
    query:str
    # intents:Optional[List[Dict[str,Any]]] = None
    intents:Optional[IntentExtractionResult] = None
    context:Optional[List[Dict[str,Any]]] = None
    current_context:Optional[str] = ""
    query_parts: Optional[Dict[str,Any]] = None
    # menu_results: Optional[Dict[str,List[Dict[str, Any]]]] = None
    menu_results: Optional[MenuResultResponse] = None
    # info_results: Optional[Dict[str,Dict[str, Any]]] = None
    info_results: Optional[DishInfoResult] = None
    preference_results: Optional[UserPreferencesResult] = None
    data : Dict[str,Any] = {}
    response : str = ""
    status : str = "pending"
    timestamp : str = datetime.now(timezone.utc).isoformat()