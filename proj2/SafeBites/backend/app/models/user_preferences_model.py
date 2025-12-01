"""
Pydantic models for user preferences queries.

This module defines the data structures for handling user preference queries
like "what am I allergic to?" or "what are my preferences?".
"""
from pydantic import BaseModel
from typing import Dict

class UserPreferencesResponse(BaseModel):
    """
    Represents the response to a single user preference query.

    Attributes:
        answer (str): The natural language answer to the user's query about their preferences.
    """
    answer: str

class UserPreferencesResult(BaseModel):
    """
    Container for all user preference query results.

    Attributes:
        preference_results (Dict[str, UserPreferencesResponse]):
            A mapping of user queries to their corresponding answers.
            Key: The original user query (e.g., "What am I allergic to?")
            Value: UserPreferencesResponse containing the answer
    """
    preference_results: Dict[str, UserPreferencesResponse]
