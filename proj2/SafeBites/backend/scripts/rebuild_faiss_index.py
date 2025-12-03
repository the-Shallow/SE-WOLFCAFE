"""
Rebuild FAISS Index Script

This script rebuilds the FAISS vector index from the dishes in the database.
Run this after updating dish data or changing the embedding structure.
"""
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.faiss_service import build_faiss_from_db
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    print("Starting FAISS index rebuild...")
    try:
        build_faiss_from_db()
        print("✓ FAISS index successfully rebuilt!")
    except Exception as e:
        print(f"✗ Error rebuilding FAISS index: {e}")
        sys.exit(1)
