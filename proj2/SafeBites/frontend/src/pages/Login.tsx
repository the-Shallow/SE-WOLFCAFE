import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_ENDPOINTS } from '../config/api';
import './Login.css';

function Login() {
    const navigate = useNavigate();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        setIsSubmitting(true);

        try {
            const response = await fetch(API_ENDPOINTS.users.login(username, password), {
                method: 'POST',
            });

            const responseText = await response.text();
            console.log('Login Response Status:', response.status);
            console.log('Login Response:', responseText);

            if (!response.ok) {
                let errorMessage = 'Failed to login';
                try {
                    const errorData = JSON.parse(responseText);
                    errorMessage = errorData.detail || errorData.message || responseText;
                } catch {
                    errorMessage = responseText || `HTTP Error ${response.status}`;
                }
                throw new Error(errorMessage);
            }

            const result = JSON.parse(responseText);
            console.log('Login successful:', result);
            
            // Store user token/data in localStorage
            if (result.access_token) {
                localStorage.setItem('authToken', result.access_token);
            }
            localStorage.setItem('username', username);
            
            alert('Login successful!');
            navigate('/dashboard');
        } catch (error) {
            console.error('Error logging in:', error);
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
            alert(`Failed to login: ${errorMessage}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card">
                {/* Logo */}
                <div className="login-logo">
                    <img src="/wolfLogo.png" alt="SafeBites Logo" className="login-logo-img" />
                    <h1>SafeBites</h1>
                </div>

                <h2 className="login-title">Welcome Back</h2>
                <p className="login-subtitle">Login to your account</p>

                {/* Login Form */}
                <form className="login-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input 
                            type="text" 
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Enter your username"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input 
                            type="password" 
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            required
                        />
                    </div>

                    <a href="#" className="forgot-password">Forgot Password?</a>

                    <button type="submit" className="login-btn" disabled={isSubmitting}>
                        {isSubmitting ? 'Logging in...' : 'Login'}
                    </button>
                </form>

                {/* Sign Up Link */}
                <div className="signup-prompt">
                    <p>Don't have an account? <a href="#" onClick={(e) => { e.preventDefault(); navigate('/signup'); }}>Sign Up</a></p>
                </div>
            </div>
        </div>
    )
}

export default Login;