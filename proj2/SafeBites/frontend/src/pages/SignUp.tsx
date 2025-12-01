import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_ENDPOINTS } from '../config/api';
import './SignUp.css';

function SignUp() {
    const navigate = useNavigate();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [formData, setFormData] = useState({
        name: "",
        username: "",
        password: "",
        confirmPassword: "",
        allergenPreferences: [] as string[]
    });

    const commonAllergens = [
        'Peanuts', 'Tree Nuts', 'Milk', 'Eggs', 'Fish', 
        'Shellfish', 'Soy', 'Wheat', 'Sesame', 'Gluten'
    ];

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleAllergenToggle = (allergen: string) => {
        setFormData(prev => ({
            ...prev,
            allergenPreferences: prev.allergenPreferences.includes(allergen)
                ? prev.allergenPreferences.filter(a => a !== allergen)
                : [...prev.allergenPreferences, allergen]
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        // Validation
        if (formData.password !== formData.confirmPassword) {
            alert("Passwords don't match!");
            return;
        }
        if (formData.password.length < 6) {
            alert("Password must be at least 6 characters!");
            return;
        }

        setIsSubmitting(true);

        try {
            const response = await fetch(API_ENDPOINTS.users.signup, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: formData.name,
                    username: formData.username,
                    password: formData.password,
                    allergen_preferences: formData.allergenPreferences
                })
            });

            const responseText = await response.text();
            console.log('SignUp Response Status:', response.status);
            console.log('SignUp Response:', responseText);

            if (!response.ok) {
                let errorMessage = 'Failed to sign up';
                try {
                    const errorData = JSON.parse(responseText);
                    errorMessage = errorData.detail || errorData.message || responseText;
                } catch {
                    errorMessage = responseText || `HTTP Error ${response.status}`;
                }
                throw new Error(errorMessage);
            }

            const result = JSON.parse(responseText);
            console.log('User created:', result);
            
            alert('Account created successfully! Please login.');
            navigate('/login');
        } catch (error) {
            console.error('Error signing up:', error);
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
            alert(`Failed to sign up: ${errorMessage}`);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="signup-container">
            <div className="signup-card">
                {/* Logo */}
                <div className="signup-logo">
                    <img src="/wolfLogo.png" alt="SafeBites Logo" className="signup-logo-img" />
                    <h1>SafeBites</h1>
                </div>

                <h2 className="signup-title">Create Account</h2>
                <p className="signup-subtitle">Join SafeBites today</p>

                {/* Sign Up Form */}
                <form className="signup-form" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="name">Full Name</label>
                        <input 
                            type="text" 
                            id="name"
                            name="name"
                            value={formData.name}
                            onChange={handleInputChange}
                            placeholder="Enter your full name"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input 
                            type="text" 
                            id="username"
                            name="username"
                            value={formData.username}
                            onChange={handleInputChange}
                            placeholder="Choose a username"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Create Password</label>
                        <input 
                            type="password" 
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleInputChange}
                            placeholder="Create a strong password"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">Confirm Password</label>
                        <input 
                            type="password" 
                            id="confirmPassword"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleInputChange}
                            placeholder="Confirm your password"
                            required
                        />
                    </div>

                    <div className="form-group allergens-section">
                        <label>Food Allergies (Optional)</label>
                        <p className="allergen-description">Select any allergies you have</p>
                        <div className="allergen-grid">
                            {commonAllergens.map((allergen) => (
                                <button
                                    key={allergen}
                                    type="button"
                                    className={`allergen-btn ${formData.allergenPreferences.includes(allergen) ? 'selected' : ''}`}
                                    onClick={() => handleAllergenToggle(allergen)}
                                >
                                    {allergen}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button type="submit" className="signup-btn" disabled={isSubmitting}>
                        {isSubmitting ? 'Creating Account...' : 'Sign Up'}
                    </button>
                </form>

                {/* Login Link */}
                <div className="login-prompt">
                    <p>Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); navigate('/login'); }}>Login</a></p>
                </div>
            </div>
        </div>
    );
}
export default SignUp;