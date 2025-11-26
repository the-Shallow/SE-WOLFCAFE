import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_ENDPOINTS } from '../config/api';
import './AddRestaurant.css';

function AddRestaurant() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    restaurantName: '',
    cuisine: [] as string[],
    street: '',
    city: '',
    state: '',
    zipCode: '',
    description: '',
    rating: ''
  });
  const [menuCsv, setMenuCsv] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const cuisineOptions = [
    'Italian', 'Japanese', 'Chinese', 'Mexican', 'Thai',
    'Indian', 'American', 'French', 'Mediterranean', 'Korean',
    'Vietnamese', 'Greek', 'Spanish', 'Brazilian', 'Middle Eastern'
  ];

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleCuisineToggle = (cuisine: string) => {
    setFormData(prev => ({
      ...prev,
      cuisine: prev.cuisine.includes(cuisine)
        ? prev.cuisine.filter(c => c !== cuisine)
        : [...prev.cuisine, cuisine]
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        alert('Please upload a CSV file');
        e.target.value = '';
        return;
      }
      setMenuCsv(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.restaurantName.trim()) {
      alert('Please enter restaurant name');
      return;
    }
    if (formData.cuisine.length === 0) {
      alert('Please select at least one cuisine type');
      return;
    }
    if (!formData.street.trim() || !formData.city.trim() || !formData.state.trim() || !formData.zipCode.trim()) {
      alert('Please fill in all address fields');
      return;
    }
    if (!formData.rating || parseFloat(formData.rating) < 0 || parseFloat(formData.rating) > 5) {
      alert('Please enter a valid rating between 0 and 5');
      return;
    }
    if (!menuCsv) {
      alert('Please upload a menu CSV file');
      return;
    }

    setIsSubmitting(true);

    try {
      // Combine address fields into location string
      const location = `${formData.street}, ${formData.city}, ${formData.state} ${formData.zipCode}`;
      
      // Create FormData for multipart/form-data
      const apiFormData = new FormData();
      apiFormData.append('restaurant_name', formData.restaurantName);
      apiFormData.append('location', location);
      apiFormData.append('cuisine', formData.cuisine.join(', ')); // Join multiple cuisines
      apiFormData.append('rating', formData.rating);
      apiFormData.append('menu_csv', menuCsv);

      // Submit to API
      for (let pair of apiFormData.entries()) {
  console.log(pair[0] + ':', pair[1]);
}
      console.log('Submitting restaurant:', {...formData, location, menuCsvName: menuCsv.name});
      const response = await fetch(API_ENDPOINTS.restaurants.base, {
        method: 'POST',
        body: apiFormData,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();
      console.log('Restaurant created:', result);
      
      alert('Restaurant submitted successfully! We will review your application.');
      navigate('/');
    } catch (error) {
      console.error('Error submitting restaurant:', error);
      alert('Failed to submit restaurant. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="add-restaurant-page">
      {/* Header */}
      <header className="add-restaurant-header">
        <div className="header-content">
          <div className="logo" onClick={() => navigate('/')}>
            <img src="/wolfLogo.png" alt="SafeBites Logo" className="logo-img" />
            <h1>SafeBites</h1>
          </div>
          <button className="back-btn" onClick={() => navigate('/')}>
            ← Back to Home
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="add-restaurant-container">
        <div className="add-restaurant-hero">
          <h1>Add Your Restaurant</h1>
          <p>Join SafeBites and help people with food allergies dine safely at your establishment</p>
        </div>

        <div className="form-card">
          <form onSubmit={handleSubmit}>
            {/* Restaurant Information Section */}
            <div className="form-section">
              <h2 className="section-title">Restaurant Information</h2>
              
              <div className="form-group">
                <label htmlFor="restaurantName">
                  Restaurant Name <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="restaurantName"
                  name="restaurantName"
                  value={formData.restaurantName}
                  onChange={handleInputChange}
                  placeholder="Enter your restaurant name"
                  required
                />
              </div>

              <div className="form-group">
                <label>
                  Cuisine Type <span className="required">*</span>
                </label>
                <p className="field-description">Select all that apply</p>
                <div className="cuisine-grid">
                  {cuisineOptions.map((cuisine) => (
                    <button
                      key={cuisine}
                      type="button"
                      className={`cuisine-btn ${formData.cuisine.includes(cuisine) ? 'selected' : ''}`}
                      onClick={() => handleCuisineToggle(cuisine)}
                    >
                      {cuisine}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="rating">
                  Restaurant Rating <span className="required">*</span>
                </label>
                <p className="field-description">Enter a rating between 0 and 5</p>
                <input
                  type="number"
                  id="rating"
                  name="rating"
                  value={formData.rating}
                  onChange={handleInputChange}
                  placeholder="4.5"
                  min="0"
                  max="5"
                  step="0.1"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="description">Restaurant Description</label>
                <p className="field-description">Tell us about your restaurant (optional)</p>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Describe your restaurant, specialties, ambiance, etc."
                  rows={4}
                />
              </div>
            </div>

            {/* Location Section */}
            <div className="form-section">
              <h2 className="section-title">Location</h2>
              
              <div className="form-group">
                <label htmlFor="street">
                  Street Address <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="street"
                  name="street"
                  value={formData.street}
                  onChange={handleInputChange}
                  placeholder="123 Main Street"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="city">
                    City <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    id="city"
                    name="city"
                    value={formData.city}
                    onChange={handleInputChange}
                    placeholder="City"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="state">
                    State <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    id="state"
                    name="state"
                    value={formData.state}
                    onChange={handleInputChange}
                    placeholder="NC"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="zipCode">
                    ZIP Code <span className="required">*</span>
                  </label>
                  <input
                    type="text"
                    id="zipCode"
                    name="zipCode"
                    value={formData.zipCode}
                    onChange={handleInputChange}
                    placeholder="27502"
                    required
                  />
                </div>
              </div>
            </div>

            {/* Menu Upload Section */}
            <div className="form-section">
              <h2 className="section-title">Menu Upload</h2>
              
              <div className="form-group">
                <label htmlFor="menuCsv">
                  Menu CSV File <span className="required">*</span>
                </label>
                <p className="field-description">Upload your restaurant menu as a CSV file with allergen information</p>
                <div className="file-upload-wrapper">
                  <input
                    type="file"
                    id="menuCsv"
                    name="menuCsv"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="file-input"
                    required
                  />
                  <label htmlFor="menuCsv" className="file-label">
                    {menuCsv ? (
                      <span className="file-selected">
                        📄 {menuCsv.name}
                      </span>
                    ) : (
                      <span className="file-placeholder">
                        📁 Choose CSV file or drag here
                      </span>
                    )}
                  </label>
                </div>
                {menuCsv && (
                  <button
                    type="button"
                    className="remove-file-btn"
                    onClick={() => {
                      setMenuCsv(null);
                      const fileInput = document.getElementById('menuCsv') as HTMLInputElement;
                      if (fileInput) fileInput.value = '';
                    }}
                  >
                    ✕ Remove file
                  </button>
                )}
              </div>
            </div>

            {/* Submit Section */}
            <div className="form-actions">
              <button 
                type="button" 
                className="cancel-btn" 
                onClick={() => navigate('/')}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="submit-btn"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Restaurant'}
              </button>
            </div>
          </form>
        </div>

        {/* Info Section */}
        <div className="info-section">
          <div className="info-card">
            <div className="info-icon">✓</div>
            <h3>Why Join SafeBites?</h3>
            <ul>
              <li>Reach customers with dietary restrictions</li>
              <li>Build trust with transparent allergen information</li>
              <li>Increase your restaurant's visibility</li>
              <li>Help create a safer dining experience</li>
            </ul>
          </div>

          <div className="info-card">
            <div className="info-icon">📋</div>
            <h3>What Happens Next?</h3>
            <ul>
              <li>Our team will review your application</li>
              <li>We'll contact you within 2-3 business days</li>
              <li>We'll help you add your menu and allergen info</li>
              <li>Your restaurant goes live on SafeBites!</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AddRestaurant;
