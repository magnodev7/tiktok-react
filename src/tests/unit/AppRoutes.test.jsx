import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '@/App';

describe('App routing e proteção de rotas', () => {
  beforeEach(() => {
    window.history.pushState({}, 'Test page', '/');
  });

  it('redireciona usuário não autenticado para /login', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument();
    });
  });

  it('permite login e navega para dashboard protegido', async () => {
    render(<App />);

    const username = await screen.findByPlaceholderText(/seu_usuario/i);
    const password = await screen.findByPlaceholderText(/••••/i);
    const submit = await screen.findByRole('button', { name: /entrar/i });

    await userEvent.type(username, 'admin');
    await userEvent.type(password, 'admin123');
    await userEvent.click(submit);

    const dashboardLabels = await screen.findAllByText(/dashboard/i);
    expect(dashboardLabels.length).toBeGreaterThan(0);
    expect(window.location.pathname).toBe('/');
  });
});
