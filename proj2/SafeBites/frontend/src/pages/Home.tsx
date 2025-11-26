import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import './Home.css';
import RestaurantMenu from './RestaurantMenu';

interface Restaurant {
  _id: string;
  name: string;
  location: string;
  cuisine: string[];
  rating: number;
}

function Home() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [filteredRestaurants, setFilteredRestaurants] = useState<Restaurant[]>([]);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [sortBy, setSortBy] = useState<string>("none");
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch restaurants from API
  useEffect(() => {
    const fetchRestaurants = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const response = await fetch(`${API_BASE_URL}/restaurants/`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch restaurants: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Fetched restaurants:', data);
        
        setRestaurants(data);
        setFilteredRestaurants(data);
      } catch (err) {
        console.error('Error fetching restaurants:', err);
        setError(err instanceof Error ? err.message : 'Failed to load restaurants');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRestaurants();
  }, []);

  // Apply sorting
  useEffect(() => {
    let sorted = [...restaurants];

    if (sortBy === "name-asc") {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "name-desc") {
      sorted.sort((a, b) => b.name.localeCompare(a.name));
    } else if (sortBy === "rating-desc") {
      sorted.sort((a, b) => b.rating - a.rating);
    } else if (sortBy === "rating-asc") {
      sorted.sort((a, b) => a.rating - b.rating);
    }

    setFilteredRestaurants(sorted);
  }, [sortBy, restaurants]);

  const handleRestaurantClick = (restaurant: Restaurant) => {
    setSelectedRestaurant(restaurant);
    setIsPopupOpen(true);
  };

  const closePopup = () => {
    setIsPopupOpen(false);
    setTimeout(() => setSelectedRestaurant(null), 300);
  };

  return (
    <div className="home-container">
      <h1 className="page-title">Explore Restaurants</h1>

      {/* Filter Section */}
      <div className="filter-section">
        <button 
          className="filter-toggle-btn"
          onClick={() => setIsFilterOpen(!isFilterOpen)}
        >
          {isFilterOpen ? '▼' : '▶'} Sort & Filter
        </button>
      </div>

      {isFilterOpen && (
        <div className="filter-container">
          <div className="filter-group">
            <label className="filter-label">Sort by Name:</label>
            <div className="filter-options">
              <button 
                className={`filter-option-btn ${sortBy === "name-asc" ? 'active' : ''}`}
                onClick={() => setSortBy("name-asc")}
              >
                A → Z
              </button>
              <button 
                className={`filter-option-btn ${sortBy === "name-desc" ? 'active' : ''}`}
                onClick={() => setSortBy("name-desc")}
              >
                Z → A
              </button>
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-label">Sort by Rating:</label>
            <div className="filter-options">
              <button 
                className={`filter-option-btn ${sortBy === "rating-desc" ? 'active' : ''}`}
                onClick={() => setSortBy("rating-desc")}
              >
                Highest First
              </button>
              <button 
                className={`filter-option-btn ${sortBy === "rating-asc" ? 'active' : ''}`}
                onClick={() => setSortBy("rating-asc")}
              >
                Lowest First
              </button>
            </div>
          </div>

          <button 
            className="clear-filter-btn"
            onClick={() => setSortBy("none")}
          >
            Clear Filters
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="loading-container">
          <p>Loading restaurants...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-container">
          <p>Error: {error}</p>
          <p>Please try again later.</p>
        </div>
      )}

      {/* Restaurant Cards Grid */}
      {!isLoading && !error && (
        <div className="restaurant-grid">
          {filteredRestaurants.length === 0 ? (
            <p>No restaurants found.</p>
          ) : (
            filteredRestaurants.map((restaurant) => (
              <div 
                key={restaurant._id} 
                className="restaurant-card"
                onClick={() => handleRestaurantClick(restaurant)}
              >
                <div className="restaurant-card-content">
                  <h2 className="restaurant-name">{restaurant.name}</h2>
                  
                  <div className="restaurant-rating">
                    <img src="/icons/pixel_perfect_flaticon_star.png" alt="Rating" className="star-icon" />
                    <span className="rating-value">{restaurant.rating.toFixed(1)}</span>
                  </div>
                  
                  <div className="restaurant-cuisine">
                    {restaurant.cuisine.join(', ')}
                  </div>
                  
                  <div className="restaurant-location">
                    <img src="/icons/md_tanvirul_haque_flaticon_location.png" alt="Location" className="location-icon" />
                    {restaurant.location}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Popup Modal */}
      {selectedRestaurant && (
        <RestaurantMenu 
          restaurant={selectedRestaurant}
          isOpen={isPopupOpen}
          onClose={closePopup}
        />
      )}
    </div>
  );
}

export default Home;