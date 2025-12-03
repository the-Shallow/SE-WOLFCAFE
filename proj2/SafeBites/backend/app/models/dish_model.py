"""
Defines Pydantic models for managing dish-related data in the SafeBites system.

This module includes schemas for creating, updating, and returning dish records,
as well as structured allergen information:

- AllergenInfo: Metadata about allergens present in a dish, including confidence and reasoning.
- DishCreate: Fields required to create a new dish entry.
- DishUpdate: Optional fields for updating an existing dish record.
- DishOut: Represents the dish object returned in API responses, including safety flags.

These models are used throughout the backend to ensure consistent data
representation for dishes, allergens, and nutritional information,
supporting both chat-based queries and API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

class AllergenInfo(BaseModel):
    """
    Represents metadata about a potential allergen found in a dish.

    This model provides structured information on allergens either explicitly
    declared or inferred from ingredients, including confidence levels and reasoning.

    Attributes:
        allergen (str): The name of the allergen (e.g., "peanuts", "dairy").
        confidence (Optional[float]): A numeric confidence score (0.0–1.0)
            indicating certainty about the allergen's presence.
        why (Optional[str]): An optional explanation describing how or why
            this allergen was detected or inferred.
    """
    allergen: str
    confidence: Optional[float] = None
    why: Optional[str] = None

class DishCreate(BaseModel):
    """
    Schema for creating a new dish entry in the database.

    This model defines all the fields required to create a dish record,
    including its basic details, allergens, and nutritional data.

    Attributes:
        restaurant_id (Optional[str]): ID of the restaurant that owns the dish.
        name (str): Name of the dish (e.g., "Grilled Chicken Caesar Salad").
        description (Optional[str]): Short textual description of the dish.
        ingredients (List[str]): List of ingredients used in the dish.
        price (float): Price of the dish in the restaurant's local currency.
        explicit_allergens (Optional[List[Union[str, AllergenInfo]]]): List of
            allergens explicitly provided or inferred, either as strings or
            detailed `AllergenInfo` objects.
        nutrition_facts (Optional[Dict[str, Any]]): Key-value pairs describing
            nutritional properties (e.g., {"calories": 450, "protein": "30g"}).
        serving_size (Optional[str]): The portion size or serving information.
        availability (Optional[bool]): Indicates if the dish is currently available.
    """
    restaurant_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    ingredients: List[str] = Field(default_factory=list)
    price: float
    explicit_allergens: Optional[List[Union[str, AllergenInfo]]] = Field(default_factory=list)
    nutrition_facts : Optional[Dict[str, Any]] = None
    serving_size: Optional[str] = None
    availability: Optional[bool] = True

class DishUpdate(BaseModel):
    """
    Schema for updating an existing dish record.

    All fields in this model are optional, allowing partial updates
    for flexibility in menu management or administrative interfaces.

    Attributes:
        restaurant_id (Optional[str]): ID of the restaurant owning the dish.
        name (Optional[str]): Updated name of the dish.
        description (Optional[str]): Updated dish description.
        ingredients (Optional[List[str]]): Updated list of ingredients.
        price (Optional[float]): Updated price value.
        explicit_allergens (Optional[List[Union[str, AllergenInfo]]]): Updated
            allergens list, either as strings or `AllergenInfo` entries.
        nutrition_facts (Optional[Dict[str, Any]]): Updated nutritional data.
        serving_size (Optional[str]): Updated serving size information.
        availability (Optional[bool]): Indicates if the dish should be marked
            available or unavailable.
    """
    restaurant_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    ingredients: Optional[List[str]] = None
    price: Optional[float] = None
    explicit_allergens: Optional[List[Union[str, AllergenInfo]]] = None
    nutrition_facts: Optional[Dict[str, Any]] = None
    serving_size: Optional[str] = None
    availability: Optional[bool] = None



class DishOut(BaseModel):
    """
    Schema for returning a dish object in API responses.

    This model is used when sending dish data to clients after creation,
    retrieval, or filtering operations. It includes all relevant dish
    attributes and a computed field for user safety (e.g., based on allergens).

    Attributes:
        id (str): Unique dish identifier (aliased from database `_id` field).
        restaurant_id (str): Identifier of the associated restaurant.
        name (str): Name of the dish.
        description (Optional[str]): Text description of the dish.
        ingredients (List[str]): List of ingredients used.
        price (float): The dish's price value.
        explicit_allergens (Optional[List[Union[str, AllergenInfo]]]): List of
            allergens associated with the dish.
        nutrition_facts (Optional[Dict[str, Any]]): Nutritional details.
        serving_size (Optional[str]): The portion size or serving information.
        availability (bool): Availability flag (True if currently offered).
        safe_for_user (bool): Indicates whether the dish is safe for a user
            based on their known allergies or dietary restrictions.
    """
    id: str = Field(..., alias="_id")
    restaurant_id: str
    name: str
    description: Optional[str]
    ingredients: List[str]
    price: float
    explicit_allergens: Optional[List[Union[str, AllergenInfo]]] = []
    nutrition_facts : Optional[Dict[str, Any]] = None
    serving_size: Optional[str] = None
    availability: bool = True
    # ALWAYS boolean now
    safe_for_user: bool
