import React, { useState } from "react";
import './Signup.css';

const Signup: React.FC = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Signup Data:", formData);
    alert("Signup successful!");
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>Signup Page</h2>
      <form onSubmit={handleSubmit} style={{ display: "inline-block", textAlign: "left" }}>
        <div>
          <label>Name: </label>
          <input type="text" name="name" onChange={handleChange} required />
        </div>
        <div>
          <label>Email: </label>
          <input type="email" name="email" onChange={handleChange} required />
        </div>
        <div>
          <label>Password: </label>
          <input type="password" name="password" onChange={handleChange} required />
        </div>
        <button type="submit" style={{ marginTop: "10px" }}>Sign Up</button>
      </form>
    </div>
  );
};

export default Signup;
