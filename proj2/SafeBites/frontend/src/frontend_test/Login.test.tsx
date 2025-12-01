import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import Login from '../pages/Login';
import { API_ENDPOINTS } from '../config/api';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock fetch
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.alert = vi.fn();
    localStorageMock.clear();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
  };

  test('renders login form with username and password inputs', () => {
    renderComponent();
    
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Login/i })).toBeInTheDocument();
  });

  test('allows user to fill in username and password', () => {
    renderComponent();
    
    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    
    expect(usernameInput).toHaveValue('testuser');
    expect(passwordInput).toHaveValue('password123');
  });

  test('successfully logs in and navigates to dashboard', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ 
        access_token: 'mock-token-123',
        message: 'Login successful' 
      }),
    });

    renderComponent();
    
    // Fill in form
    fireEvent.change(screen.getByLabelText(/Username/i), { 
      target: { value: 'testuser' } 
    });
    fireEvent.change(screen.getByLabelText(/Password/i), { 
      target: { value: 'password123' } 
    });
    
    // Submit form
    const loginButton = screen.getByRole('button', { name: /Login/i });
    fireEvent.click(loginButton);
    
    // Wait for API call
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    }, { timeout: 3000 });
    
    // Verify API call
    const fetchCall = (global.fetch as any).mock.calls[0];
    expect(fetchCall[0]).toBe(API_ENDPOINTS.users.login('testuser', 'password123'));
    expect(fetchCall[1].method).toBe('POST');
    
    // Verify localStorage was updated
    await waitFor(() => {
      expect(localStorageMock.getItem('authToken')).toBe('mock-token-123');
      expect(localStorageMock.getItem('username')).toBe('testuser');
    });
    
    // Verify navigation to dashboard
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  test('navigates to signup when "Sign Up" link is clicked', () => {
    renderComponent();
    
    const signupLink = screen.getByText(/Don't have an account\?/i).parentElement?.querySelector('a');
    expect(signupLink).toBeInTheDocument();
    
    if (signupLink) {
      fireEvent.click(signupLink);
      expect(mockNavigate).toHaveBeenCalledWith('/signup');
    }
  });
});