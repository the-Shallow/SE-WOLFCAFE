"""
Defines API endpoints for managing restaurants and handling user menu queries.

Endpoints include:
    - POST /restaurants/ : Create a new restaurant entry (with optional menu CSV upload).
    - GET /restaurants/ : Retrieve a list of all restaurants.
    - GET /restaurants/{restaurant_id} : Retrieve a specific restaurant by ID.
    - PATCH /restaurants/{restaurant_id} : Update details of an existing restaurant.
    - DELETE /restaurants/{restaurant_id} : Delete a restaurant by ID.
    - POST /restaurants/search : Perform user menu queries using multi-agent pipeline.
    - GET /restaurants/history/{user_id}/{restaurant_id} : Retrieve chat history for a user and restaurant.
"""
from fastapi import APIRouter,HTTPException, Depends,Form,UploadFile,File,BackgroundTasks
from bson import ObjectId
from fastapi.responses import JSONResponse
from ..models.restaurant_model import RestaurantCreate, RestaurantUpdate, RestaurantBase, RestaurantInDB
from ..services import restaurant_service, state_service
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..services.orchestrator_service import agents
from ..services.intent_service import extract_query_intent
from ..flow.graph import create_chat_graph
from ..flow.state import ChatState
from fastapi.encoders import jsonable_encoder
from ..flow.state_store import state_store
router = APIRouter(prefix="/restaurants", tags=["restaurants"])
import logging

logger = logging.getLogger(__name__)

@router.post("/",response_model=RestaurantInDB)
async def create_restaurant(
    background_tasks : BackgroundTasks,
    restaurant_name : str = Form(...),
    location:str = Form(...),
    cuisine:str = Form(...),
    rating:float = Form(...),
    menu_csv : UploadFile = File(...)
):
    """
        Create a new restaurant entry in the database. If allergen information is not provided, 
        it will be inferred using an external service.

        Args:
            restaurant(RestaurantCreate): The restaurant data provided by the client.
        
        Returns:
            RestaurantInDB: The created restaurant entry with its unique ID.
    """
    cuisine = cuisine.split(",") if cuisine else []
    return await restaurant_service.create_restaurant(RestaurantCreate(name=restaurant_name,location=location,cuisine=cuisine,rating=rating),menu_csv,background_tasks)

@router.get("/",response_model=list[RestaurantInDB])
async def list_restaurants():
    """
        Retrieve a list of all restaurants in the database.
        Args:
            None
        
        Returns:
            list[RestaurantInDB]: A list of all restaurant entries in the database.
    """
    return await restaurant_service.get_restaurants()

class ChatQuery(BaseModel):
    query: str
    user_id: Optional[str] = None
    restaurant_id: Optional[str] = None

@router.post("/search")
async def chat_search(payload: ChatQuery):
    """
    Endpoint to handle user menu queries using the multi-agent pipeline.
    Returns a structured JSON suitable for frontend rendering.

    Includes user allergen preferences in the context automatically.
    """
    try:
        query = payload.query
        user_id = payload.user_id or "guest"  # Use "guest" if no user_id provided
        restaurant_id = payload.restaurant_id

        session_id = state_service.get_or_create_session(user_id, restaurant_id)

        context = state_service.rebuild_context(session_id, user_id if user_id != "guest" else None)
        logger.debug(f"Rebuilt Context: {context}")

        chat_graph = create_chat_graph()
        state = ChatState(user_id=user_id, session_id=session_id, restaurant_id=restaurant_id, query=query, query_parts={},
                          context=context,current_context="")

        final_state = chat_graph.invoke(state)
        logger.debug(f"Final State: {final_state}")
        state_service.save_chat_state(final_state)
        return JSONResponse(status_code=200, content=jsonable_encoder(final_state))
    except Exception as e:
        logger.error(f"Error in chat_search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}/{restaurant_id}")
def chat_history(user_id:str, restaurant_id:str):
    try:
        session_id = state_service.get_or_create_session(user_id, restaurant_id)
        chat_states = state_service.get_chat_history(session_id)

        return JSONResponse(status_code=200, content=jsonable_encoder(chat_states))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{restaurant_id}",response_model=RestaurantInDB)
def get_restaurant(restaurant_id:str):
    """
        Retrieve a specific restaurant by its ID.

        Args:
            restaurant_id(str): The unique identifier of the restaurant.
        
        Returns:
            RestaurantInDB: The restaurant entry corresponding to the provided ID.
        
        Raises:
            HTTPException(404): If no restaurant with the given ID is found.
    """
    return restaurant_service.get_restaurant_by_id(restaurant_id)

@router.patch("/{restaurant_id}",response_model=RestaurantInDB)
def update_restaurant(restaurant_id:str,updates:RestaurantUpdate):
    """
        Update an existing restaurant's information.

        Args:
            restaurant_id(str): The unique identifier of the restaurant to be updated.
            updates(RestaurantUpdate): The fields to be updated with their new values.

        Returns:
            RestaurantInDB: The updated restaurant entry.
        Raises:
            HTTPException(404): If no restaurant with the given ID is found.
    """
    return restaurant_service.update_restaurant(restaurant_id,updates)

@router.delete("/{restaurant_id}")
def delete_restaurant(restaurant_id:str):
    """
        Delete a restaurant from the database.

        Args:
            restaurant_id(str): The unique identifier of the restaurant to be deleted.

        Returns:
            None

        Raises:
            HTTPException(404): If no restaurant with the given ID is found.
    """
    return restaurant_service.delete_restaurant(restaurant_id)