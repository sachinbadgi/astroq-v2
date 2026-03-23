import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AuthPage from '../components/auth/AuthPage';
import apiClient from '../api/client';

// Mock the API client
vi.mock('../api/client');

describe('AuthPage', () => {
  it('renders login form with username/password fields', () => {
    render(<AuthPage onLogin={() => {}} />);
    expect(screen.getByPlaceholderText('Choose a cosmos identifier')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Enter the Portal/i })).toBeInTheDocument();
  });

  it('shows auth error message on failed login', async () => {
    (apiClient.post as any).mockRejectedValueOnce({
      response: { data: { detail: 'Incorrect credentials' } }
    });

    render(<AuthPage onLogin={() => {}} />);
    
    fireEvent.change(screen.getByPlaceholderText('Choose a cosmos identifier'), { target: { value: 'wrong' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'pass' } });
    fireEvent.click(screen.getByRole('button', { name: /Enter the Portal/i }));

    await waitFor(() => {
      expect(screen.getByText('Incorrect credentials')).toBeInTheDocument();
    });
  });

  it('toggles to register mode', () => {
    render(<AuthPage onLogin={() => {}} />);
    
    // Initial state is login
    expect(screen.getByRole('button', { name: /Enter the Portal/i })).toBeInTheDocument();
    
    // Toggle to register
    fireEvent.click(screen.getByText(/Need an account\?/i));
    
    // New state is register
    expect(screen.getByRole('button', { name: /Forge Account/i })).toBeInTheDocument();
  });

  it('calls /login API with correct payload', async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: { access_token: 'fake-token' }
    });
    
    const onLoginMock = vi.fn();
    render(<AuthPage onLogin={onLoginMock} />);
    
    fireEvent.change(screen.getByPlaceholderText('Choose a cosmos identifier'), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /Enter the Portal/i }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/login', expect.any(FormData));
    });
    
    // Check if token was saved
    expect(localStorage.getItem('astroq_token')).toBe('fake-token');
    expect(localStorage.getItem('astroq_user')).toBe('testuser');
    expect(onLoginMock).toHaveBeenCalled();
  });

  it('renders Google Sign-In button area', () => {
    render(<AuthPage onLogin={() => {}} />);
    // In actual implementation, we'll wrap with GoogleOAuthProvider, but here we just check our wrapper text
    expect(screen.getByText('Or')).toBeInTheDocument();
  });
});
