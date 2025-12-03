"""
Defines Pydantic models for handling dish and menu-related information
in the SafeBites backend.

Models:

- AllergenInfo: Details about potential allergens in a dish.
- NutritionFacts: Nutritional information for a dish.
- DishResult: Represents a dish retrieved from the database or service.
- InfoResult: Contains requested information about a specific dish.
- QueryResponse: Wraps a single query and its corresponding result(s).
- FinalResponse: Aggregates all query responses for a user session.

These models standardize the data passed between services and responses
returned to clients in the chat and menu system.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

class AllergenInfo(BaseModel):
    """
    Represents detailed information about an allergen detected or specified in a dish.

    Attributes:
        allergen (str): The name of the allergen (e.g., "peanuts", "gluten").
        confidence (float): Confidence score (0–1) indicating the certainty of allergen presence.
        why (Optional[str]): Explanation or reasoning behind allergen detection (e.g., "ingredient inference").
    """
    allergen:str
    confidence:float
    why:Optional[str]

class NutritionFacts(BaseModel):
    """
    Represents nutritional details of a dish, including macronutrient and caloric breakdown.

    Attributes:
        calories (Optional[Dict[str, Any]]): Information about calorie content.
        protein (Optional[Dict[str, Any]]): Protein content details.
        fat (Optional[Dict[str, Any]]): Fat content details.
        carbohydrates (Optional[Dict[str, Any]]): Carbohydrate content details.
        sugar (Optional[Dict[str, Any]]): Sugar content details.
        fiber (Optional[Dict[str, Any]]): Fiber content details.
    """
    calories: Optional[Dict[str,Any]] = None
    protein : Optional[Dict[str,Any]] = None
    fat : Optional[Dict[str,Any]] = None
    carbohydrates : Optional[Dict[str,Any]] = None
    sugar : Optional[Dict[str,Any]] = None
    fiber : Optional[Dict[str,Any]] = None

class DishResult(BaseModel):
    """
    Represents a dish item retrieved from the database or a retrieval service.

    Attributes:
        _id (str): Unique identifier for the dish.
        restaurant_id (str): ID of the restaurant offering the dish.
        name (str): Name of the dish.
        description (str): Description of the dish.
        price (Optional[float]): Price of the dish.
        ingredients (Optional[List[str]]): List of ingredients used.
        inferred_allergens (Optional[List[AllergenInfo]]): List of inferred allergens and their confidence scores.
        nutrition_facts (Optional[NutritionFacts]): Nutritional information of the dish.
        availability (Optional[bool]): Availability status of the dish.
        serving_size (Optional[str]): The serving size or portion information.
        explicit_allergens (Optional[List[str]]): Explicitly mentioned allergens, if any.
    """
    _id:str
    restaurant_id:str
    name:str
    description:str
    price:Optional[float]
    ingredients:Optional[List[str]] = []
    inferred_allergens: Optional[List[AllergenInfo]] = []
    nutrition_facts : Optional[NutritionFacts] = None
    availability : Optional[bool] = None
    serving_size : Optional[str] = None
    explicit_allergens : Optional[List[str]] = None

class InfoResult(BaseModel):
    """
    Represents a response containing requested information about a specific dish.

    Attributes:
        dish_name (Optional[str]): Name of the dish queried.
        requested_info (Optional[Union[str, Dict[str, Any]]]): Specific information requested (e.g., ingredients, price).
        source_data (Optional[List[Any]]): Source data or raw results used to derive the response.
    """
    dish_name:Optional[str] = None
    requested_info:Optional[Union[str, Dict[str, Any]]] = None
    source_data : Optional[List[Any]] = []

class PreferenceResult(BaseModel):
    """
    Represents a response to user preference queries like "what am I allergic to?"

    Attributes:
        answer (str): The natural language answer to the user's preference query.
    """
    answer: str

class QueryResponse(BaseModel):
    """
    Represents a single query-response pair for a user's input.

    Attributes:
        query (str): The user's query text.
        type (str): The query type (e.g., 'menu_search', 'dish_info', 'user_preferences', 'irrelevant').
        result (Union[List[DishResult], InfoResult, PreferenceResult, Dict[str, str]]): The resulting data or information retrieved.
    """
    query : str
    type : str
    result : Union[List[DishResult],InfoResult, PreferenceResult, Dict[str,str]]


class FinalResponse(BaseModel):
    """
    Represents the complete structured response for a user session,
    combining all processed queries and their results.

    Attributes:
        user_id (str): Unique identifier for the user.
        session_id (str): Unique session identifier.
        restaurant_id (str): ID of the restaurant context for the conversation.
        original_query (str): The original user input.
        responses (List[QueryResponse]): A list of structured query responses.
        status (str): Processing status (e.g., 'pending', 'completed', 'failed').
        timestamp (str): ISO-formatted timestamp indicating when the response was generated.
    """
    user_id:str
    session_id:str
    restaurant_id:str
    original_query:str
    responses : List[QueryResponse]
    status : str
    timestamp : str = Field(default_factory=lambda: datetime.utcnow().isoformat())

