"""
User Preferences Service Module

This module handles queries about user's own preferences, allergens, and account information.
It retrieves user-specific data from the conversation context rather than searching the menu.
"""
import logging
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import os, json
from dotenv import load_dotenv
from ..models.user_preferences_model import UserPreferencesResult, UserPreferencesResponse
from ..utils.llm_tracker import LLMUsageTracker

logger = logging.getLogger(__name__)

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"),callbacks=[LLMUsageTracker()])

def get_user_preferences(state):
    """
    Handle user preference queries like "what am I allergic to?" or "what are my preferences?"

    This function extracts user-specific information from the conversation context
    rather than searching the restaurant menu. It uses an LLM to interpret the query
    and format a response based on the user's stored preferences (allergens, etc.).

    Args:
        state: A ChatState object containing:
            - query_parts (dict): Parsed user intents with "user_preferences" queries
            - context (list): Conversation context including user allergen preferences
            - current_context (str): Summarized context

    Returns:
        dict: A mapping with key "preference_results" containing UserPreferencesResult,
        which includes structured responses for each user preference query.

    Example:
        Query: "What am I allergic to?"
        Context: [{"user_allergens": ["peanuts", "dairy"], "message": "User is allergic to: peanuts, dairy"}]
        Response: {
            "preference_results": {
                "What am I allergic to?": {
                    "answer": "You are allergic to peanuts and dairy."
                }
            }
        }
    """
    results = {}

    user_pref_queries = state.query_parts.get("user_preferences", [])

    if not user_pref_queries:
        logger.debug("No user_preferences query parts found in state.")
        return {"preference_results": UserPreferencesResult(preference_results=results)}

    logger.info(f"Processing {len(user_pref_queries)} user preference queries")

    for query in user_pref_queries:
        logger.debug(f"Handling user preference query: {query}")

        # Extract user allergen info from context
        user_allergens = []
        if state.context:
            for ctx_item in state.context:
                if "user_allergens" in ctx_item:
                    user_allergens = ctx_item.get("user_allergens", [])
                    break

        logger.debug(f"Found user allergens in context: {user_allergens}")

        # Use LLM to format a natural response
        prompt = ChatPromptTemplate.from_template("""
            You are a helpful assistant answering questions about the user's preferences and account information.

            User Query: {query}

            User Information:
            - Allergen Preferences: {allergens}

            Provide a helpful, conversational answer to the user's query.
            If they ask about allergens and the list is empty, tell them they haven't set any allergen preferences yet.

            CRITICAL: Your response must ONLY be valid JSON. Do not include any explanation, markdown formatting, or additional text.

            Output format (JSON only):
            {{"answer": "your conversational answer to the query"}}

            Remember: Output ONLY the JSON object, nothing else.
        """)

        try:
            response = llm.invoke(prompt.format_messages(
                query=query,
                allergens=", ".join(user_allergens) if user_allergens else "None set"
            ))

            logger.debug(f"LLM Response for user preferences: {response.content}")

            # Check if response is empty
            if not response.content or not response.content.strip():
                logger.warning(f"Empty LLM response for user preferences query: {query}")
                results[query] = UserPreferencesResponse(
                    answer="I couldn't retrieve your preference information. Please try again."
                )
                continue

            # Try to extract JSON from markdown code blocks if present
            content = response.content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            response_json = json.loads(content)
            results[query] = UserPreferencesResponse(**response_json)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in get_user_preferences. Response: {response.content[:500]}. Error: {str(e)}")
            results[query] = UserPreferencesResponse(
                answer=f"I understand you're asking about your preferences, but I encountered an error. Please try again."
            )
        except Exception as e:
            logger.error(f"Error handling user preferences query: {str(e)}")
            results[query] = UserPreferencesResponse(
                answer=f"I encountered an error retrieving your preferences: {str(e)}"
            )

    logger.debug(f"User preferences results: {results}")
    return {"preference_results": UserPreferencesResult(preference_results=results)}
