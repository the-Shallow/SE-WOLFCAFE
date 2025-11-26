"""
This module provides functionality to resolve contextual references in user queries
for a food delivery assistant. It uses a large language model (LLM) to:

1. Rewrite queries that contain implicit references (e.g., "that dish", "it") 
   into self-contained queries.
2. Summarize prior conversation context relevant to the current query, 
   producing a concise factual summary.
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os, json
import logging
from dotenv import load_dotenv
from ..utils.llm_tracker import LLMUsageTracker
from .exception_service import BadRequestException, GenericException

logger = logging.getLogger(__name__)

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"),callbacks=[LLMUsageTracker()])

def resolve_context(state):
    """
    Resolves contextual references in the user's query using prior conversation history.

    This function performs two major LLM tasks:
      1. **Query Rewriting:** Identifies implicit references in the user query
         (e.g., “that dish”, “those options”, “it”) and rewrites it into a
         self-contained query.
      2. **Context Summarization:** Summarizes the relevant prior context so
         the next model can respond accurately and efficiently.

    Args:
        state: A `ChatState` object containing the user's query and previous context.

    Returns:
        dict: A dictionary with:
            - `query` (str): The rewritten, self-contained query.
            - `current_context` (str): A concise, factual summary of prior context relevant to the query.

    Example:
        >>> state.query = "What about that pasta?"
        >>> state.context = {"previous_dishes": ["creamy mushroom pasta", "chicken alfredo"]}
        >>> resolve_context(state)
        {
            "query": "Tell me about creamy mushroom pasta",
            "current_context": "User previously viewed creamy mushroom pasta and chicken alfredo dishes."
        }

    Raises:
        Exception: Propagates any LLM invocation or API errors.
    """
    logger.debug(f"Resolving context for state: {state}")
    if not getattr(state, "query", None):
        raise BadRequestException("Missing user query in state.")
    try:
        prompt_template = ChatPromptTemplate.from_template("""
    You are a context resolver for a food delivery assistant.
    Your job is to interpret the current user query in the context of prior conversation.

    User query: {query}

    Previous Context :
    {context}

    **Task**: Rewrite the query to be self-contained by incorporating relevant context.

    **Rules**:
    1. **DO NOT rewrite user preference queries**: If the query asks about the USER'S OWN preferences, allergens, or account info (e.g., "what am I allergic to?", "what are my preferences?"), return it EXACTLY as-is without any changes.
    2. If the user query refers to something previously mentioned (e.g., "that", "those", "it"), resolve what it refers to.
    3. If the user query is a **refinement** (adds a constraint without mentioning a dish type):
       - Example: Previous query: "show me pizzas", Current query: "under $20" → Rewrite to: "show me pizzas under $20"
       - Example: Previous query: "burgers", Current query: "gluten-free" → Rewrite to: "show me gluten-free burgers"
       - Example: Previous query: "Italian dishes", Current query: "less than 500 calories" → Rewrite to: "show me Italian dishes less than 500 calories"
    4. If the user query is a **new request** (mentions a new dish type or topic), use it as-is.
    5. If user allergens are in context, you don't need to add them to the query (they'll be handled separately).

    Return ONLY the rewritten query text, nothing else.
    """)
        
        response = llm.invoke(prompt_template.format_messages(
            query=state.query,
            context=state.context or {}
        ))
        logger.debug("Rewritten Query:", response.content)
        # return {"query": response.content.strip()}

        rewritten_query = response.content.strip()

        if not rewritten_query:
            raise GenericException("LLM returned an empty rewritten query.")

        context_summary_prompt = ChatPromptTemplate.from_template("""
    You are summarizing conversation context for another LLM.
    Given the following context, extract only relevant information that might help answer the query below.

    Context: {context}
    Query: {query}

    Return a short, factual summary (under 300 words) describing relevant dishes, filters, or results.
    """)
        
        summary_response = llm.invoke(context_summary_prompt.format_messages(
            context=state.context or {},
            query=rewritten_query
        ))

        current_context = summary_response.content.strip()

        logger.debug(f"Resolved Context Response: {current_context}")

        return {
            "query": rewritten_query,
            "current_context": current_context
        }
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Data parsing error during context resolution....")
        raise BadRequestException(f"Invalid data format : {e}")
    except Exception as e:
        logger.error("Unexpected error in context resolver....")
        raise GenericException(f"Unexpected error : {e}")