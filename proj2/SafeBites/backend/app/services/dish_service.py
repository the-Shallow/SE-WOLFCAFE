"""
Dish Service Module

This module provides CRUD operations for managing dish documents in the
database. It integrates MongoDB operations with Pydantic validation and
allergen safety checks for users.
"""
from ..db import db
from bson import ObjectId
from fastapi import HTTPException
from bson.objectid import ObjectId
from app.models.exception_model import NotFoundException, BadRequestException, DatabaseException, ConflictException
from langchain_core.tools import tool


def _to_out(doc: dict) -> dict:
    """
    Convert a MongoDB document to a serializable format by converting
    the `_id` field to a string. Returns the modified document.
    """
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    return doc

def create_dish(restaurant_id: str, dish_create):
    """
    Create a new dish entry for a given restaurant.

    Args:
        restaurant_id (str): The restaurant's unique identifier.
        dish_create (DishCreate): Pydantic model containing dish creation details.

    Raises:
        BadRequestException: If required fields are missing.
        ConflictException: If a dish with the same name already exists in the restaurant.
        DatabaseException: If database insertion fails.

    Returns:
        dict: The created dish document with `safe_for_user` field included.
    """
    if not dish_create.name or not dish_create.restaurant_id:
        raise BadRequestException(message="Missing required dish fields")
    # enforce unique dish name per restaurant
    existing = db.dishes.find_one({"name": dish_create.name, "restaurant_id": dish_create.restaurant_id})
    if existing:
        raise ConflictException(detail="Dish with same name already exists for this restaurant")

    doc = dish_create.model_dump()
    doc["availability"] = doc.get("availability", True)
    try:
        res = db.dishes.insert_one(doc)
        created = db.dishes.find_one({"_id": res.inserted_id})
        out = _to_out(created)
        out["safe_for_user"] = True  # default
        return out
    except Exception as e:
        raise DatabaseException(message=f"Failed to create dish: {e}")
    

def list_dishes(filter_query: dict, user_id: str = None):
    """
    List dishes that match a given filter query.
    Automatically attaches a `safe_for_user` boolean for each dish based on user allergens.

    Args:
        filter_query (dict): MongoDB filter criteria.
        user_id (str, optional): User ID to check allergen safety. Defaults to None.

    Raises:
        DatabaseException: If there is an issue fetching dishes from the database.

    Returns:
        list[dict]: List of dish documents, each including `safe_for_user` status.
    """
    try:
        docs = list(db.dishes.find(filter_query).limit(100))
        print(docs)
        out = []
        user_allergens = []

        # Get user allergens if user_id provided
        if user_id:
            try:
                user_doc = db.users.find_one({"_id": ObjectId(user_id)})
                print(user_doc)
                if user_doc:
                    user_allergens = [a.lower() for a in user_doc.get("allergen_preferences", [])]
            except Exception:
                pass

        for d in docs:
            d_out = _to_out(d)
            dish_all = [a["allergen"].lower() for a in d_out.get("explicit_allergens", [])]

            if user_allergens:
                d_out["safe_for_user"] = len(set(dish_all) & set(user_allergens)) == 0
            else:
                d_out["safe_for_user"] = True

            out.append(d_out)

        return out
    except Exception as e:
        raise DatabaseException(message=f"Failed to list dishes: {e}")

def get_dish(dish_id: str, user_id: str = None):
    """
    Retrieve a single dish by its ID and determine if it's safe for a user based on allergens.

    Args:
        dish_id (str): The unique dish identifier.
        user_id (str, optional): The user's ID for allergen safety check. Defaults to None.

    Raises:
        NotFoundException: If the dish does not exist or invalid ID is provided.

    Returns:
        dict: The dish document with `safe_for_user` field attached.
    """
    try:
        obj = ObjectId(dish_id)
    except Exception:
        raise NotFoundException(name="Invalid dish id")

    doc = db.dishes.find_one({"_id": obj})
    if not doc:
        raise NotFoundException(name="Dish not found")

    d_out = _to_out(doc)
    dish_all = [a["allergen"].lower() for a in d_out.get("explicit_allergens", [])]

    if user_id:
        try:
            user_doc = db.users.find_one({"_id": ObjectId(user_id)})
            user_allergens = [a.lower() for a in user_doc.get("allergen_preferences", [])] if user_doc else []
            d_out["safe_for_user"] = len(set(dish_all) & set(user_allergens)) == 0
        except Exception:
            d_out["safe_for_user"] = True
    else:
        d_out["safe_for_user"] = True

    return d_out

def update_dish(dish_id: str, update_data: dict):
    """
    Update a dish’s details by its ID. Checks for duplicate dish names within the same restaurant.

    Args:
        dish_id (str): Unique identifier of the dish to update.
        update_data (dict): Fields to update with their new values.

    Raises:
        BadRequestException: If no update data is provided.
        NotFoundException: If the dish does not exist.
        ConflictException: If another dish with the same name exists in the restaurant.

    Returns:
        dict: The updated dish document including `safe_for_user`.
    """
    if not update_data:
        raise BadRequestException(message="No fields to update")

    try:
        obj = ObjectId(dish_id)
    except Exception:
        raise NotFoundException(name="Invalid dish id")
    if "name" in update_data or "restaurant" in update_data:
        current = db.dishes.find_one({"_id": obj})
        if not current:
            raise NotFoundException(name="Dish not found")
        new_name = update_data.get("name", current.get("name"))
        new_rest = update_data.get("restaurant", current.get("restaurant"))
        other = db.dishes.find_one({"name": new_name, "restaurant": new_rest, "_id": {"$ne": obj}})
        if other:
            raise ConflictException(detail="Another dish with same name exists in the restaurant")

    res = db.dishes.update_one({"_id": obj}, {"$set": update_data})
    if res.matched_count == 0:
        raise NotFoundException(name="Dish not found")

    updated = db.dishes.find_one({"_id": obj})
    out = _to_out(updated)
    out["safe_for_user"] = True
    return out


def delete_dish(dish_id: str):
    """
    Delete a dish document by its ID.

    Args:
        dish_id (str): The dish's unique identifier.

    Raises:
        NotFoundException: If the dish ID is invalid or not found.

    Returns:
        dict: Confirmation message indicating successful deletion.
    """
    try:
        obj = ObjectId(dish_id)
    except Exception:
        raise NotFoundException(name="Invalid dish id")

    res = db.dishes.delete_one({"_id": obj})
    if res.deleted_count == 0:
        raise NotFoundException(name="Dish not found")

    return {"detail": "deleted"}


@tool
def get_dish_details(dish_name: str, restaurant_id: str | None = "None"):
    """
        Get full dish details such as price, ingredients, allergens,
        nutrition facts, and availability.
    """
    query = {
        "name" : {"$regex": dish_name, "$options": "i"}
    }

    if restaurant_id:
        query["restaurant_id"] = restaurant_id

    dish = db.dishes.find_one(query)
    if not dish:
        return {
            "found" : False,
            "message": f"No dish found matching {dish_name}"
        }
    
    dish["_id"] = str(dish["_id"])

    return {
        "found": True,
        "dish_id": dish.get("_id"),
        "restaurant_id": dish.get("restaurant_id"),
        "dish_name": dish.get("name"),
        "description": dish.get("description"),
        "price": dish.get("price"),
        "ingredients": dish.get("ingredients",[]),
        "explicit_allergens": dish.get("explicit_allergens", []),
        "inferred_allergens": dish.get("inferred_allergens", []),
        "nutrition_facts": dish.get("nutrition_facts", {}),
    }

