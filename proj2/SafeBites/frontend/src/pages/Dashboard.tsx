import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_ENDPOINTS } from '../config/api';
import './Dashboard.css';
import Home from './Home';
import SearchChat from './SearchChat';
import Settings from './Settings';

function Dashboard() {
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState('home');

  // User data from API
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [allergies, setAllergies] = useState<string[]>([]);
  const [isLoadingUser, setIsLoadingUser] = useState(true);

  // Fetch user data on component mount
  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const authToken = localStorage.getItem('authToken');
      const storedUsername = localStorage.getItem('username');

      if (!authToken) {
        // Not logged in, redirect to login
        navigate('/login');
        return;
      }

      const response = await fetch(API_ENDPOINTS.users.me, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user data');
      }

      const userData = await response.json();
      console.log('Dashboard - User data:', userData);
      
      setUsername(userData.username || storedUsername || 'User');
      setName(userData.name || 'User');
      setAllergies(userData.allergen_preferences || []);
    } catch (error) {
      console.error('Dashboard - Error fetching user data:', error);
      // Use fallback data from localStorage
      const storedUsername = localStorage.getItem('username');
      if (storedUsername) {
        setUsername(storedUsername);
        setName('User');
      }
    } finally {
      setIsLoadingUser(false);
    }
  };

  const handleLogout = () => {
    // Clear auth data
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    navigate('/login');
  };

  const renderContent = () => {
    switch(currentPage) {
      case 'home':
        return <Home />;
      case 'search-chat':
        return <SearchChat />;
      case 'settings':
        return <Settings />;
      default:
        return <Home />;
    }
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        {/* Left: Logo and Name */}
        <div className="header-left">
          <div className="logo">
            <img src="/wolfLogo.png" alt="SafeBites Logo" className="logo-img" />
            <h1>SafeBites</h1>
          </div>
        </div>

        {/* Right: Profile Icon */}
        <div className="header-right">
          <div className="profile-container">
            <button 
              className="profile-btn"
              onClick={() => setIsProfileOpen(!isProfileOpen)}
            >
              <img src="/icons/hugeicons_male.png" alt="Profile" className="profile-icon" />
            </button>
            
            {/* Profile Dropdown */}
            {isProfileOpen && (
              <div className="profile-dropdown">
                <div className="profile-info">
                  <p className="profile-fullname">{name}</p>
                  <p className="profile-username">@{username}</p>
                </div>

                {/* Allergen Preferences */}
                {!isLoadingUser && allergies.length > 0 && (
                  <div className="profile-allergies">
                    <p className="profile-allergies-label">Allergies:</p>
                    <div className="profile-allergies-list">
                      {allergies.map((allergy, index) => (
                        <span key={index} className="profile-allergy-tag">
                          {allergy}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* No allergies message */}
                {!isLoadingUser && allergies.length === 0 && (
                  <div className="profile-allergies">
                    <p className="profile-no-allergies">No allergies set</p>
                  </div>
                )}
                
                <button 
                  className="btn-logout"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="dashboard-body">
        {/* Sidebar */}
        <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
          <button 
            className="menu-toggle-btn-sidebar"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            {isSidebarOpen ? (
              <span className="close-icon">✕</span>
            ) : (
              <span className="hamburger-icon">☰</span>
            )}
          </button>
          
          <nav className="sidebar-nav">
            <button 
              className={`sidebar-item ${currentPage === 'home' ? 'active' : ''}`}
              onClick={() => setCurrentPage('home')}
            >
              <img src="/icons/hugeicons_home.png" alt="Home" className="sidebar-icon" />
              {isSidebarOpen && <span className="sidebar-text">Home</span>}
            </button>

            <button 
              className={`sidebar-item ${currentPage === 'search-chat' ? 'active' : ''}`}
              onClick={() => setCurrentPage('search-chat')}
            >
              <img src="/icons/hugeicon_ai_search.png" alt="Search Chat" className="sidebar-icon" />
              {isSidebarOpen && <span className="sidebar-text">Search Chat</span>}
            </button>
            
            <button 
              className={`sidebar-item ${currentPage === 'settings' ? 'active' : ''}`}
              onClick={() => setCurrentPage('settings')}
            >
              <img src="/icons/hugeicons_setting.png" alt="Settings" className="sidebar-icon" />
              {isSidebarOpen && <span className="sidebar-text">Settings</span>}
            </button>
          </nav>
        </aside>

        {/* Main Content */}
        <main className={`dashboard-main ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default Dashboard;