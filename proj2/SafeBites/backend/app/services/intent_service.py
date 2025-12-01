"""
Intent Extraction Module

This module uses a language model (LLM) to parse complex user queries
into structured intents relevant to a food or restaurant assistant.
"""
import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os, json
from typing import List
from dotenv import load_dotenv
from ..models.intent_model import IntentQuery, IntentExtractionResult
from ..utils.llm_tracker import LLMUsageTracker

logger = logging.getLogger(__name__)

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"),callbacks=[LLMUsageTracker()])

def extract_query_intent(state):
    """
    Extracts structured intents from a user query using an LLM.
    
    The function classifies parts of the query into:
      - `menu_search`: requests for dishes or food items.
      - `dish_info`: queries about dish details such as calories or ingredients.
      - `irrelevant`: anything not related to restaurant or food services.
    
    Args:
        state: A ChatState object containing at least a `query` field.
    
    Returns:
        IntentExtractionResult: structured result with intent type and sub-queries.
    
    Raises:
        ValueError: if query is missing or response is invalid.
    """
    query = getattr(state,"query", None)

    if not query:
        raise Exception("Missing query in state during extraction.")
  
    logging.debug(f"Extracting intents for query: {query}")
    prompt = ChatPromptTemplate.from_template("""
                  You are an expert at splitting complex food-related user queries into independent, actionable components.

                  Your task is to take any user query and produce a JSON object containing four keys:

                  1. "menu_search" → a list of self-contained queries that ask for dishes, meals, or items.
                  2. "dish_info" → a list of self-contained queries that ask for information about **specific dishes** (ingredients, calories, allergens, price, etc.)
                  3. "user_preferences" → a list of queries asking about the **user's own** preferences, allergies, or account info (e.g., "what am I allergic to?", "what are my preferences?")
                  4. "irrelevant" → a list of queries or parts that are unrelated to food or restaurant services.

                  ⚡ CRITICAL - User preference queries:
                  - If the query asks "what am I allergic to?", "what are my allergies?", "what are my preferences?", or similar → ALWAYS put it in "user_preferences"
                  - DO NOT put user preference queries in "dish_info" or "menu_search"
                  - User preference queries are about the USER, not about dishes

                  ⚡ Important rules:
                  - Each query part must be **self-contained**: if a query depends on previous results, include that dependency explicitly.  
                  - Preserve **order of dependency**: queries that must be processed sequentially should include phrases like “from the dishes above” or “from the previous results”.  
                  - Split all queries clearly and avoid ambiguity.  
                  - Respond only in valid JSON, nothing else.

                  ---

                  Example 1:

                  User Query: "Provide me a list of five chocolate dishes less than $20. Calculate the total price to buy all of them. Also, are there any dishes less than $5? If yes, how much calories does each one of them contains?"

                  Output:
                  {{
                    "menu_search": [
                      "List five chocolate dishes under $20",
                      "List dishes under $5"
                    ],
                    "dish_info": [
                      "Calculate the total price of the five chocolate dishes under $20",
                      "Provide the calories of the dishes under $5"
                    ],
                    "user_preferences": [],
                    "irrelevant": []
                  }}

                  ---

                  Example 2:

                  User Query: "Do you have vegan pasta options? Also, what are your opening hours? Ignore seafood dishes."

                  Output:
                  {{
                    "menu_search": [
                      "List vegan pasta options excluding seafood dishes"
                    ],
                    "dish_info": [],
                    "user_preferences": [],
                    "irrelevant": [
                      "What are your opening hours?"
                    ]
                  }}

                  ---

                  Example 3:

                  User Query: "I want a chocolate cake. By the way, tell me a joke."

                  Output:
                  {{
                    "menu_search": [
                      "List chocolate cakes"
                    ],
                    "dish_info": [],
                    "user_preferences": [],
                    "irrelevant": [
                      "Tell me a joke"
                    ]
                  }}

                  ---

                  Example 4:

                  User Query: "What am I allergic to? Also, show me safe desserts."

                  Output:
                  {{
                    "menu_search": [
                      "Show me safe desserts"
                    ],
                    "dish_info": [],
                    "user_preferences": [
                      "What am I allergic to?"
                    ],
                    "irrelevant": []
                  }}

                  ---

                  Now analyze this user query and split it into independent parts:

                  {query}
    """)
    try:
        response = llm.invoke(prompt.format_messages(query=query))

        # Log the raw response for debugging
        logger.debug(f"Raw LLM response for intent extraction: {response.content}")

        # Check if response is empty
        if not response.content or not response.content.strip():
            logger.warning(f"Empty LLM response for query: {query}. Treating as irrelevant.")
            return {"intents":IntentExtractionResult(
                intents=[IntentQuery(type="irrelevant",query=query)]
            )}

        # Try to extract JSON from markdown code blocks if present
        content = response.content.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        data = json.loads(content)
        logging.debug(f"Extracted intents: {data}")

        intents: List[IntentQuery] = []
        for intent_type, queries in data.items():
            for q in queries:
                intents.append(IntentQuery(type=intent_type, query=q))

        return {"intents":IntentExtractionResult(intents=intents)}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in extract_query_intent. Response: {response.content[:500]}. Error: {str(e)}")
        logger.warning("Falling back to treating query as irrelevant due to JSON parse error")
        return {"intents":IntentExtractionResult(
            intents=[IntentQuery(type="irrelevant",query=query)]
        )}
    except Exception as e:
        logger.error(f"Error in extract_query_intent: {str(e)}")
        return {"intents":IntentExtractionResult(
            intents=[IntentQuery(type="irrelevant",query=query)]
        )}
