import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import SignUp from '../pages/SignUp';
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

describe('SignUp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.alert = vi.fn();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <SignUp />
      </BrowserRouter>
    );
  };

  test('renders signup form with all input fields', () => {
    renderComponent();
    
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Create Password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirm Password/i)).toBeInTheDocument();
    expect(screen.getByText(/Food Allergies/i)).toBeInTheDocument();
  });

  test('allows user to fill in all form inputs', () => {
    renderComponent();
    
    const nameInput = screen.getByLabelText(/Full Name/i);
    const usernameInput = screen.getByLabelText(/Username/i);
    const passwordInput = screen.getByLabelText(/Create Password/i);
    const confirmPasswordInput = screen.getByLabelText(/Confirm Password/i);
    
    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(usernameInput, { target: { value: 'johndoe' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });
    
    expect(nameInput).toHaveValue('John Doe');
    expect(usernameInput).toHaveValue('johndoe');
    expect(passwordInput).toHaveValue('password123');
    expect(confirmPasswordInput).toHaveValue('password123');
  });

  test('allows user to select optional food allergies', () => {
    renderComponent();
    
    const peanutsBtn = screen.getByRole('button', { name: 'Peanuts' });
    const milkBtn = screen.getByRole('button', { name: 'Milk' });
    
    fireEvent.click(peanutsBtn);
    fireEvent.click(milkBtn);
    
    expect(peanutsBtn).toHaveClass('selected');
    expect(milkBtn).toHaveClass('selected');
  });

  test('successfully signs up and navigates to login', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ id: 1, message: 'User created' }),
    });

    renderComponent();
    
    // Fill in form
    fireEvent.change(screen.getByLabelText(/Full Name/i), { 
      target: { value: 'John Doe' } 
    });
    fireEvent.change(screen.getByLabelText(/Username/i), { 
      target: { value: 'johndoe' } 
    });
    fireEvent.change(screen.getByLabelText(/Create Password/i), { 
      target: { value: 'password123' } 
    });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), { 
      target: { value: 'password123' } 
    });
    
    // Submit form
    const signupButton = screen.getByRole('button', { name: /Sign Up/i });
    fireEvent.click(signupButton);
    
    // Wait for API call
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    }, { timeout: 3000 });
    
    // Verify API call
    const fetchCall = (global.fetch as any).mock.calls[0];
    expect(fetchCall[0]).toBe(API_ENDPOINTS.users.signup);
    expect(fetchCall[1].method).toBe('POST');
    
    // Verify navigation to login
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  test('navigates to login when "Already have an account" link is clicked', () => {
    renderComponent();
    
    const loginLink = screen.getByText(/Already have an account\?/i).parentElement?.querySelector('a');
    expect(loginLink).toBeInTheDocument();
    
    if (loginLink) {
      fireEvent.click(loginLink);
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    }
  });

  test('shows error when passwords do not match', async () => {
    renderComponent();
    
    fireEvent.change(screen.getByLabelText(/Full Name/i), { 
      target: { value: 'John Doe' } 
    });
    fireEvent.change(screen.getByLabelText(/Username/i), { 
      target: { value: 'johndoe' } 
    });
    fireEvent.change(screen.getByLabelText(/Create Password/i), { 
      target: { value: 'password123' } 
    });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), { 
      target: { value: 'differentpassword' } 
    });
    
    const signupButton = screen.getByRole('button', { name: /Sign Up/i });
    fireEvent.click(signupButton);
    
    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith("Passwords don't match!");
    });
  });
});