import React, { useState } from "react";
import './UserProfile.css';

const UserProfile: React.FC = () => {
  const [user] = useState({
  name: "Ishwarya",
  email: "ishwarya@example.com",
});


  const handleLogout = () => {
    alert("Logged out!");
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h2>User Profile</h2>
      <p><strong>Name:</strong> {user.name}</p>
      <p><strong>Email:</strong> {user.email}</p>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
};

export default UserProfile;
