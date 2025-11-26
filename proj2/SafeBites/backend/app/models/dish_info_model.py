"""
Defines Pydantic models for representing dish-level data and
responses for the SafeBites conversational system.

This module includes structures for:
- DishData: Core details about a specific dish, including ingredients, allergens,
  and nutritional information.
- DishInfoResponse: Encapsulates the response to a user's dish query.
- DishInfoResult: Aggregates multiple DishInfoResponse objects for multi-dish queries.
- IntentResponse: Represents basic intent classification results.
- GeneralKnowledgeResponse: Handles responses for general or non-dish-specific queries.

These models are used throughout the chat pipeline to ensure consistent
data representation between retrieval, processing, and response synthesis
stages.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DishData(BaseModel):
    """
    Represents structured information about a specific dish.

    This model captures all essential attributes of a dish, including
    its name, description, pricing, ingredients, allergens, and nutritional
    details. It is typically used to store or return dish-level data retrieved
    from restaurant menus or external data sources.

    Attributes:
        dish_id (str): Unique identifier for the dish.
        dish_name (str): Human-readable name of the dish.
        description (Optional[str]): Short textual description of the dish.
        price (Optional[Any]): Price value, which may vary in type (string, float, or object).
        ingredients (List[str]): List of primary ingredients used in the dish.
        serving_size (Optional[str]): The portion size or serving information.
        availability (Optional[bool]): Indicates if the dish is currently available.
        allergens (List[str]): List of potential allergens present in the dish.
        nutrition_facts (Dict[str, Any]): Key-value mapping of nutritional data
            (e.g., {"calories": 250, "protein": "10g"}).
    """
    dish_id: str
    dish_name : str = Field(default="N/A")
    description : Optional[str] = None
    price : Optional[Any] = None
    ingredients : List[str] = None
    serving_size : Optional[str] = None
    availability : Optional[bool] = None
    allergens : List[str] = None
    nutrition_facts : Dict[str, Any] = {}

class DishInfoResponse(BaseModel):
    """
    Encapsulates the response data for a dish information query.

    This model is used to represent structured responses from the
    `dish_info_service`, which extracts and returns specific details
    requested by the user about a dish.

    Attributes:
        dish_name (Optional[str]): The name of the dish requested.
        requested_info (Optional[str]): The specific type of information requested
            (e.g., "ingredients", "calories", "price").
        source_data (Optional[List[Any]]): Raw or processed data used to
            generate the final response.
    """
    dish_name : Optional[str] = None
    requested_info : Optional[str] = None
    source_data : Optional[List[Any]] = None

class IntentResponse(BaseModel):
    """
    Represents a basic intent classification result.

    This model is primarily used to store the high-level intent type
    extracted from a user's query (e.g., "dish_info", "menu_lookup").

    Attributes:
        type (str): The classified intent type.

    """
    type : str

class GeneralKnowledgeResponse(BaseModel):
    """
    Represents responses generated for general or non-specific user queries.

    This model captures general-purpose answers that are not tied to a
    particular restaurant or dish — such as food facts or cooking knowledge.

    Attributes:
        answer (str): The generated natural language response or explanation.
    """
    answer : str

class DishInfoResult(BaseModel):
    """
    Aggregates multiple dish information responses for a given request.

    This model maps dish names to their corresponding structured
    `DishInfoResponse` entries, allowing the system to handle
    multi-dish or multi-query responses efficiently.

    Attributes:
        info_results (Dict[str, DishInfoResponse]): Mapping of dish names
            to their detailed information responses.

    """
    info_results: Dict[str, DishInfoResponse]