import React, { useState } from "react";
import './RestaurantCreation.css';
const RestaurantCreation: React.FC = () => {
  const [restaurant, setRestaurant] = useState({
    name: "",
    location: "",
    cuisine: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setRestaurant(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Restaurant Created:", restaurant);
    alert(`Restaurant "${restaurant.name}" created successfully!`);
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>Create a Restaurant</h2>
      <form onSubmit={handleSubmit} style={{ display: "inline-block", textAlign: "left" }}>
        <div>
          <label>Restaurant Name: </label>
          <input type="text" name="name" onChange={handleChange} required />
        </div>
        <div>
          <label>Location: </label>
          <input type="text" name="location" onChange={handleChange} required />
        </div>
        <div>
          <label>Cuisine Type: </label>
          <input type="text" name="cuisine" onChange={handleChange} required />
        </div>
        <button type="submit" style={{ marginTop: "10px" }}>Create</button>
      </form>
    </div>
  );
};

export default RestaurantCreation;
