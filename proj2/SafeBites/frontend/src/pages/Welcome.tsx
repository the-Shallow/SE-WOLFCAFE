import { useNavigate, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";
import "./Welcome.css";

interface Restaurant {
  _id: string;
  name: string;
  location: string;
  cuisine: string[];
  rating: number;
}

function Welcome() {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [allRestaurants, setAllRestaurants] = useState<Restaurant[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Check if user is logged in
  useEffect(() => {
    const authToken = localStorage.getItem("authToken");
    setIsLoggedIn(!!authToken);
  }, []);

  // Fetch all restaurants for search
  useEffect(() => {
    const fetchRestaurants = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/restaurants/`);
        if (response.ok) {
          const data = await response.json();
          setAllRestaurants(data);
        }
      } catch (error) {
        console.error("Error fetching restaurants:", error);
      }
    };

    fetchRestaurants();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("username");
    setIsLoggedIn(false);
    navigate("/");
  };

  const handleSearch = () => {
    if (!searchTerm.trim()) {
      // No search term, navigate to dashboard with all restaurants
      navigate("/dashboard", {
        state: { searchResults: allRestaurants, searchTerm: "" },
      });
      return;
    }

    setIsSearching(true);

    // Create case-insensitive regex for search
    const regex = new RegExp(searchTerm, "i");

    // Filter restaurants by name or location
    const filteredResults = allRestaurants.filter(
      (restaurant) =>
        regex.test(restaurant.name) || regex.test(restaurant.location)
    );

    // Navigate to dashboard with search results
    navigate("/dashboard", {
      state: {
        searchResults: filteredResults,
        searchTerm: searchTerm.trim(),
      },
    });

    setIsSearching(false);
  };

  const handleSearchKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="welcome-container">
      {/* Header */}
      <header className="welcome-header">
        <Link
          to="/"
          className="logo"
          style={{
            textDecoration: "none",
            color: "inherit",
            cursor: "pointer",
          }}
        >
          <img src="/wolfLogo.png" alt="SafeBites Logo" className="logo-img" />
          <h1>SafeBites</h1>
        </Link>

        <div className="header-buttons">
          {isLoggedIn ? (
            <>
              <button
                className="header-dashboard-btn"
                onClick={() => navigate("/dashboard")}
              >
                Dashboard
              </button>
              <button className="header-signout-btn" onClick={handleLogout}>
                Sign Out
              </button>
            </>
          ) : (
            <button
              className="header-signin-btn"
              onClick={() => navigate("/login")}
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Hero Section with Search */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">Find Restaurants Near You</h1>
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search by restaurant name, address, or zip code"
              className="search-input"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={handleSearchKeyPress}
            />
            <button
              className="search-button"
              onClick={handleSearch}
              disabled={isSearching}
            >
              <img
                src="/icons/icons8-search-24.png"
                alt="Search"
                className="search-icon"
              />
            </button>
          </div>
          {isSearching && (
            <p className="search-status">Searching restaurants...</p>
          )}
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="feature-card-large">
          <img
            src="/icons/victoruler-flaticon-food-package.png"
            alt="Allergen Protection"
            className="feature-icon-img"
          />
          <h2>Eat Safely, Every Time</h2>
          <p>
            Never worry about hidden allergens again. Our intelligent filtering
            instantly removes unsafe dishes, showing you only meals you can
            enjoy with confidence.
          </p>
        </div>

        <div className="feature-card-large">
          <img
            src="/icons/parzival-flaticon-chatbot.png"
            alt="AI Search"
            className="feature-icon-img"
          />
          <h2>Search Like You Talk</h2>
          <p>
            Forget complex filters—just ask! Chat naturally with our AI to find
            exactly what you're craving, whether it's "low-sodium options" or
            "vegan desserts nearby."
          </p>
        </div>

        <div className="feature-card-large">
          <img
            src="/icons/freepik-flaticon-selection.png"
            alt="Smart Filtering"
            className="feature-icon-img"
          />
          <h2>Set It Once, Use It Forever</h2>
          <p>
            Tell us your allergies and preferences once. Every time you search,
            SafeBites automatically protects you—making safe dining effortless
            and stress-free.
          </p>
        </div>
      </section>

      {/* About Section */}
      <section className="about-section">
        <div className="about-image">
          <img src="/foodImages/foodAllergy.jpg" alt="Food Allergy Items" />
        </div>
        <div className="about-content">
          <h2>About SafeBites</h2>
          <p>
            Dining out shouldn't be a guessing game. SafeBites uses AI to help
            people with food allergies and dietary restrictions find safe,
            delicious meals at their favorite restaurants—instantly.
          </p>
          <p>
            Our intelligent platform analyzes restaurant menus, detects
            allergens, and filters dishes based on your personal dietary
            profile. No more scrolling through unsafe options or worrying about
            hidden ingredients. Just ask what you want, and SafeBites delivers
            personalized recommendations you can trust.
          </p>
          <p className="tagline">Safe dining made simple.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="welcome-footer">
        <div className="footer-content">
          <div className="footer-column">
            <h3>Get to know us</h3>
            <ul>
              <li>
                <a href="#">About Us</a>
              </li>
              <li>
                <a href="#">Our Apps</a>
              </li>
              <li>
                <a href="#">Careers</a>
              </li>
              <li>
                <a href="#">Investors</a>
              </li>
              <li>
                <a href="#">Blogs</a>
              </li>
            </ul>
          </div>

          <div className="footer-column">
            <h3>Useful links</h3>
            <ul>
              <li>
                <a href="#">Help</a>
              </li>
              <li>
                <a href="#">Gift Cards</a>
              </li>
              <li>
                <a href="#">Account Details</a>
              </li>
              <li>
                <a href="#">Catering</a>
              </li>
            </ul>
          </div>

          <div className="footer-column">
            <h3>Doing Business</h3>
            <ul>
              <li>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    navigate("/add-restaurant");
                  }}
                >
                  Add your restaurant
                </a>
              </li>
              <li>
                <a href="#">Sign up to deliver</a>
              </li>
              <li>
                <a href="#">Create a business account</a>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-links">
            <a href="#">Terms of Use</a>
            <a href="#">Privacy Policy</a>
            <a href="#">Do not sell or share my personal information</a>
          </div>
          <div className="footer-right">
            <div className="social-icons">
              <img
                src="/icons/icons8-twitter-bird-24.png"
                alt="Twitter"
                className="Twitter-icon"
              />
              <img
                src="/icons/icons8-facebook-circled-24.png"
                alt="Facebook"
                className="Facebook-icon"
              />
              <img
                src="/icons/icons8-instagram-24.png"
                alt="Instagram"
                className="Instagram-icon"
              />
            </div>
            <p className="footer-copyright">&copy; 2025 SafeBites - Group 6</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Welcome;
