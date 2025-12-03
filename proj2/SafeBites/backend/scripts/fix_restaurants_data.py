"""
Fix restaurants.json data structure to match the restaurant model.

This script converts MongoDB ObjectId format to simple string IDs.
"""

import json
import os

def fix_restaurants_data():
    """Fix the restaurant data structure."""
    # Define file path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    restaurants_file = os.path.join(base_dir, 'data', 'SafeBites_data', 'restaurants.json')

    print(f"Reading restaurants from: {restaurants_file}")

    # Load the data
    with open(restaurants_file, 'r') as f:
        restaurants = json.load(f)

    print(f"Loaded {len(restaurants)} restaurants")

    # Fix each restaurant
    fixed_restaurants = []
    for restaurant in restaurants:
        # Convert ObjectId format to simple string
        if isinstance(restaurant.get('_id'), dict) and '$oid' in restaurant['_id']:
            restaurant['_id'] = restaurant['_id']['$oid']

        fixed_restaurants.append(restaurant)

    # Write back the fixed data
    with open(restaurants_file, 'w') as f:
        json.dump(fixed_restaurants, f, indent=2)

    print(f"✓ Fixed {len(fixed_restaurants)} restaurants")
    print(f"✓ Updated file: {restaurants_file}")

    # Show a sample
    print("\nSample restaurant after fix:")
    sample = fixed_restaurants[0]
    print(f"  _id: {sample['_id']}")
    print(f"  name: {sample['name']}")
    print(f"  location: {sample['location']}")
    print(f"  cuisine: {sample['cuisine']}")
    print(f"  rating: {sample['rating']}")

if __name__ == "__main__":
    fix_restaurants_data()
