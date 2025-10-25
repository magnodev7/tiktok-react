import { describe, expect, it, vi } from 'vitest';
import { screen, render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';

function AuthProbe() {
  const { user, login, logout } = useAuth();

  return (
    <div>
      <span data-testid="current-user">{user?.username ?? 'anonymous'}</span>
      <button onClick={() => login('admin', 'admin123')}>do-login</button>
      <button onClick={() => logout()}>do-logout</button>
    </div>
  );
}

describe('AuthContext', () => {
  it('realiza login e persiste token', async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    expect(screen.getByTestId('current-user').textContent).toBe('anonymous');

    await userEvent.click(screen.getByRole('button', { name: 'do-login' }));

    await waitFor(() => {
      expect(screen.getByTestId('current-user').textContent).toBe('admin');
    });

    expect(localStorage.getItem('auth_token')).toBe('mock-token');
  });

  it('realiza logout limpando token armazenado', async () => {
    localStorage.setItem('auth_token', 'mock-token');

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('current-user').textContent).toBe('admin');
    });

    await userEvent.click(screen.getByRole('button', { name: 'do-logout' }));

    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(screen.getByTestId('current-user').textContent).toBe('anonymous');
  });
});
