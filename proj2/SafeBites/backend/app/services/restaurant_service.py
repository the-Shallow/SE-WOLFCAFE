"""
Restaurant Service Module

This module provides core functionality for managing restaurants and their menus,
including CRUD operations, menu CSV ingestion, dish enrichment, filtering, and validation.
"""
import csv
import pandas as pd
import logging
from bson import ObjectId
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.models.exception_model import NotFoundException, BadRequestException, DatabaseException,GenericException
from app.models.restaurant_model import RestaurantCreate, RestaurantUpdate, RestaurantInDB, DishFilterModel, DishValidationResult
from app.services.faiss_service import update_faiss_index
from app.db import get_db
from pymongo.errors import PyMongoError
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import os, json
from dotenv import load_dotenv
from ..models.dish_model import DishCreate
from ..utils.llm_tracker import LLMUsageTracker
from .dish_service import create_dish

logger = logging.getLogger(__name__)

load_dotenv()
db = get_db()

tmp_dir = "/tmp"
os.makedirs(tmp_dir, exist_ok=True)

llm = ChatOpenAI(model="gpt-4o-mini",temperature=1,openai_api_key=os.getenv("OPENAI_KEY"),callbacks=[LLMUsageTracker()])

restaurant_collection = db["restaurants"]

async def create_restaurant(restaurant:RestaurantCreate, menu_csv, background_tasks):
    """
        Creates a new restaurant in the database.

        Args:
            restaurant (RestaurantCreate): The restaurant data to create.
            Example:
            {
                "name": "Pasta Palace",
                "address": "123 Noodle St, Food City",
                "cuisine": "Italian",
                "rating":4.5
            }

        Returns:
            RestaurantInDB: The created restaurant with its ID.
    """
    try:
        result = restaurant_collection.insert_one(restaurant.dict())
        if not result.inserted_id:
            raise BadRequestException("Failed to create restaurant")
        
        file_path = os.path.join(tmp_dir, f"{result.inserted_id}_menu.csv")
        contents = await menu_csv.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        background_tasks.add_task(process_menu_file,file_path, str(result.inserted_id))
        return JSONResponse(status_code=201, content={"id": str(result.inserted_id)})
    except PyMongoError as e:
        raise DatabaseException(f"Database error: {str(e)}")
    except Exception as e:
        raise GenericException(f"Unexpected error: {str(e)}")
    

def process_menu_file(file_path:str,restaurant_id:str):
    """
    Process a restaurant menu CSV file and insert dishes into the database.

    Steps:
    1. Parse the CSV file to create DishCreate objects.
    2. Enrich dish information with ingredients, allergens, and nutrition facts if missing.
    3. Insert each dish into the database.
    4. Update FAISS index with newly created dishes.

    Parameters
    ----------
    file_path : str
        Path to the menu CSV file.
    restaurant_id : str
        The unique ID of the restaurant to associate the dishes with.

    Notes
    -----
    Logs any errors encountered during processing without stopping the entire batch.
    """
    try:
        dishes = parse_menu_csv(file_path,restaurant_id)
        created_dish = []
        print(dishes)
        for dish in dishes:
            if not dish.ingredients or not dish.explicit_allergens or not dish.nutrition_facts:
                enrich_dish_info(dish)
            print(dish.dict())
            inserted_dish = create_dish(restaurant_id, dish)
            print(inserted_dish)
        
        if created_dish:
            update_faiss_index(created_dish)
    except Exception as e:
        logger.error(f"Error processing menu file for restaurant {restaurant_id}: {str(e)}")

def enrich_dish_info(dish:DishCreate):
    """
    Enrich a dish with missing information using an LLM.

    Fills in the following fields if they are missing:
    - ingredients
    - inferred allergens (with confidence and reasoning)
    - nutrition facts (calories, protein, fat, carbohydrates, sugar, fiber)
    - summary description (one-line)

    Parameters
    ----------
    dish : DishCreate
        Dish object to enrich.

    Returns
    -------
    DishCreate
        Updated dish object with enriched fields.

    Notes
    -----
    Uses a GPT-5 model (via LangChain) to generate structured JSON output.
    Does not modify existing dish metadata like name, price, or availability.
    """
    llm = ChatOpenAI(model="gpt-5", api_key=os.environ.get("OPENAI_KEY"))
    prompt_template = ChatPromptTemplate.from_template("""
You are an allergen annotator for a restaurant dish database.

Given a dish name and description,ingredients(maybe) infer ONLY:
- ingredients (as a list of words/phrases) only if they are not present,
- allergens (list of {{allergen, confidence [0–1], why}}),
- nutrition_facts: object with approximate nutritional numeric values
- a one-line summary of the dish.

Do NOT return any other fields. 
Do NOT change dish name, description, price, or other metadata.

Allowed allergens: peanuts, tree_nuts, dairy, egg, soy, wheat_gluten, fish, shellfish, sesame.

Dish input:
Name: "{name}"
Description: "{description}"
Ingredients: "{ingredients}"

Output JSON ONLY:
{{
  "ingredients": [...],
  "inferred_allergens": [
    {{"allergen": "...", "confidence": 0.95, "why": "..."}}
  ],
    "nutrition_facts": object with approximate numeric values and confidences for:
    {{
      "calories": "value": number (kcal),
      "protein":"value": number (grams),
      "fat":"value": number (grams),
      "carbohydrates":"value": number (grams),
      "sugar":"value": number (grams),
      "fiber":"value": number (grams)
    }}
  "summary": "..."
}}
""")
    
    prompt = prompt_template.format_messages(
        name=dish.name,
        description=dish.description,
        ingredients=dish.ingredients
    )

    logger.debug(f"Printing generated prompt {prompt}")
    response = llm.invoke(prompt)

    try:
        refined = json.loads(response.content)
    except Exception as e:
        logger.error(str(e))
        return dish
    
    if not getattr(dish, "ingredients", []):
        print("Setting ingredients")
        dish.ingredients = refined.get("ingredients", [])

    if not getattr(dish, "explicit_allergens", []):
        print("Setting allergens")
        dish.explicit_allergens = refined.get("inferred_allergens", [])

    if not getattr(dish, "nutrition_facts", {}):
        print("Setting nutrition facts")
        dish.nutrition_facts = refined.get("nutrition_facts", {})

    if not getattr(dish, "description", ""):
        dish.description = refined.get("summary", "")

    # Ensure defaults exist
    if not hasattr(dish, "availability"):
        dish.availability = True
    # if not hasattr(dish, "serving_size"):
    #     dish.serving_size = "single"

    return dish


def parse_menu_csv(file_path:str,restaurant_id:str):
    """
    Parse a CSV file of dishes into a list of DishCreate objects.

    Parameters
    ----------
    file_path : str
        Path to the CSV file containing dish data.
    restaurant_id : str
        The restaurant ID to assign to each dish.

    Returns
    -------
    list[DishCreate]
        List of DishCreate objects parsed from the CSV.

    Notes
    -----
    - Handles different encodings (UTF-8, Latin1) automatically.
    - Converts fields such as ingredients, allergens, nutrition facts, availability.
    - Logs and skips rows with parsing errors without stopping the process.
    """
    dishes = []
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 failed for {file_path}, trying latin1")
        df = pd.read_csv(file_path, encoding='latin1')
    for num, row in df.iterrows():  # iterate over DataFrame rows
        try:
            # Handle possible NaN
            name = row.get("dish_name") or row.get("name") or "Unnamed Dish"
            description = row.get("description") if pd.notna(row.get("description")) else ""
            price = float(row["price"]) if pd.notna(row.get("price")) else 0.0

            ingredients = []
            if pd.notna(row.get("ingredients")):
                ingredients = [ing.strip() for ing in str(row.get("ingredients")).split(",") if ing.strip()]

            explicit_allergens = []
            if pd.notna(row.get("allergens")):
                explicit_allergens = [a.strip() for a in str(row.get("allergens")).split(",") if a.strip()]

            serving_size = row.get("serving_size") if pd.notna(row.get("serving_size")) else ""
            availability = str(row.get("availability", "True")).lower() in ("true", "1", "yes")

            nutrition_facts = {}
            if pd.notna(row.get("nutrition_facts")) and row.get("nutrition_facts").strip():
                try:
                    nutrition_facts = json.loads(row.get("nutrition_facts"))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid nutrition JSON in row {num}, defaulting to empty dict")

            dish = DishCreate(
                name=name,
                restaurant_id=restaurant_id,
                description=description,
                price=price,
                ingredients=ingredients,
                explicit_allergens=explicit_allergens,
                serving_size=serving_size,
                availability=availability,
                nutrition_facts=nutrition_facts
            )
            dishes.append(dish)
        except Exception as e:
            logger.error(f"Error parsing row {num}: {str(e)}")

    return dishes

def get_restaurant_by_id(restaurant_id:str):
    """
    Retrieves a restaurant by ID.
    
    Args:
        restaurant_id (str): The ID of the restaurant to retrieve.
            Example: "60c72b2f9b1d4c3f8c8e4b1a"
    Returns:
        RestaurantInDB: The restaurant data if found.
    """
    try:
        result = restaurant_collection.find_one({"_id":ObjectId(restaurant_id)})
        result["_id"] = str(result["_id"])
        if not result:
            raise NotFoundException(f"Restaurant with ID {restaurant_id} not found.")
        return JSONResponse(status_code=200, content=RestaurantInDB(**result).dict(by_alias=True))
    except PyMongoError as e:
        raise DatabaseException(f"Database error: {str(e)}")
    except Exception as e:
        raise GenericException(f"Unexpected error: {str(e)}")

async def get_restaurants():
    """
    Retrieves all restaurants from the database.
    Args:
        None
    Returns:
        List[RestaurantInDB]: A list of all restaurants.
    """
    try:
        results = []
        cursor = restaurant_collection.find()
        if not cursor:
            raise NotFoundException("No restaurants found.")
        for document in cursor:
            document["_id"] = str(document["_id"])
            results.append(RestaurantInDB(**document).dict(by_alias=True))
        return JSONResponse(status_code=200, content=results)
    except PyMongoError as e:
        raise DatabaseException(f"Database error: {str(e)}")
    except Exception as e:
        raise GenericException(f"Unexpected error: {str(e)}")
    
def update_restaurant(restaurant_id:str, restaurant:RestaurantUpdate):
    """
    Updates an existing restaurant by ID.
    
    Args:
        restaurant_id (str): The ID of the restaurant to update.
            Example: "60c72b2f9b1d4c3f8c8e4b1a"
        restaurant (RestaurantUpdate): The restaurant data to update.
            Example:
            {
                "name": "Pasta Palace",
                "address": "123 Noodle St, Food City",
                "cuisine": "Italian",
                "rating":4.5
            }
    Returns:
        RestaurantInDB: The updated restaurant data.
    """
    try:
        result = restaurant_collection.update_one(
            {"_id":ObjectId(restaurant_id)},
            {"$set": restaurant.dict(exclude_unset=True)}
        )
        if result.matched_count == 0:
            raise NotFoundException(f"Restaurant with ID {restaurant_id} not found.")
        if result.modified_count == 0:
            raise BadRequestException("No changes made to the restaurant.")
        updated_restaurant = restaurant_collection.find_one({"_id":ObjectId(restaurant_id)})
        updated_restaurant["_id"] = str(updated_restaurant["_id"])
        return JSONResponse(status_code=200, content=RestaurantInDB(**updated_restaurant).dict(by_alias=True))
    except PyMongoError as e:
        raise DatabaseException(f"Database error: {str(e)}")
    except Exception as e:
        raise GenericException(f"Unexpected error: {str(e)}")
    
def delete_restaurant(restaurant_id:str):
    """
    Deletes a restaurant by ID.
    Args:
        restaurant_id (str): The ID of the restaurant to delete.
            Example: "60c72b2f9b1d4c3f8c8e4b1a"
    Returns:
        dict: A message indicating successful deletion.
    """
    try:
        result = restaurant_collection.delete_one({"_id":ObjectId(restaurant_id)})
        if result.deleted_count == 0:
            raise NotFoundException(f"Restaurant with ID {restaurant_id} not found.")
        return JSONResponse(status_code=200, content={"message": f"Restaurant with ID {restaurant_id} deleted successfully."})
    except PyMongoError as e:
        raise DatabaseException(f"Database error: {str(e)}")
    except Exception as e:
        raise GenericException(f"Unexpected error: {str(e)}")
    


def apply_filters(query,dishes):
    """
    Extract and apply filters (price, ingredients, allergens, nutrition) to a list of dishes.

    Args:
        query (str): User query describing filter preferences.
        dishes (List[Dict]): List of dish objects with price, ingredients, and nutrition fields.

    Returns:
        List[Dict]: Filtered dishes matching user criteria.
    """
    logging.debug(f"Applying filters to : {dishes}")

    if not dishes:
        return []
    prompt_template = ChatPromptTemplate.from_template("""
You are a filter extraction model for a restaurant system.
Extract filters related to price, ingredients, allergens, or nutrition.

Return only JSON in this structure:
{{
  "price": {{"max": <float>, "min": <float>}},
  "ingredients": {{"include": [list], "exclude": [list]}},
  "allergens": {{"exclude": [list]}},
  "nutrition": {{"max_calories": <float>, "min_protein": <float>}}
}}

Rules:
- Extract only **true ingredients**, not dish types or categories.
  For example, "cheese", "chicken", "nuts", or "tomato" are ingredients.
  But "pizza", "burger", "pasta", or "sandwich" are **dish types**, not ingredients — exclude them.
- If the user asks for a specific dish type (like "List pizza dishes" or "Show me burgers"),
  leave the `ingredients.include` list empty.
- Use `price`, `allergens`, and `nutrition` only when mentioned.
- Never include a dish type (e.g. pizza, burger, pasta) in the ingredients list.

Example:
Query: "Show me chocolate dishes under 10 dollars."
Response:
{{
  "price": {{"max": 10, "min": 0}},
  "ingredients": {{"include": ["chocolate"], "exclude": []}},
  "allergens": {{"exclude": []}},
  "nutrition": {{}}
}}

Query: "List pizza dishes"
Response:
{{
  "price": {{}},
  "ingredients": {{"include": [], "exclude": []}},
  "allergens": {{}},
  "nutrition": {{}}
}}

Now analyze this query:
{query}
""")
    try:
        response =  llm.invoke(prompt_template.format_messages(query=query))
        raw_filters = json.loads(response.content)
        logger.debug(f"Extracted raw filters: {raw_filters}")
        price = raw_filters.get("price", {})
        min_price = price.get("min")
        max_price = price.get("max")

        # Convert to valid float values
        min_price = 0.0 if min_price in (None, "inf") else float(min_price)
        max_price = float("inf") if max_price in (None, "inf") else float(max_price)

        raw_filters["price"]["min"] = min_price
        raw_filters["price"]["max"] = max_price
        filters = DishFilterModel.parse_obj(raw_filters)
        logging.debug(f"Generated filters : {filters.dict()}")
    except Exception as e:
        raise GenericException(str(e))

    # price = filters.get("price",{})
    # include_ing = set(filters.get("ingredients",{}).get("include",[]))
    # exclude_ing = set(filters.get("ingredients",{}).get("exclude",[]))
    # exclude_allergens = set(filters.get("allergens",{}).get("exclude",[]))
    # nutrition = filters.get("nutrition",{})

    # DishData(
    #         dish_name=dish["name"],
    #         description=dish["description"],
    #         price=dish["price"],
    #         ingredients=dish["ingredients"],
    #         serving_size=dish["serving_size"],
    #         availability=dish["availaibility"],
    #         allergens=[a["allergen"] for a in dish["inferred_allergens"]],
    #         nutrition_facts=dish["nutrition_facts"]
    #     )

    def passes_nutrition_filter(dish):
        facts = dish.nutrition_facts
        logger.debug(f"Checking nutrition facts: {facts} against filters: {filters.nutrition}")
        # Helper to safely get numeric values
        def get_val(key):
            return facts.get(key, {}).get("value", 0)

        # Apply nutrition-based conditions (optional, only if present)
        n = filters.nutrition
        if n.max_calories and get_val("calories") > n.max_calories:
            return False
        if n.min_protein and get_val("protein") < n.min_protein:
            return False
        if n.max_fat and get_val("fat") > n.max_fat:
            return False
        if n.max_carbs and get_val("carbohydrates") > n.max_carbs:
            return False
        return True

    filtered = []
    for d in dishes:
        try:
            price = filters.price
            min_price = price.min
            max_price = price.max
            if not (min_price <= d.price <= max_price):
                continue
            if filters.ingredients.include and not set(filters.ingredients.include).issubset(set(d.ingredients)):
                continue
            if filters.ingredients.exclude and set(filters.ingredients.exclude).intersection(set(d.ingredients)):
                continue
            if filters.allergens.exclude and set(filters.allergens.exclude).intersection(
                set(d.allergens)
            ):
                continue
            if not passes_nutrition_filter(d):
                continue
            filtered.append(d)
        except Exception as e:
            logging.error(str(e))

    logging.debug(f"Filtered Dishes: {filtered}")
    return filtered

def validate_retrieved_dishes(query:str, dishes:list):
    if not dishes:
        return []

    prompt_template =ChatPromptTemplate.from_template("""
        You are an intelligent restaurant assistant helping to filter dishes for a user query.

        User query: {query}

        For each of the following dishes, decide whether it matches the user's request.
        Be strict but reasonable — match meaningfully relevant dishes, not partial overlaps.

        Output ONLY a valid JSON list:
        [
        {{"dish_id": "...", "include": true/false, "reason": "..."}},
        ...
        ]

        Dishes:
        {dishes}
    """)
    try:
        response =  llm.invoke(prompt_template.format_messages(query=query,dishes=dishes))
        parsed = json.loads(response.content)
        logging.debug(f"Filtered Dish IDs : {parsed}")
        validated = [DishValidationResult(**item) for item in parsed]
    except Exception as e:
        raise GenericException(str(e))

    valid_ids = {v.dish_id for v in validated if v.include }
    logging.debug(f"Valid Dish IDs : {valid_ids} ")
    filtered_dishes = [d for d in dishes if d.dish_id in valid_ids]
    logging.debug(f"Filtered Dishes by LLM : {filtered_dishes}")
    return filtered_dishes


@tool
def apply_menu_filters(
    dishes: list,
    excluded_ingredients: list = [],
    excluded_allergens: list = [],
    max_price: float | None = None,
    min_protein: float | None = None,
):
    """
    Apply deterministic filters to retrieved menu candidates.

    Use this to:
    - exclude allergens
    - exclude ingredients
    - filter by nutrition
    - filter by price
    """

    filtered = []
    
    for dish in dishes:
        if max_price is not None:
            price = dish.get("price")

            if price is not None and price > max_price:
                continue

        ingredients = [
            i.lower()
            for i in dish.get("ingredients", [])
        ]

        excluded_ingredients_lower = [
            i.lower()
            for i in excluded_ingredients
        ]

        if any(ex in ingredients for ex in excluded_ingredients_lower):
            continue

        allergens = []

        for a in dish.get("explicit_allergens", []):
            if isinstance(a, dict):
                allergens.append(a.get("allergen", "").lower())
            else:
                allergens.append(str(a).lower())

        for a in dish.get("inferred_allergens", []):
            if isinstance(a, dict):
                allergens.append(a.get("allergen", "").lower())

        excluded_allergens_lower = {
            a.lower()
            for a in excluded_allergens
        }

        if any(ex in allergens for ex in excluded_allergens_lower):
            continue
            
        if min_protein is not None:
            nutrition = dish.get("nutrition_facts", {})
            protein = dish.get("protein", {}).get("value")

            if protein is None or protein < min_protein:
                continue

        filtered.append(dish)

    return {
        "count": len(filtered),
        "results": filtered
    }


@tool
def handle_irrelvant_query(query:str):
    """
    Use this when the user query is not related to restaurant menus,
    dishes, ingredients, allergens, dietary preferences, price, cuisine,
    or food ordering.

    This tool should politely redirect the user back to food/menu-related help.
    """
    return {
        "type": "irrelevant_query",
        "message": (
            "I can help with restaurant menus, dishes, ingredients, allergens, "
            "dietary preferences, prices, and food recommendations. "
            "Please ask me something related to the menu or food."
        ),
        "original_query": query
    }