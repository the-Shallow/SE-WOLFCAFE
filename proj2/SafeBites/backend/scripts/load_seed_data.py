"""
Load seed data from JSON files into MongoDB database.

This script loads restaurants and dishes from the seed_data directory
into your MongoDB database.

Usage:
    python load_seed_data.py
"""

import json
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
load_dotenv(env_path)

# MongoDB connection
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME", "foodapp")

if not MONGO_URI:
    logger.error("MONGO_URI not found in environment variables!")
    sys.exit(1)

def load_json_file(filepath):
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} items from {os.path.basename(filepath)}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON in {filepath}: {e}")
        return []

def clear_collection(collection, collection_name):
    """Clear all documents from a collection."""
    result = collection.delete_many({})
    logger.info(f"Cleared {result.deleted_count} documents from '{collection_name}' collection")

def insert_documents(collection, documents, collection_name):
    """Insert documents into a collection."""
    if not documents:
        logger.warning(f"No documents to insert into '{collection_name}'")
        return 0

    try:
        result = collection.insert_many(documents, ordered=False)
        logger.info(f"Inserted {len(result.inserted_ids)} documents into '{collection_name}' collection")
        return len(result.inserted_ids)
    except Exception as e:
        logger.error(f"Error inserting documents into '{collection_name}': {e}")
        return 0

def main():
    """Main function to load seed data."""
    logger.info("=" * 60)
    logger.info("SAFEBITES SEED DATA LOADER")
    logger.info("=" * 60)

    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        client.admin.command('ping')
        logger.info(f"✓ Connected to MongoDB database: '{DB_NAME}'")
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {e}")
        sys.exit(1)

    # Define file paths
    seed_data_dir = os.path.join(base_dir, 'seed_data')
    safebites_data_dir = os.path.join(base_dir, 'data', 'SafeBites_data')

    # Ask user which data source to use
    print("\nWhich data source would you like to load?")
    print("1. seed_data/ (original seed data)")
    print("2. data/SafeBites_data/ (fixed production data)")
    data_source_choice = input("Enter choice (1 or 2, default: 2): ").strip() or "2"

    if data_source_choice == "2":
        data_dir = safebites_data_dir
        restaurants_file = os.path.join(data_dir, 'restaurants.json')
        dishes_file = os.path.join(data_dir, 'dishes.json')

        # Check if files exist
        if not os.path.exists(restaurants_file):
            logger.error(f"restaurants.json not found in {data_dir}")
            sys.exit(1)
        if not os.path.exists(dishes_file):
            logger.error(f"dishes.json not found in {data_dir}")
            sys.exit(1)

        dish_file_to_use = dishes_file
    else:
        data_dir = seed_data_dir
        restaurants_file = os.path.join(data_dir, 'restaurants.json')
        dishes_file = os.path.join(data_dir, 'dishes.json')
        dishes_refined_file = os.path.join(data_dir, 'dishes_refined.json')

        # Check if files exist
        if not os.path.exists(restaurants_file):
            logger.error(f"restaurants.json not found in {data_dir}")
            logger.info("Run 'python generate_seed.py' first to generate seed data")
            sys.exit(1)

        # Ask user which dish file to use
        print("\nWhich dish file would you like to load?")
        print("1. dishes.json (60 basic dishes without allergen data)")
        print("2. dishes_refined.json (16 dishes enriched with allergen & nutrition data)")
        choice = input("Enter choice (1 or 2, default: 2): ").strip() or "2"

        dish_file_to_use = dishes_refined_file if choice == "2" else dishes_file

        if not os.path.exists(dish_file_to_use):
            logger.error(f"{os.path.basename(dish_file_to_use)} not found!")
            sys.exit(1)

    # Ask if user wants to clear existing data
    print("\n⚠️  Do you want to clear existing data before loading?")
    clear_choice = input("Enter 'yes' to clear, anything else to skip: ").strip().lower()

    # Load data from files
    logger.info("\nLoading data from JSON files...")
    restaurants = load_json_file(restaurants_file)
    dishes = load_json_file(dish_file_to_use)

    if not restaurants or not dishes:
        logger.error("Failed to load seed data. Exiting.")
        sys.exit(1)

    # Get collections
    restaurants_collection = db['restaurants']
    dishes_collection = db['dishes']

    # Clear collections if requested
    if clear_choice == 'yes':
        logger.info("\nClearing existing collections...")
        clear_collection(restaurants_collection, 'restaurants')
        clear_collection(dishes_collection, 'dishes')

    # Insert data
    logger.info("\nInserting data into database...")
    restaurant_count = insert_documents(restaurants_collection, restaurants, 'restaurants')
    dish_count = insert_documents(dishes_collection, dishes, 'dishes')

    # Verify insertion
    logger.info("\n" + "-" * 60)
    logger.info("Verifying data insertion...")
    total_restaurants = restaurants_collection.count_documents({})
    total_dishes = dishes_collection.count_documents({})

    logger.info(f"✓ Total restaurants in database: {total_restaurants}")
    logger.info(f"✓ Total dishes in database: {total_dishes}")

    # Display sample data
    logger.info("\n" + "-" * 60)
    logger.info("Sample Restaurant:")
    sample_restaurant = restaurants_collection.find_one()
    if sample_restaurant:
        logger.info(f"  Name: {sample_restaurant.get('name')}")
        logger.info(f"  Cuisine: {sample_restaurant.get('cuisine')}")
        logger.info(f"  Address: {sample_restaurant.get('address')}")

    logger.info("\nSample Dish:")
    sample_dish = dishes_collection.find_one()
    if sample_dish:
        logger.info(f"  Name: {sample_dish.get('name')}")
        logger.info(f"  Price: ${sample_dish.get('price')}")
        logger.info(f"  Restaurant ID: {sample_dish.get('restaurant_id')}")
        ingredients = sample_dish.get('ingredients', [])
        logger.info(f"  Ingredients: {', '.join(ingredients[:3])}...")

        if 'explicit_allergens' in sample_dish and sample_dish.get('explicit_allergens'):
            allergens = [f"{a['allergen']} ({a.get('confidence', 0):.2f})"
                        for a in sample_dish.get('explicit_allergens', [])]
            logger.info(f"  Allergens: {', '.join(allergens)}")

        if 'nutrition_facts' in sample_dish:
            nutrition = sample_dish.get('nutrition_facts', {})
            if nutrition:
                cal = nutrition.get('calories', {}).get('value', 'N/A')
                logger.info(f"  Nutrition: {cal} calories")

    logger.info("\n" + "=" * 60)
    logger.info("✓ SEED DATA LOADED SUCCESSFULLY!")
    logger.info("=" * 60)

    # Show next steps
    logger.info("\nNext steps:")
    logger.info("1. Start the backend server: uvicorn app.main:app --reload")
    logger.info("2. Rebuild FAISS index (will happen automatically on server startup)")
    logger.info("3. Create a user account and test the search functionality")

    # Close connection
    client.close()
    logger.info("\nMongoDB connection closed.")

if __name__ == "__main__":
    main()
