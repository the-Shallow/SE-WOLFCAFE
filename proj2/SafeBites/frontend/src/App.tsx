import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import Login from "./pages/Login.tsx";
import Signup from "./pages/Signup.tsx";
import UserProfile from "./pages/UserProfile.tsx";
import RestaurantCreation from "./pages/RestaurantCreation.tsx";
import "./App.css";

function App() {
  return (
    <Router>
      <nav className="p-4 bg-gray-200 flex justify-center gap-4">
        <Link to="/">Login</Link>
        <Link to="/signup">Signup</Link>
        <Link to="/profile">User Profile</Link>
        <Link to="/restaurant">Restaurant Creation</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/profile" element={<UserProfile />} />
        <Route path="/restaurant" element={<RestaurantCreation />} />
      </Routes>
    </Router>
  );
}

export default App;
